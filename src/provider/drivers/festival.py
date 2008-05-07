#!/usr/bin/python

import sys
import select
import socket
import time
import thread

import driver

from ttsapi.structures import *
from ttsapi.errors import *

retrieval_socket = None

class Configuration(driver.Configuration):
    """Configuration class for Festival"""
    # public
    server_host = 'localhost'
    server_port = 1314
    debug_save_output = False
    recode_fallback = '?'
    data_block = 4096
    # private
    retrieval_host = '127.0.0.1'
    retrieval_port = 6576
    
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
        """Open new connection to festival according to configuration"""
        # TODO: Handle festival crashes
        
        self._lock = thread.allocate_lock()

        self._festival_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._festival_socket.connect((socket.gethostbyname(host), port))
        self._festival_socket.setblocking(0) # non-blocking
        # disable Nagles algorithm
        self._festival_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
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

        # festival-freebsoft-utils won't produce any output unless
        # we set voice manually
        self.command("speechd-set-voice", "male1")
        self.command("speechd-set-language", "en")
        
    def close(self):
        self._festival_socket.shutdown(1)
        self._festival_socket.close()
        
        
    def _send(self, data):
        # Send data to socket
        driver.log.debug("Sending to Festival:" + data)
        self._festival_socket.send(data)
        driver.log.debug("Data sent to Festival")
        
    def _read_to_buffer(self):
        """If there are any data on the socket, read them
        to the buffer. Otherwise wait until there is something
        and read it.'"""

        driver.log.debug("Reading to buffer from Festival")
        fd_tuple = [self._festival_socket,]
        sel = select.select(fd_tuple, [],  fd_tuple) # wait for output ready and exceptions
        new_data = self._festival_socket.recv(conf.data_block)
        if len(new_data) == 0:
            driver.log.debug("Raising IO Error 1")
            driver.log.debug("Select returned:" + str(sel))
            driver.log.debug("Data read: |" + new_data + "|")
            # Very mysterious, but this sometimes happens...
            raise IOError
        self._com_buffer += new_data

        driver.log.debug("Now we are sure there is something to read ("+str(self._festival_socket)+")")
        while True:
            sel = select.select(fd_tuple, [], fd_tuple, 0) # non-blocking now
            if sel == ([], [], []):
                return
            driver.log.debug("Reading something from Festival socket in a loop " + str(sel))
            new_data = self._festival_socket.recv(conf.data_block)
            if len(new_data) == 0:
                # I don't know why, but sometimes select returns activity
                # on the socket when in fact there is nothing, and we
                # end up in an infinite loop
                driver.log.debug("Raising IO Error 2")
                driver.log.debug("Select returned:" + str(sel))
                driver.log.debug("Data read: |" + new_data + "|")
                raise IOError
            self._com_buffer += new_data    

    def _read_identifier(self):
        """Read a Festival communication identifier: LP, OK or ER
        from the buffer"""
        
        if len(self._com_buffer) < 3:
            self._read_to_buffer()
        identifier = self._com_buffer[:3]
        self._com_buffer = self._com_buffer[3:]

        driver.log.debug("Received identifier "+identifier)

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
        
        It returns a tuple (reply_code, reply_data, audio_data). If reply_code is 'ER', it also
        raises te FestivalReplyError exception.""" 
        id, audio_data, reply_data = None, None, None
        
        driver.log.debug("Receiving reply from Festival")
        self._read_to_buffer()
        driver.log.debug("Reply read from Festival")
        id = self._read_identifier() # Read LP, OK, or ER
        if (id == 'OK') or (id == 'ER'):
            driver.log.debug("Received from Festival:" + id)
            return (id, None, None)
        
        while (id == 'LP') or (id == 'WV'):
            driver.log.debug("Received from Festival:" + id)
            pointer = self._com_buffer.find('ft_StUfF_key')
            last_id = id
            while pointer == -1:
                self._read_to_buffer()
                pointer = self._com_buffer.find('ft_StUfF_key')
            if id == 'LP':
                reply_data = self._com_buffer[:pointer]
            elif id == 'WV':
                audio_data = self._com_buffer[:pointer]
                
            self._com_buffer = self._com_buffer[pointer+len('ft_StUfF_key') : ]
            id = self._read_identifier()
                
        if (id == 'OK') or (id == 'ER'):
            driver.log.debug("Received data from Festival:" + reply_data)
            if audio_data != None:
                driver.log.debug("Received audio data from Festival: (not listed)")
            driver.log.debug("Received from Festival:" + id)
            return (id, reply_data, audio_data)
        else:
            driver.log.debug("Received from Festival:" + id)
            raise FestivalCommunicationError("Expected ER or OK but got " + id)
        
    def parse_lisp_list(self, lisp_list):
        """Parse a lisp list returned from Festival as a string into a python
        list of individual items.
        
        Arguments:
        lisp_list -- a string containing the lisp list
        """
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
        
        self._lock.acquire()
        self._send(cmd)
        reply = self.receive_reply()
        self._lock.release()
        
        return reply

class Core(driver.Core):

    def __init__(self):
        """Create Festival driver core object"""
        global festival
        festival = FestivalConnection()

    def init(self):
        """Initialize Festival core, connect to Festival server and prepare for speaking"""
        festival.open(host=conf.server_host, port=conf.server_port)

    def quit(self):
        """Terminate connection to festival and quit"""
        driver.log.info("Closing connection to Festival")
        festival.close()
        super(Core, self).quit()

    def drivers(self):
        """Report information about this driver"""
        return DriverDescription(
            driver_id = "festival",
            synthesizer_name = "Festival Speech Synthesizer",
            driver_version = "0.1",
            synthesizer_version = None
            )
    
    def voices(self):
        """Return list of voices"""
        code, voices_string, data = festival.command('voice-list')
        voice_list = voices_string.strip('()\n').split()
        driver.log.debug(str(voice_list))
        reply = []
        for voice_name in voice_list:
            voice = VoiceDescription()
            code, voice_details, data = festival.command('voice.description', (voice_name, 's'))
            voice.name = voice_name
            if voice_details.strip("\n\r ") != 'nil':
                driver.log.debug("'"+str(voice_details)+"'")
                driver.log.debug(str(festival.parse_lisp_list(voice_details)))
                driver.log.debug(str(festival.parse_lisp_list(voice_details)[1]))
                for  entry, value in festival.parse_lisp_list(voice_details)[1]:
                    if entry == 'language':
                        voice.language = value
                    elif entry == 'dialect':
                        voice.dialect = value
                    elif entry == 'gender':
                        voice.gender = value
                    elif entry == 'age':
                        voice.age = int(age)
            else:
                driver.log.warning("Voice description for voice " + voice_name +
                    "missing in Festival reply!");
            reply += [voice]
                
        return reply
    
    def driver_capabilities(self):
        """Return driver capabilities"""
        return DriverCapabilities(
            can_list_voices = True,
            rate_settings = ['relative'],
            pitch_settings = ['relative'],
            punctuation_modes = ['all', 'none', 'some'],
            can_set_punctuation_detail = False,
            capital_letters_modes = ['no', 'spelling', 'icon'],
            can_say_char = True,
            can_say_key = True,
            can_say_icon = True,
            audio_methods = ['retrieval'],
            events = 'message',
            performance_level = 'good',
            message_format = ['ssml'],
            supports_multilingual_utterances = False,
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
        driver.log.debug("Got request to set rate " + method)
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
        else:
            raise ErrorInvalidArgument
            
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
        else:
            raise ErrorInvalidArgument
                
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
            return
            

    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """
        global retrieval_socket
        assert isinstance(host, str)
        assert isinstance(port, int) and port > 0

