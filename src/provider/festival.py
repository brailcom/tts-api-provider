#!/usr/bin/env python

import sys
import select
import socket

import driver

from ttsapi.structures import *
from ttsapi.errors import *

class Configuration(driver.Configuration):
    """Configuration class"""
    # public
    server_host = 'localhost'
    server_port = 1314
    debug_save_output = False
    recode_fallback = '?'
    data_block = 4096
    # private
    retrieval_host = None
    retrieval_port = None
    
conf = Configuration()

class FestivalError(Exception):
    """Error in Festival"""

    def __init__(self, description=None):
        self.description = description
    
class FestivalCommunicationError(FestivalError):
    """Bad reply from Festival"""

class FestivalReplyError(FestivalError):
    """Festival returned the 'ER' reply"""
    
class FestivalConnection(object):
    """Connection to festival"""
    
    def open(self,host="localhost", port=1314):
        """Open new festival to festival according to configuration"""
        # Handle festival crashes
        self._festival_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._festival_socket.connect((socket.gethostbyname(host), port))
        self._festival_socket.setblocking(0) # non-blocking
        self._com_buffer = ""
        try:
            self.command("require", ("speech-dispatcher", 's'))
        except FestivalReplyError:
           driver.log.error("festival-freebsoft-utils missing in Festival")
           sys.exit(1)
        try:
            self.command("speechd-enable-multi-mode", ("t", 's'))
        except FestivalReplyError:
            driver.log.error("""Multi mode not supported in Festival, it seems you are
            using an old release of festival-freebsoft-utils""")
            sys.exit(1)
        
    def _send(self, data):
        # Send data to socket
        driver.log.debug("Sending to Festival:" + data)
        self._festival_socket.send(data)
        
    def _read_to_buffer(self):
        """If there are any data on the socket, read them
        to the buffer. Otherwise wait until there is something
        and read it.'"""
        
        fd_tuple = [self._festival_socket,]
        select.select(fd_tuple, [],  fd_tuple) # wait for output ready and exceptions
        self._com_buffer += self._festival_socket.recv(conf.data_block)
        while select.select(fd_tuple, [], fd_tuple, 0)  != ([],[],[]): # non-blocking now
            self._com_buffer += self._festival_socket.recv(conf.data_block)
    
    def _read_identifier(self):
        """Read a Festival communication identifier: LP, OK or ER
        from the buffer"""
        
        if len(self._com_buffer) < 3:
            self._read_to_buffer()
        identifier = self._com_buffer[:3]
        self._com_buffer = self._com_buffer[3:]
        
        if (identifier == 'ER\n'):
            raise FestivalReplyError;
            return 'ER'
        elif (identifier == 'LP\n'):
            return 'LP'
        elif (identifier == 'WV\n'):
            return 'WV'
        elif (identifier == 'OK\n'):
            return 'OK'
        else:
            raise FestivalCommunicationError("Unknown reply identifier " + identifier) 
    
    def receive_reply(self):
        """Read data (at least one byte or block) and receive a reply from festival,
        including reply identification, reply data and the trailing reply
        status information.
        
        It returns a tuple (reply_data, reply_code). If reply_code is 'ER', it also
        raises te FestivalReplyError exception.""" 
    
        self._read_to_buffer()
        id = self._read_identifier() # Read LP, OK, or ER
        if (id == 'OK') or (id == 'ER'):
            driver.log.debug("Received from Festival:" + id)
            return (None, id)
        elif (id == 'LP') or (id == 'WV'):
            driver.log.debug("Received from Festival:" + id)
            pointer = self._com_buffer.find('ft_StUfF_key')
            last_id = id
            while pointer == -1:
                self._read_to_buffer()
                pointer = self._com_buffer.find('ft_StUfF_key')
            data = self._com_buffer[:pointer]
            self._com_buffer = self._com_buffer[pointer+len('ft_StUfF_key') : ]
            id = self._read_identifier()
            if (id == 'OK') or (id == 'ER'):
                if last_id != 'WV':
                    driver.log.debug("Received data from Festival:" + data)
                else: # we have audio data
                    driver.log.debug("Received audio data")
                driver.log.debug("Received from Festival:" + id)
                return (data, id)
            else:
                driver.log.debug("Received from Festival:" + id)
                raise FestivalCommunicationError("Expected ER or OK but got " + id)
        
    def parse_lisp_list(self, lisp_list):
        result = []
        temp = lisp_list.strip()
        if len(temp) == 0: return
        if temp[0] == '(':
            temp = temp[1:]
            if temp[-1] == ')':
                temp = temp[:-1]
            else:
                raise "Syntax error in parse_lisp_list"
        else: # an atom already
            return lisp_list
        
        level, last_pos = 0, 0
        quotes = False
        for i in range(0, len(temp)-1):
            if (temp[i] == '"'):
                quotes = not quotes
            if level == 0 and not quotes and (temp[i] == ' '
                    or  (i>0 and temp[i-1]==')' and temp[i] == '(')):
                result += [self.parse_lisp_list(temp[last_pos:i].strip())]
                last_pos = i
            elif temp[i] == '(':
                level+=1
            elif temp[i] == ')':
                level -=1
            if level < 0:
                raise "Syntax error in parse_lisp_list, unbalanced parenthesis"
        result += [self.parse_lisp_list(temp[last_pos:].strip())]
        return result
        
    def command(self, command, *arg_list):
        """Send the specified command with the given arguments
           and return the reply as a tuple (reply_data, reply_code).
            
        Arguments:
        command -- a string with the command to execute
        arg_list -- a tuple with arguments as strings or numbers or tuples.
                        If the argument is a tuple, it has the form (arg, type) where
                        type is 's' for symbols."""
            
        cmd  = "(" + command
        for a in arg_list:
            if isinstance(a, str):
                cmd += " " + '"' + a + '"'
            elif isinstance(a, tuple):
                a[1] == 's'
                cmd += " " + "'" + a[0]
            else:
                cmd += " " + str(a)
        cmd += ")\n"
            
        self._send(cmd)
        return self.receive_reply()
        
