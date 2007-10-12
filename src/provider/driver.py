#
# driver.py - Synthesis driver skeleton
#   
# Copyright (C) 2006, 2007 Brailcom, o.p.s.
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
# $Id: driver.py,v 1.7 2007-10-12 08:37:45 hanke Exp $
 
"""TTS API driver logic"""

import sys
import thread
import threading
import time
import logging
import socket
import ttsapi
from copy import copy

import event
import audio

from ttsapi.structures import *
from ttsapi.errors import *


class CtrlRequest(event.Event):
    _attributes = {
        'type': ("Type of the event",
                 ("say_text", "say_deferred", "say_char","say_key", "say_icon",
                  "cancel", "defer", "discard", "quit")),
        'text': ("Text of message",  ("say_text","say_key", "say_char", "say_icon")),
        'format': ("Format of the message", ("say_text",)),
        'position': ("Position in text", ("say_text", "say_deferred")),
        'position_type': ("Type of position", ("say_text", "say_deferred")),
        'index_mark': ("Index mark position", ("say_text", "say_deferred")),
        'character': ("Character position", ("say_text", "say_deferred")),
        'message_id': ("ID of the message", ("say_text", "say_deferred", "say_char",
                                             "say_key", "say_icon", "cancel", "defer",
                                             "discard"))
    }


# Log, initialized in main_loop or by the driver
log = None


class RetrievalSocket(object):
    """Class for handling the TTS API audio retrieval socket from inside the driver."""
    host = None
    port = None
    
    def __init__(self, host, port):
        """Open socket to target or raise exception if impossible
        host -- host name or IP address as a string
        port -- a number representing the desired port"""
        assert isinstance(host, str)
        assert isinstance(port, int)
        self.host = host
        self.port = port

        self._lock = thread.allocate_lock()

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.connect((socket.gethostbyname(host), port))

    def close(self):
        """Close the socket"""
        self._socket.close()
        
    def send_data_block(self, msg_id, block_number,
        data_format, audio_length, audio_data,
        sample_rate = None, channels = None, encoding = None,
        event_list = None):
        """Send a block of data on the retrieval socket, arguments
        as defined in TTS API specifications"""
        data_length = len(audio_data)
        assert isinstance(msg_id, int) and msg_id >= 0
        assert isinstance(block_number, int) and block_number >= 0
        assert isinstance(data_format, str)
        assert isinstance(data_length, int)
        assert isinstance(audio_length, int)
        assert isinstance(sample_rate, int) or sample_rate == None
        assert isinstance(channels, int) or channels == None
        assert isinstance(encoding, str) or encoding == None
        assert isinstance(event_list, list) or event_list == None
        
        ENDLINE = "\r\n"
        
        # BLOCK identification and PARAMETERS block
        message = ("BLOCK " + str(msg_id) + " " + str(block_number) + ENDLINE
         + "PARAMETERS" + ENDLINE
         + "data_format "+data_format+ENDLINE
         + "data_length "+str(data_length)+ENDLINE
         + "audio_lenth "+str(audio_length)+ENDLINE)
         
        if sample_rate:
            message += "sample_rate "+str(sample_rate)+ENDLINE
        if channels:
            message += "channels "+str(channels)+ENDLINE
        if encoding:
            message += "encoding "+encoding+ENDLINE
        message += "END OF PARAMETERS" + ENDLINE
        
        # EVENTS block
        if event_list != None and len(event_list)!=0:
            message += "EVENTS"+ENDLINE
            for event in event_list:
                code, event_line = \
                      ttsapi.server.tcp_format_event(event)
                message += event_line+ENDLINE
            message += "END OF EVENTS" + ENDLINE
            
        # DATA block
        message += "DATA"+ENDLINE
        message += audio_data
        message += "END OF DATA"+ENDLINE
        
        # send it
        self._lock.acquire()
        total_bytes = len(message)
        bytes_sent = 0
        try:
            while bytes_sent < total_bytes:
                bytes_sent += self._socket.send(message[bytes_sent:])
                log.debug("Sent " + str(bytes_sent) + " out of " + str(total_bytes) + " data len" + str(len(audio_data)))
        finally:
            self._lock.release()
    
