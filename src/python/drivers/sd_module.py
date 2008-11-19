#!/usr/bin/python
#
# sd_module.py - Interface to Speech Dispatcher modules
#   
# Copyright (C) 2007 Brailcom, o.p.s.
# 
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this package; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301, USA.
# 
# $Id: sd_module.py,v 1.3 2008-05-07 08:20:51 hanke Exp $

"""Interface to Speech Dispatcher modules"""

import sys
import select
import socket
import time
import thread
import threading
import subprocess

import driver

from ttsapi.structures import *
from ttsapi.errors import *

class SSIPError(Exception):
    """Common base class for exceptions during SSIP communication."""
    
class SSIPCommunicationError(SSIPError):
    """Exception raised when trying to operate on a closed connection."""
    
class SSIPResponseError(Exception):
    def __init__(self, code, msg, data):
        Exception.__init__(self, "%s: %s" % (code, msg))
        self._code = code
        self._msg = msg
        self._data = data

    def code(self):
        """Return the server response error code as integer number."""
        return self._code
        
    def msg(self):
        """Return server response error message as string."""
        return self._msg


class SSIPCommandError(SSIPResponseError):
    """Exception raised on error response after sending command."""

    def command(self):
        """Return the command string which resulted in this error."""
        return self._data

    
class SSIPDataError(SSIPResponseError):
    """Exception raised on error response after sending data."""

    def data(self):
        """Return the data which resulted in this error."""
        return self._data

    