class Core(driver.Core):

    def __init__(self):
        """Create Festival driver core object"""
        global festival
        festival = FestivalConnection()

    def init(self):
        """Initialize Festival core, connect to Festival server and prepare for speaking"""
        festival.open(host=conf.server_host, port=conf.server_port)
    
    def drivers(self):
        """Report information about this driver"""
        return DriverDescription(
            driver_id = "festival",
            synthesizer_name = "Festival Speech Synthesizer",
            driver_version = "0.0",
            synthesizer_version = None
            )
    
    def voices(self):
        """Return list of voices"""
        voices_string, code = festival.command('voice-list')
        voice_list = voices_string.strip('()\n').split()
        
        reply = []
        for voice_name in voice_list:
            voice = VoiceDescription()
            voice_details, code = festival.command('voice.description', voice_name)
            voice.name = voice_name
            for  entry, value in festival.parse_lisp_list(voice_details)[1]:
                if entry == 'language':
                    voice.language = value
                elif entry == 'dialect':
                    voice.dialect = value
                elif entry == 'gender':
                    voice.gender = value
                elif entry == 'age':
                    voice.age = int(age)
            reply += [voice]
        return reply
    
    def driver_capabilities(self):
        """Return driver capabilities"""
        return DriverCapabilities(
            can_list_voices = True,
            rate_settings = ['relative'],
            pitch_settings = ['relative'],
            punctuation_modes = ['all', 'none', 'some'],
            can_set_punctuation_detail = True,
            capital_letters_modes = ['no', 'spelling', 'icon'],
            can_say_char = True,
            can_say_key = True,
            can_say_icon = True,
            audio_methods = ['retrieval'],
            #events = 'index_marks',
            performance_level = 'good',
            can_parse_ssml = True,
            supports_multilingual_utterances = False
           )
           
    def set_voice_by_name(self, voice_name):
        """Set voice.

        Arguments:
        voice_name -- name of a voice as obtained by voices()          
        """
        assert isinstance(voice_name, str)
        festival.command("speechd-set-voice", voice_name)
    
    def set_voice_by_properties(self, voice_description, variant):
        """Choose and set a voice best matching the given description.

        Arguments:
        voice_description -- VoiceDescription object
        variant -- a positive number meaning variant
        of the voice from those matching voice_description          
        """
        assert isinstance(voice_description, VoiceDescription)
        assert isinstance(variant, int)
        
        def _add_args(args, value, symbol=False):
            if value != None:
                if symbol:
                    args += [value]
                else:
                    args += [(value, 's')]
            else:
                args += ['nil']
            return args
        
        #TODO: This is currently broken since Festival
        #expects language name in English, while we are
        #sending ISO language code. Hope this gets fixed
        #in festival-freebsoft-utils.
        args = []
        args = _add_args(args, voice_description.language)
        args = _add_args(args, voice_description.dialect)
        args = _add_args(args, voice_description.gender, symbol=True)
        args = _add_args(args, voice_description.age)
        args = _add_args(args, variant)
        args = _add_args(args, voice_description.name)
    
        festival.command("speechd-select-voice", *args)
    
    def current_voice(self):
        """Return VoiceDescription of the current voice."""
        #TODO:
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
            raise ErrorNotSupportedByDriver
        elif method == 'relative':
            try:
                # TODO: black magic, needs support in Festival
                frate = rate
                if frate >= 500: frate = 500
                if frate <= -500: frate = -500
                # frate in (-500:500)
                festival.command("speechd-set-rate", frate/5)
            except FestivalReplyError:
                driver.log.error("Festival can't set desired " + method + "TTS API rate " + str(rate))
        
    def set_pitch(self, pitch, method='relative'):
        """Set relative or absolute pitch.

        Arguments:
        pitch -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(pitch, int)
        if method == 'absolute':
            raise ErrorNotSupportedByDriver
        elif method == 'relative':
            try:
                # TODO: black magic, needs support in Festival
                fpitch = pitch
                if fpitch >= 500: fpitch = 500
                if fpitch <= -500: fpitch = -500
                # fpitch in (-500:500)
                festival.command("speechd-set-pitch", fpitch/5)
            except FestivalReplyError:
                driver.log.error("Festival can't set desired " + method + "TTS API pitch " + str(pitch))
                
    ## Style parameters

    def set_punctuation_mode(self, mode):
        """Set punctuation reading mode.
        
        Arguments:
        mode -- one of 'none', 'all', 'some'          
        """
        assert mode in ('none', 'all', 'some')
        try:
            festival.command("speechd-set-punctuation-mode",  (mode, 's'))
        except:
            driver.log.error("Festival can't set desired punctuation mode" + mode)
            
    def set_capital_letters_mode(self, mode):
        """Set mode for reading capital letters.

        Arguments:
        mode -- one of 'no', 'spelling', 'icon', 'pitch'          
        """
        assert mode in ('no', 'spelling', 'icon', 'pitch')
        #TODO: mode 'pitch' is currently not supported in Festival
        fmode = mode
        if fmode == 'no':
            fmode = 'none'
        try:
            festival.command("speechd-set-capital-character-recognition-mode",
                (mode, 's'))
        except:
            driver.log.error("Festival can't set desired punctuation mode" + mode)

    def set_audio_output(self, method='playback'):
        """Set audio output method as described in TTS API.

        Arguments:
        method -- one of 'playback', 'retrieval'          
        """
        assert method in ('playback', 'retrieval')
        
        if method == 'playback':
            raise ErrorNotSupportedByDriver
        else: # method == retrieval
            return; # Retrieval is the default and only option for this driver

    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """
        assert isinstance(host, str)
        assert isinstance(port, int) and port > 0
        conf.retrieval_host = host
        conf.retrival_port = port