class Core(object):
    """Core of the driver, takes care of TTS API communication etc."""

    controller = None
    _message_id = None
    
    def __init__ (self):
        """Initialize the instance"""
    # Initialization

    def set_controller(self, controller):
        """Set the controller object. Its run() method will be started
        in a separate thread. See Controller for more information.
        
        This method must be run before the Core.init() method."""
        self.controller = controller

    def init(self):
        """Init the driver, start the Controller thread etc."""
        if self.controller != None:
            log.info("Starting the controller thread.")
            thread.start_new_thread(self.controller.run, ())

    def quit(self):
        """Terminate the driver"""
        log.info("Terminating");
        ctrl_thread_requests.push(CtrlRequest(type='quit'))
        
        log.debug("Joining controller thread");
        self.controller.join()
        log.debug("End of quit in core");
        
    # Driver discovery

    def drivers(self):
        """Report information about this driver"""
        return DriverDescription()
    
    def driver_capabilities (self):
        """Return a DriverCapabilities object for the
        given driver.

        Arguments:
        """
        return DriverCapabilities()

    def voices (self):
        """Return a list of voices available to the given
        driver as a list of VoiceDescription objects.

        Arguments:
        driver_id -- identification of the driver
        """
        raise ErrorNotSupportedByDriver

    # Speech Synthesis commands

    def say_text (self, text, format='plain',
                  position = None, position_type = None,
                  index_mark = None, character = None):
        """Send the synthesis request to the Controller thread.

        Arguments:
        format -- either 'plain' or 'ssml'
        text -- text of the message in unicode

        For Event based positioning:
        position -- a positive number indicating the position
        position_type -- one of: 'message_begin', 'sentence_start',
        'sentence_end', 'word_start', 'word_end'

        For Index marker based positioning:
        index_mark -- name of the index mark where synthesis
        should start

        For Character based positioning:
        position -- a positive value indicating the position
        of character where synthesis should start          
        """
        assert isinstance(text, str)
        assert format in ('plain', 'ssml')
        assert position == None or isinstance(position, int)
        assert position_type in (None, 'message_begin', 'sentence_start',
                                 'sentence_end', 'word_start', 'word_end')
        assert index_mark == None or isinstance(index_mark, str)
        assert character == None or isinstance(character, int)
        
        if not self.controller:
            raise ErrorNotSupportedByDriver
        
        ctrl_thread_requests.push(
            CtrlRequest(type='say_text', text=text, format=format, position=position,
            position_type=position_type, index_mark = index_mark, character = character,
                  message_id=self._message_id))
        #self._message_id = None
        
        return self._message_id
      
    def say_deferred (self, message_id,
                      format='plain',
                      position = None, position_type = None,
                      index_mark = None, character = None):        
        """Send the synthesis request to the controller thread.

        Arguments:
        message_id -- unique identification number of the message

        For the meaning of other arguments please see say_text()
        """
        assert isinstance(message_id, int)
        assert position == None or isinstance(position, int)
        assert position_type in (None, 'message_begin', 'sentence_start',
                                 'sentence_end', 'word_start', 'word_end')
        assert index_mark == None or isinstance(index_mark, str)
        assert character == None or isinstance(character, int)

        if not self.controller:
            raise ErrorNotSupportedByDriver
      
        ctrl_thread_requests.push(
            CtrlRequest(type='say_deferred', message_id=message_id, position=position, 
            position_type=position_type, index_mark = index_mark, character = character))        
    
        
    def say_key (self, key):
        """Send the key synthesis request to the controller thread.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        assert isinstance(key, str)
        
        if not self.controller:
            raise ErrorNotSupportedByDriver
        
        ctrl_thread_requests.push(
            CtrlRequest(type='say_key', text=key, message_id=self._message_id))
        #self._message_id = None
        
        return self._message_id
        
    def say_char (self, character):
        """Send the character synthesis request to the controller thread.

        Arguments:
        character -- a single UTF-32 character.          
        """
        assert len(character) == 1
        if not self.controller:
            raise ErrorNotSupportedByDriver
        
        ctrl_thread_requests.push(
            CtrlRequest(type='say_char', text=character, message_id=self._message_id))
        #self._message_id = None
        
        return self._message_id
        
    def say_icon (self, icon):
        """Send the sound icon synthesis request to the controller thread.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)

        if not self.controller:
            raise ErrorNotSupportedByDriver
        
        ctrl_thread_requests.push(
            CtrlRequest(type='say_icon', text=icon, message_id=self._message_id))
        #self._message_id = None
        
        return self._message_id
        
    # Speech Controll commands

    def cancel (self):
        """Cancel current synthesis process and audio output.
        Sends the request to the controller thread."""
        if not self.controller:
            raise ErrorNotSupportedByDriver
        ctrl_thread_requests.push(CtrlRequest(type='cancel'))
    
    def defer (self):
        """Defer current message. Sends the defer request to the controller thread."""        
        if not self.controller:
            raise ErrorNotSupportedByDriver
        ctrl_thread_requests.push(CtrlRequest(type='defer'))
        
    def discard (self, message_id):
        """Discard a previously deferred message.
        Sends the discard request to the controller thread.
        Arguments:
        message_id -- unique identification of the message to discard          
        """
        assert isinstance(message_id, int)
        if not self.controller:
            raise ErrorNotSupportedByDriver
        ctrl_thread_requests.push(CtrlRequest(type='discard', message_id=message_id))
        
    # Parameter settings

    ## Driver selection

    def set_driver(self, driver_id):
        """Set driver

        Arguments:
        driver_id -- id of the driver as returned by drivers()
        """
        assert isinstance(driver_id, str)
        raise ErrorNotSupportedByDriver

    def set_message_id(self, message_id):
        """Set the identification number for the next message"""
        self._message_id = message_id
        
    ## Voice selection

    def set_voice_by_name(self, voice_name):
        """Set voice.

        Arguments:
        voice_name -- name of a voice as obtained by voices()          
        """
        assert isinstance(voice_name, str)
        raise ErrorNotSupportedByDriver
        
    def set_voice_by_properties(self, voice_description, variant):
        """Choose and set a voice best matching the given description.

        Arguments:
        voice_description -- VoiceDescription object
        variant -- a positive number meaning variant
        of the voice from those matching voice_description          
        """
        assert isinstance(voice_description, VoiceDescription)
        assert isinstance(variant, int)

        raise ErrorNotSupportedByDriver
        
    def current_voice(self):
        """Return VoiceDescription of the current voice."""
        raise ErrorNotSupportedByDriver
        

    ## Prosody parameters
        
    def set_rate(self, rate, method='relative'):
        """Set relative or absolute rate.

        Arguments:
        rate -- desired rate change with respect to default represented
        as a number in percents for relative change or as a positive number
        in words per minute for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(rate, int)
        raise ErrorNotSupportedByDriver
        
    def default_absolute_rate(self):
        """Returns default absolute rate for the given voice
        as a positive number in words per minute.
        """
        raise ErrorNotSupportedByDriver
        
    def set_pitch(self, pitch, method='relative'):
        """Set relative or absolute pitch.

        Arguments:
        pitch -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(pitch, int)
        raise ErrorNotSupportedByDriver
        
    def default_absolute_pitch(self):
        """Returns default absolute pitch for the given voice
        as a positive number in Hertzs.
        """
        raise ErrorNotSupportedByDriver
        
    def set_pitch_range(self, range, method='relative'):
        """Set relative or absolute pitch range.

        Arguments:
        range -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(range, int)
        raise ErrorNotSupportedByDriver
        
    def set_volume(self, volume, method='relative'):
        """Set relative or absolute volume.

        Arguments:
        volume -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        between 0 and 100 for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(volume, int)
        pass
        
    def default_absolute_volume(self):
        """Returns default absolute volume for the given voice
        as a positive number between 0 and 100.
        """
        assert len(data) > 0
        raise ErrorNotSupportedByDriver

    ## Style parameters

    def set_punctuation_mode(self, mode):
        """Set punctuation reading mode.


        Arguments:
        mode -- one of 'none', 'all', 'some'          
        """
        assert mode in ('none', 'all', 'some')
        raise ErrorNotSupportedByDriver

    def set_punctuation_detail(self, detail):
        """Set punctuation detail.

        Arguments:
        detail -- a list of punctuation characters that
        should be explicitly indicated by the synthesizer          
        """
        assert isinstance(detail, str)
        raise ErrorNotSupportedByDriver

    def set_capital_letters_mode(self, mode):
        """Set mode for reading capital letters.

        Arguments:
        mode -- one of 'no', 'spelling', 'icon', 'pitch'          
        """
        assert mode in ('no', 'spelling', 'icon', 'pitch')
        raise ErrorNotSupportedByDriver

    def set_number_grouping(self, grouping):
        """Set grouping of digits for reading numbers.
        Arguments:
        grouping -- 0 for default or a positive value
        specifying how many digits should be read together          
        """
        assert isinstance(grouping, int)
        raise ErrorNotSupportedByDriver

    # Dictionaries
    
    def set_dictionary(self):
        """Set user dictionary. Exact behavior yet undefined."""
        raise ErrorNotSupportedByDriver

    # Audio Output
    
    def set_audio_output(self, method='playback'):
        """Set audio output method as described in TTS API.

        Arguments:
        method -- one of 'playback', 'retrieval'          
        """
        assert method in ('playback', 'retrieval')
        
        if method == 'playback':
            return
        else: # method == retrieval
            raise ErrorNotSupportedByDriver

    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """
        assert isinstance(host, str)
        assert isinstance(port, int) and port > 0
        raise ErrorNotSupportedByDriver

    def register_callback(self, connection, function):
        """Register callback (do nothing by default)"""

        pass


# ----------------------------------------------------------------

class Controller(threading.Thread):
    """Controlls the speech synthesis process in a separate thread"""

    def __init__(self):
        global ctrl_thread_requests

        ctrl_thread_requests = event.EventPot()
        threading.Thread.__init__(self, name="Controller")
        self.start()
        
    def run(self):
        log.debug("Driver thread running!")
        while True:
            e = ctrl_thread_requests.pop()
            if e.type == 'say_text':
                self.say_text(e.text, e.format, e. position, e.position_type,
                              e.index_mark, e.character, e.message_id)
            elif e.type == 'say_deferred':
                self.say_deferred(e.message_id, e. position, e.position_type,
                                  e.index_mark, e.character)
            elif e.type == 'say_char':
                self.say_char(e.text, e.message_id)
            elif e.type == 'say_key':
                self.say_key(e.text, e.message_id)
            elif e.type == 'say_icon':
                self.say_icon(e.text, e.message_id)
            elif e.type == 'cancel':
                self.cancel()
            elif e.type == 'defer':
                self.defer()
            elif e.type == 'discard':
                self.discard(e.message_id)
            elif e.type == 'quit':
                self.quit()
            else:
                raise "Unknown event type"

    def quit(self):
        """Quit"""
        thread.exit()
    
    def say_text (self, text, format='plain',
                 position = None, position_type = None,
                 index_mark = None, character = None):
        """Synthesize the whole message of given format
        from the given position.

        Arguments:
        format -- either 'plain' or 'ssml'
        text -- text of the message in unicode

        For Event based positioning:
        position -- a positive number indicating the position
        position_type -- one of: 'message_begin', 'sentence_start',
        'sentence_end', 'word_start', 'word_end'

        For Index marker based positioning:
        index_mark -- name of the index mark where synthesis
        should start

        For Character based positioning:
        position -- a positive value indicating the position
        of character where synthesis should start          
        """
        assert isinstance(text, str)
        assert format in ('plain', 'ssml')
        assert position == None or isinstance(position, int)
        assert position_type in (None, 'message_begin', 'sentence_start',
                                 'sentence_end', 'word_start', 'word_end')
        assert index_mark == None or isinstance(index_mark, str)
        assert character == None or isinstance(character, int)

        raise ErrorNotSupportedByDriver
        
        
    def say_deferred (self, message_id,
                      position = None, position_type = None,
                      index_mark = None, character = None):        
        """Synthesize the whole message deffered message.

        Arguments:
        message_id -- unique identification number of the message

        For the meaning of other arguments please see say_text()
        """
        assert isinstance(message_id, int)
        assert position == None or isinstance(position, int)
        assert position_type in (None, 'message_begin', 'sentence_start',
                                 'sentence_end', 'word_start', 'word_end')
        assert index_mark == None or isinstance(index_mark, str)
        assert character == None or isinstance(character, int)

        print "say_deferred called with message_id " + str(message_id) \
              + " position " + str(position) + " pos_type " \
              + str(position_type) + " index mark " + str(index_mark) + " character "  \
              + str(character)
        raise ErrorNotSupportedByDriver

    def say_key (self, key):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        assert isinstance(key, str)
        raise ErrorNotSupportedByDriver
        
    def say_char (self, character):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        assert len(character) == 1
        raise ErrorNotSupportedByDriver
        
    def say_icon (self, icon):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)
        raise ErrorNotSupportedByDriver
        
    def cancel (self):
        """Cancel current synthesis process and audio output."""
        raise ErrorNotSupportedByDriver
        
    def defer (self):
        """Defer current message."""
        raise ErrorNotSupportedByDriver
        
    def discard (self, message_id):
        """Discard a previously deferred message.

        Arguments:
        message_id -- unique identification of the message to discard          
        """
        assert isinstance(message_id, int)
        raise ErrorNotSupportedByDriver
        
    # Parameter settings

class Configuration(object):
    pass
    

def EventCallback(connection, event):
    connection.send_audio_event(event)

def main_loop(Core, Controller):
    """Main function and core read-process-notify loop of a driver"""
    global log
    
    # Initialize logging to stderr.
    log = logging.Logger('tts-api-driver', level=logging.DEBUG)
    log_formatter = logging.Formatter("%(asctime)s %(threadName)s %(levelname)s %(message)s")
    log_handler = logging.StreamHandler(sys.stderr)
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)
    
    # Initialize driver Core
    driver_core = Core()
    # Initialize driver controller and attach it to the Core
    if Controller != None:
        driver_core.set_controller(Controller())

    # Create communication interface as TTS API server
    # over text protocol pipes (stdin, stdout, stderr)
    driver_comm = ttsapi.server.TCPConnection(provider=driver_core,
                                              logger=log, method='pipe')

    driver_comm.provider.register_callback(driver_comm, EventCallback)

    while True:
        # Process input, call appropriate Core and Controller functions
        # according to TTS API specifications
        try:
            driver_comm.process_input()
        except ttsapi.server.ClientGone:
            log.info("Client gone, terminating")
            return