class _SSIP_Connection:
    """Implemantation of low level SSIP communication."""
    
    _NEWLINE = "\n"
    _END_OF_DATA_MARKER = '.'
    _END_OF_DATA_MARKER_ESCAPED = '..'
    _END_OF_DATA = _NEWLINE + _END_OF_DATA_MARKER + _NEWLINE
    _END_OF_DATA_ESCAPED = _NEWLINE + _END_OF_DATA_MARKER_ESCAPED + _NEWLINE

    _CALLBACK_TYPE_MAP = {700: 'index_mark',
                          701: 'message_start',
                          702: 'message_end',
                          703: None,
                          704: None,
                          705: None,
                          }
    
    def __init__(self, pipe_in, pipe_out):
        """Init connection: open the socket to server,
        initialize buffers, launch a communication handling
        thread."""
        self._pipe_in = pipe_in
        self._pipe_out = pipe_out
        self._buffer = ""
        self._com_buffer = []
        self._callback = None
        self._ssip_reply_semaphore = threading.Semaphore(0)
        self._communication_thread = \
                threading.Thread(target=self._communication, kwargs={},
                                 name="SSIP client communication thread")
        self._communication_thread.start()
    
    def close(self):
        """Close the server connection, destroy the communication thread."""
        # Destroy other thread
        self._pipe_in.close()
        self._pipe_out.close()
        # Wait for the other thread to terminate
        self._communication_thread.join()
        
    def _communication(self):
        """Handle incomming socket communication.

        Listens for all incomming communication on the pipe, dispatches
        events and puts all other replies into self._com_buffer list in the
        already parsed form as (code, msg, data).  Each time a new item is
        appended to the _com_buffer list, the corresponding semaphore
        'self._ssip_reply_semaphore' is incremented.

        This method is designed to run in a separate thread.  The thread can be
        interrupted by closing the pipe on which it is listening for
        reading."""

        driver.log.info("Communication thread starting")

        while True:
            try:
                code, msg, data = self._recv_message()
            except IOError:
                # If the socket has been closed, exit the thread
                driver.log.info("Communication broken, exiting")
                sys.exit()
            if code/100 != 7:
                # This is not an index mark nor an event
                self._com_buffer.append((code, msg, data))
                self._ssip_reply_semaphore.release()
                continue
            # Ignore the event if no callback function has been registered.
            #if self._callback is not None:
            else:
                type = self._CALLBACK_TYPE_MAP[code]
                if type == None:
                    return
                event = AudioEvent(type = type)
                if event.type == 'index_mark':
                    event.name = data[0]
                global module
                event.message_id = module.current_msg_id

                driver.log.debug("Executing callback function from driver")
                self._callback_function(self._callback_connection, event)
                
    def _readline(self):
        """Read one whole line from the socket.

        Blocks until the line delimiter ('_NEWLINE') is read.
        """
        pointer = self._buffer.find(self._NEWLINE)
        while pointer == -1:
            try:
                driver.log.debug("Reading")
                d = self._pipe_out.readline()
                driver.log.debug("FROM MODULE:" + d)
            except Exception, e:
                driver.log.error("Received exception: " + str(e))
                raise IOError
            if len(d) == 0:
                driver.log.error("Raising IOError because len(d)==0")
                raise IOError
            self._buffer += d
            pointer = self._buffer.find(self._NEWLINE)
        line = self._buffer[:pointer]
        self._buffer = self._buffer[pointer+len(self._NEWLINE):]
        return line

    def _recv_message(self):
        """Read server response or a callback
        and return the triplet (code, msg, data)."""
        data = []
        c = None
        while True:
            line = self._readline()
            assert len(line) >= 4, "Malformed data received from server!"
            code, sep, text = line[:3], line[3], line[4:]
            assert code.isalnum() and (c is None or code == c) and \
                   sep in ('-', ' '), "Malformed data received from server!"
            if sep == ' ':
                msg = text
                return int(code), msg, tuple(data)
            data.append(text)

    def _recv_response(self):
        """Read server response from the communication thread
        and return the triplet (code, msg, data)."""
        # TODO: This check is dumb but seems to work.  The main thread
        # hangs without it, when the Speech Dispatcher connection is lost.
        driver.log.debug("Checking if com thread is alive in sd_module")
        if not self._communication_thread.isAlive():
            raise SSIPCommunicationError
        driver.log.debug("Trying to acquire semaphore in sd_module")
        self._ssip_reply_semaphore.acquire()
        driver.log.debug("Semaphore acquired in sd_module")
        # The list is sorted, read the first item
        response = self._com_buffer[0]
        del self._com_buffer[0]
        return response

    def send_command(self, command, wait_for_reply=True, *args):
        """Send SSIP command with given arguments and read server response.

        Arguments can be of any data type -- they are all stringified before
        being sent to the server.

        Returns a triplet (code, msg, data), where 'code' is a numeric SSIP
        response code as an integer, 'msg' is an SSIP rsponse message as string
        and 'data' is a tuple of strings (all lines of response data) when a
        response contains some data.
        
        'SSIPCommandError' is raised in case of non 2xx return code.  See SSIP
        documentation for more information about server responses and codes.

        'IOError' is raised when the socket was closed by the remote side.
        
        """
        driver.log.debug("Sending command INIT in sd_module")
        cmd = ' '.join((command,) + tuple(map(str, args)))
        try:
            self._pipe_in.write(cmd + "\n")
            self._pipe_in.flush()
            driver.log.debug("TO MODULE:" + cmd)
        except IOError:
            raise SSIPCommunicationError("Driver connection lost.")
        driver.log.debug("INIT waiting for reply in sd_module")
        if wait_for_reply:
            code, msg, data = self._recv_response()
            if code/100 != 2:
                raise SSIPCommandError(code, msg, cmd)
            driver.log.debug("Reply received in sd_module")
            return code, msg, data
        else:
            return None
        
    def send_data(self, data):
        """Send multiline data and read server response.

        Returned value is the same as for 'send_command()' method.

        'SSIPDataError' is raised in case of non 2xx return code. See SSIP
        documentation for more information about server responses and codes.
        
        'IOError' is raised when the socket was closed by the remote side.
        
        """
        # Escape the end-of-data marker even if present at the beginning
        if data.startswith(self._END_OF_DATA_MARKER + self._NEWLINE):
            l = len(self._END_OF_DATA_MARKER)
            data = self._END_OF_DATA_MARKER_ESCAPED + data[l:]
        elif data == self._END_OF_DATA_MARKER:
            data = self._END_OF_DATA_MARKER_ESCAPED
        data = data.replace(self._END_OF_DATA, self._END_OF_DATA_ESCAPED)
        try:
            self._pipe_in.write(data + self._END_OF_DATA)
            self._pipe_in.flush()
        except IOError:
            raise SSIPCommunicationError("Driver connection lost.")
        code, msg, response_data = self._recv_response()
        if code/100 != 2:
            raise SSIPDataError(code, msg, data)
        return code, msg, response_data

    def set_callback(self, callback):
        """Register a callback function for handling asynchronous events.

        Arguments:
          callback -- a callable object (function) which will be called to
            handle asynchronous events (arguments described below).  Passing
            `None' results in removing the callback function and ignoring
            events.  Just one callback may be registered.  Attempts to register
            a second callback will result in the former callback being
            replaced.

        The callback function must accept three positional arguments
        ('message_id', 'client_id', 'event_type') and an optional keyword
        argument 'index_mark' (when INDEX_MARK events are turned on).

        Note, that setting the callback function doesn't turn the events on.
        The user is responsible to turn them on by sending the appropriate `SET
        NOTIFICATION' command.

        """
        self._callback = callback

            