#        if (retrieval_socket == None
 #           or retrieval_socket.host != host or retrieval_socket.port != port):
        conf.retrieval_host = host
        conf.retrival_port = port
        if retrieval_socket != None:
            retrieval_socket.close()
        retrieval_socket = driver.RetrievalSocket(host=conf.retrieval_host, \
                                                      port=conf.retrieval_port)
        
class Controller(driver.Controller):
    
    def retrieve_data(self, message_id):
    
        def read_item(header, data, type):
            pos = header.find(data)
            nist_type = header[pos+len(data)+2];
            pos_data_begin = header.find(" ", pos+len(data)+2)
            pos_data_end = header.find("\n", pos+len(data)+2)                    
            pos_data = header[pos_data_begin:pos_data_end]
            if nist_type == 'i':
                return int(pos_data)
            elif nist_type == 's':
                return pos_data
    
        block_number = 0
        total_samples = 0
        code, reply_data, audio_data = festival.command('speechd-next')
        last_block = False

        driver.log.info("speechd-next returned code: " + code)
        driver.log.info("speechd-next returned data: " + reply_data)
        while True:
            #driver.log.info("speechd-next returned audio data: " + audio_data)

            if (audio_data == None) or (len(audio_data) == 1024):
                driver.log.info("No audio data for this message, last block")
                last_block = True
            else:
                driver.log.timestamp("Received audio data from Festival")
                if audio_data[:4] != "NIST":
                    driver.log.error("NIST header missing in audio block from festival, skipping")
                    # TODO: Maybe return?
                    continue
                
                audio_NIST_header = audio_data[:1024]
                audio_data_raw = audio_data[1024:]
                #driver.log.info("Audio NIST header follows:\n"+audio_NIST_header)
                sample_rate = read_item(audio_NIST_header, "sample_rate", int)
                sample_count = read_item(audio_NIST_header, "sample_count", int)
                total_samples += sample_count
                sample_byte_format = read_item(audio_NIST_header, "sample_byte_format", str)
                sample_n_bytes = read_item(audio_NIST_header, "sample_n_bytes", int)
                channel_count = read_item(audio_NIST_header, "channel_count", int)
            
            if sample_byte_format == '01':
                endian = 'LE'
            elif sample_byte_format == '10':
                endian = 'BE'
            else:
                driver.log.error("Unknown byte format from Festival, supposing little endian")
                endian = 'LE'
            
            encoding = 'S'+str(8*sample_n_bytes) + '_' + endian

            global retrieval_socket

            if not last_block:
                driver.log.info("Sending " + str(len(audio_data_raw)) + " bytes of audio data for playback")
                event_list = []

            if block_number == 0:
                event_list.append(AudioEvent(type='message_start', pos_text=0,
                                             pos_audio=0))
                                                         
            # Sending datablock to retrieval socket
            retrieval_socket.send_data_block(
                msg_id = message_id, block_number = block_number,
                data_format = "raw",
                audio_length = sample_count/sample_rate*1000,
                audio_data=audio_data_raw,
                sample_rate = sample_rate,
                channels = channel_count,
                encoding = encoding,
                event_list = event_list)
            block_number += 1

            code, reply_data, audio_data = festival.command('speechd-next')
            if (audio_data == None) or (len(audio_data) == 1024):
                driver.log.info("No more data, appending message_end to event list")
                event_list=[]
                event_list.append(AudioEvent(type='message_end', pos_text = 0,
                                             pos_audio = float(total_samples)/sample_rate*1000))
                retrieval_socket.send_data_block(
                    msg_id = message_id, block_number = block_number,
                    data_format = "raw",
                    audio_length = sample_count/sample_rate*1000,
                    audio_data=None,
                    sample_rate = sample_rate,
                    channels = channel_count,
                    encoding = encoding,
                    event_list = event_list)
                return



    def say_text (self, text, format='ssml',
                 position = None, position_type = None,
                 index_mark = None, character = None, message_id = None):
        """Say text using Festivals (SayText ...) method"""

        if message_id == None:
            raise """Invalid message_id None"""        
        if len(text) == 0: return
        if format != 'ssml': raise ErrorNotSupportedByDriver
    
        escaped_text = text.replace('\\','\\\\').replace('"', '\\\"')
        
        driver.log.timestamp("Sending synthesis request to Festival")

        # Ask for synthesis
        try:
            festival.command("speechd-speak-ssml", escaped_text)
        except:
            driver.log.error("SayText unsuccessful with text: |" + text + "|")
            return

        # Retrieve data and listen for stop events
        try:
            self.retrieve_data(message_id = message_id)
        except FestivalError:
            driver.log.error("Couldn't retrieve audio data.");
        
        return message_id
        
    def say_key (self, key, message_id=None):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        if message_id == None:
            raise """Invalid message_id None"""        
        try:
            festival.command("speechd-key", key)
        except:
            driver.log.error("speechd-key unsuccessful with key: |" + key + "|")

        # Retrieve data and listen for stop events
        try:
            self.retrieve_data(message_id = message_id)
        except:
            driver.log.error("Couldn't retrieve audio data.");
        
        return message_id
        
    def say_char (self, character, message_id=None):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        if message_id == None:
            raise """Invalid message_id None"""        
        try:
            festival.command("speechd-character", character)
        except:
            driver.log.error("speechd-character unsuccessful with: |" + character + "|")

        # Retrieve data and listen for stop events
        try:
            self.retrieve_data(message_id = message_id)
        except:
            driver.log.error("Couldn't retrieve audio data.");
        
        return message_id
        
    def say_icon (self, icon, message_id=None):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)
        if message_id == None:
            raise """Invalid message_id None"""        
        try:
            festival.command("speechd-sound-icon", (icon, 's'))
        except:
            driver.log.error("speechd-sound-icon unsuccessful with: |" + icon + "|")

        # Retrieve data and listen for stop events
        try:
            self.retrieve_data(message_id = message_id)
        except:
            driver.log.error("Couldn't retrieve audio data.");
        
        return message_id
        
    def cancel (self):
        """Cancel current synthesis process and audio output."""

        #Here we should somehow terminate synthesis when it will be possible
        #in Festival
        pass
        
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

    