class Controller(driver.Controller):
    
    def retrieve_data(self):
    # TODO: retrieve data, send them to the desired output, etc.
#        while True:
 #           data, code = festival.command('speechd-next')
    
    def say_text (self, text, format='ssml',
                 position = None, position_type = None,
                 index_mark = None, character = None):
        """Say text using Festivals (SayText ...) method"""
        
        if len(text) == 0: return
        if format == 'plain': raise ErrorNotSupportedByDriver
        
        # TODO: This is only method PLAYBACK, RETRIEVAL is desired
        # see festival.c in Speech Dispatcher
        escaped_text = text.replace('\\','\\\\').replace('"', '\\\"')
        
        # Ask for synthesis
        try:
            festival.command("speechd-say-ssml", escaped_text)
        except:
            driver.log.error("SayText unsuccessful with text: |" + text + "|")

        # Retrieve data and listen for stop events
        self.retrieve_data()
        
    def say_key (self, key):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        try:
            festival.command("speechd-key", key)
        except:
            driver.log.error("speechd-key unsuccessful with key: |" + key + "|")

        # Retrieve data and listen for stop events
        self.retrieve_data()
        
    def say_char (self, character):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        try:
            festival.command("speechd-character", character)
        except:
            driver.log.error("speechd-character unsuccessful with: |" + character + "|")

        # Retrieve data and listen for stop events
        self.retrieve_data()
        
    def say_icon (self, icon):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)
        try:
            festival.command("speechd-icon", (icon, 's'))
        except:
            driver.log.error("speechd-icon unsuccessful with: |" + icon + "|")

        # Retrieve data and listen for stop events
        self.retrieve_data()
        
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
        
def main():
    """Main loop for driver code"""
    driver.main_loop(Core, Controller)
    
if __name__ == "__main__":
    sys.exit(main())
else:
    main()

    