class SSIPDriver(object):
    """Basic Driver SSIP client interface."""

    settings = {'language' : 'en'}
    current_msg_id = None

    def __init__(self, binary_path, binary_conf):
        """Run binary_path as a subprocess and establish piped connection"""

        self._lock = threading.Lock()

        self._module = subprocess.Popen((binary_path, binary_conf), bufsize=1,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        close_fds=True)
        self._conn = _SSIP_Connection(self._module.stdin, self._module.stdout)

    def quit(self):
        """Close the connection"""
        driver.log.info("Closing connection")
        self._conn.close()
        driver.log.info("Waiting for child process (sd_*) to terminate")
        self._module.wait()
        driver.log.info("Child process terminated")

    def set(self, item, value):
        # TODO: Locking
        self.settings[item] = value

    def init(self):
        """Initialize the module"""
        driver.log.debug("Called INIT in sd_module")
        result = self._conn.send_command('INIT')
        
        return result
           
    def send_settings(self):
        """Send current settings to output module. Settings is a list of tuples
        (field, value)"""
        res = ""
        for field, value in self.settings.iteritems():
            if isinstance(value, str):
                val = value
            elif isinstance(value, int) or isinstance(value, float):
                val = str(int(value))
            else:
                raise "Unexpected data type"
            res += field + "=" + val + "\n"
        self._conn.send_command('SET')
        driver.log.debug("Sending set data |" + res.rstrip('\n') + "|")
        self._conn.send_data(res.rstrip('\n'))

    def speak(self, text):
        """Say given message.

        Arguments:
          text -- message text to be spoken in UTF-8

        This method is non-blocking;  it just sends the command, given
        message is queued on the server and the method returns immediately.

        """
        self.send_settings()
        self._conn.send_command('SPEAK')
        result = self._conn.send_data(text)
        return result

    def char(self, char):
        """Say given character.

        Arguments:
          char -- a character to be spoken.  Either a Python unicode string or
            a UTF-8 encoded byte string.

        This method is non-blocking;  it just sends the command, given
        message is queued on the server and the method returns immediately.

        """
        self._conn.send_command('CHAR')
        self._conn.send_data(char.replace(' ', 'space'))

    def key(self, key):
        """Say given key name.

        Arguments:
          key -- the key name (as defined in SSIP); string.

        This method is non-blocking;  it just sends the command, given
        message is queued on the server and the method returns immediately.

        """
        self.send_settings()
        self._conn.send_command('KEY')
        self._conn.send_data(key)

    def sound_icon(self, sound_icon):
        """Output given sound_icon.

        Arguments:
          sound_icon -- the name of the sound icon as defined by SSIP; string.

        This method is non-blocking; it just sends the command, given message
        is queued on the server and the method returns immediately.

        """
        self.send_settings()
        self._conn.send_command('SOUND_ICON')
        self._conn.send_data(sound_icon)

    def stop(self):
        """Immediately stop speaking the currently spoken message."""
        self._conn.send_command('STOP', wait_for_reply=False)    


class Configuration(driver.Configuration):
    """Configuration class for this driver"""
    # public
    synthesizer = None
    binary_path = None
    binary_conf = None
    recode_fallback = '?'
    
conf = Configuration()

class ModuleError(Exception):
    """Error in Module"""

    def __init__(self, description=None):
        self.description = description
        

module = None

class Core(driver.Core):

    _callback_connection = None
    _callback_function = None

    def __init__(self):
        """Create driver core object"""
        global conf
        global module

        module = SSIPDriver(conf.binary_path, conf.binary_conf)
        self.module = module

    def init(self):
        """Initialize Speech Dispatcher module"""

        (code, msg, data) = self.module.init()
        
        driver.log.info("Module started with message " + str(data))

    def quit(self):
        global module

        driver.log.debug("Quit in sd_module Core")
        module.quit()
        driver.log.debug("Calling parent quit")
        super(Core, self).quit()

    def register_callback(self, connection, function):
        """Register callback"""

        self.module._conn._callback_connection = connection
        self.module._conn._callback_function = function

    def drivers(self):
        """Report information about this driver"""
        global conf
        return DriverDescription(
            driver_id = "sd_module",
            synthesizer_name = "Speech Dispatcher Module with configuration for " + str(conf.synthesizer),
            driver_version = "0.0",
            synthesizer_version = None
            )
    
    def voices(self):
        """Return list of voices"""
        # TODO:
        raise NotImplementedError
    
    def driver_capabilities(self):
        """Return driver capabilities"""
        return DriverCapabilities(
            can_list_voices = False,
            rate_settings = ['relative'],
            pitch_settings = ['relative'],
            punctuation_modes = ['all', 'none', 'some'],
            can_set_punctuation_detail = False,
            capital_letters_modes = ['no', 'spelling'],
            can_say_char = True,
            can_say_key = True,
            can_say_icon = True,
           audio_methods = ['playback'],
            events = 'message',
            performance_level = 'good',
            message_format = ['ssml'],
            supports_multilingual_utterances = False
           )
           
    def set_voice_by_name(self, voice_name):
        """Set voice.

        Arguments:
        voice_name -- name of a voice as obtained by voices()          
        """
        assert isinstance(voice_name, str)
        raise NotImplementedError
    
    def set_voice_by_properties(self, voice_description, variant):
        """Choose and set a voice best matching the given description.

        Arguments:
        voice_description -- VoiceDescription object
        variant -- a positive number meaning variant
        of the voice from those matching voice_description          
        """
        assert isinstance(voice_description, VoiceDescription)
        assert isinstance(variant, int)
        
        raise NotImplementedError
    
    def current_voice(self):
        """Return VoiceDescription of the current voice."""
        raise NotSupportedByDriver
    
    def set_rate(self, rate, method='relative'):
        """Set relative or absolute rate.

        Arguments:
        rate -- desired rate change with respect to default represented
        as a number in percents for relative change or as a positive number
        in words per minute for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(rate, int)
        
        if method == 'absolute':
            return ErrorNotSupportedByDriver
        
        ssip_rate = (rate - 100)
        if ssip_rate > 0:
            ssip_rate /= 5.0
        if ssip_rate > 100:
            ssip_rate = 100
        if ssip_rate < -100:
            ssip_rate = -100

        self.module.set('rate', ssip_rate)
            
    def set_pitch(self, pitch, method='relative'):
        """Set relative or absolute pitch.

        Arguments:
        pitch -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        if method == 'absolute':
            return ErrorNotSupportedByDriver
        
        ssip_pitch = (pitch - 100)
        if ssip_pitch > 0:
            ssip_pitch /= 5.0
        if ssip_pitch > 100:
            ssip_pitch = 100
        if ssip_pitch < -100:
            ssip_pitch = -100

        self.module.set('pitch', ssip_pitch)

                
    ## Style parameters

    def set_punctuation_mode(self, mode):
        """Set punctuation reading mode.
        
        Arguments:
        mode -- one of 'none', 'all', 'some'          
        """
        assert mode in ('none', 'all', 'some')
        self.module.set('punctuation_mode', mode)
            
    def set_capital_letters_mode(self, mode):
        """Set mode for reading capital letters.

        Arguments:
        mode -- one of 'no', 'spelling', 'icon', 'pitch'          
        """
        assert mode in ('no', 'spelling', 'icon', 'pitch')
        if mode == 'no':
            self.module.set('cap_let_recogn', 'off')
        else:
            self.module.set('cap_let_recogn', 'on')

    def set_audio_output(self, method='playback'):
        """Set audio output method as described in TTS API.

        Arguments:
        method -- one of 'playback', 'retrieval'          
        """
        assert method in ('playback', 'retrieval')
        if method == 'retrieval':
            raise ErrorNotSupportedByDriver
    
    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """
        raise ErrorNotSupportedByDriver
        
class Controller(driver.Controller):
    
    def say_text (self, text, format='ssml',
                 position = None, position_type = None,
                 index_mark = None, character = None, message_id = None):
        """Say text"""
        
        if len(text) == 0: return
        if format != 'ssml': raise ErrorNotSupportedByDriver
    
        # Ask for synthesis
        try:
            module.speak(text)
            module.current_msg_id = 1
        except Exception, e:
            driver.log.error("say_text unsuccessful with text: |" + text + "|" + str(e))
            return

        # TODO: Handle message_id consistently
        message_id = module.current_msg_id
        return message_id
        
    def say_key (self, key, message_id=None):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        try:
            module.key(key)
        except:
            driver.log.error("say_key unsuccessful with key: |" + key + "|")

        message_id = 1
        return message_id
        
    def say_char (self, character, message_id=None):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        try:
            module.char(character)
        except:
            driver.log.error("say_char unsuccessful with: |" + character + "|")

        message_id = 1
        return message_id
        
    def say_icon (self, icon, message_id=None):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)
        try:
            module.sound_icon(icon)
        except:
            driver.log.error("speechd-sound-icon unsuccessful with: |" + icon + "|")

        message_id = 1
        return message_id
        
    def cancel (self):
        """Cancel current synthesis process and audio output."""

        module.stop()
        
    def defer (self):
        """Defer current message."""
        raise ErrorNotSupportedByDriver
        
    def discard (self, message_id):
        """Discard a previously deferred message.
4
        Arguments:
        message_id -- unique identification of the message to discard          
        """
        assert isinstance(message_id, int)
        raise ErrorNotSupportedByDriver
        
def main():
    """Main loop for driver code"""

    global conf
    
    if len(sys.argv) < 5:
        print "Can't initialize driver, no module path, module configuration path or synthesizer name specified"
        return -1

    # TODO: This needs to be modified to handle shared memmory communication
    # as well where arguments have different position
    conf.synthesizer, conf.binary_path, conf.binary_conf = sys.argv[2:]

    driver.main_loop(Core, Controller)
    
if __name__ == "__main__":
    sys.exit(main())
else:
    main()



