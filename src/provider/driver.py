import sys
import threading
import time
import logging
import ttsapi
from copy import copy

from ttsapi.structures import *
from ttsapi.errors import *

# Log, initialized in main_loop or by the driver
log = None

class RetrievalSocket(object):
    _host = None
    _port = None
    
    def open(self, host, port):
        """Open socket to target or raise exception if impossible
        host -- host name or IP address as a string
        port -- a number representing the desired port"""
        assert isinstance(host, str)
        assert isinstance(port, int)
        self. _host = host
        self._port = port

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        assert isinstance(data_format, string)
        assert isinstance(data_length, int)
        assert isinstance(audio_length, int)
        assert isinstance(sample_rate, int) or sample_rate == None
        assert isinstance(channels, int) or channels == None
        assert isinstance(encoding, str) or encoding == None
        assert isinstance(event_list, list) or event_list == None
        
        ENDLINE = "\r\n"
        
        # BLOCK identification and PARAMETERS block
        message = ("BLOCK " + msg_id + " " + block_number + ENDLINE
         + "PARAMETERS" + ENDLINE
         + "data_format="+data_format+ENDLINE
         + "data_length="+data_length+ENDLINE
         + "audio_lenth="+audio_length+ENDLINE)
         
        if sample_rate:
            message += "sample_rate="+sample_rate+ENDLINE
        if channels:
            message += "channels="+channels+ENDLINE
        if encoding:
            message += "encoding="+encoding+ENDLINE
        message += "END OF PARAMETERS" + ENDLINE
        
        # EVENTS block
        message += "EVENTS"+ENDLINE
        for type, text_position, audio_position in events:
            message += type + text_position + audio_position + ENDLINE
        message += "END OF EVENTS"+ENDLINE
        
        # DATA block
        message += "DATA"+ENDLINE
        message += audio_data
        message += "END OF DATA"+ENDLINE
        
        # send it
        self._socket.send(message)
        
class Core(object):
    """Core of the driver, takes care of TTS API communication etc."""

    controller = None
    
    def __init__ (self):
        """Initialize the instance"""
    # Initialization

    def set_controller(self, controller):
        self.controller = controller
        
    def init(self):
        """Init the driver (connecto to server etc.)"""
        thread.start_new_thread(self.controller.run, ())
        
    # Driver discovery

    def drivers(self):
        """Report information about this driver"""
        return DriverDescription
    
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
        
        if not self.controller:
            raise ErrorNotSupportedByDriver
            
        event.set(type='say_text', text=text, format=format, position=position,
            position_type=position_type, index_mark = index_mark, character = character)
        event_ctl.set()
      
    def say_deferred (self, message_id,
                      format='plain',
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

        if not self.controller:
            raise ErrorNotSupportedByDriver
      
        event.set(type='say_deferred', message_id=message_id, position=position, 
            position_type=position_type, index_mark = index_mark, character = character)
        event_ctl.set()
        
    def say_key (self, key):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        assert isinstance(key, str)
        
        if not self.controller:
            raise ErrorNotSupportedByDriver
        event.set(type='say_key', key=key)
        event_ctl.set()
        
    def say_char (self, character):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        assert len(character) == 1
        if not self.controller:
            raise ErrorNotSupportedByDriver
      
        event.set(type='say_char', key=key)
        event_ctl.set()
        
    def say_icon (self, icon):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)
        
        if not self.controller:
            raise ErrorNotSupportedByDriver
        event.set(type='say_icon', icon=icon)
        event_ctl.set()
        
    # Speech Controll commands

    def cancel (self):
        """Cancel current synthesis process and audio output."""
        if not self.controller:
            raise ErrorNotSupportedByDriver
        event.set(type='cancel')
        event_ctl.set()
    
    def defer (self):
        """Defer current message."""        
        if not self.controller:
            raise ErrorNotSupportedByDriver
        event.set(type='defer')
        event_ctl.set()
        
    def discard (self, message_id):
        """Discard a previously deferred message.

        Arguments:
        message_id -- unique identification of the message to discard          
        """
        assert isinstance(message_id, int)
        if not self.controller:
            raise ErrorNotSupportedByDriver
        event.set(type='discard', message_id=message_id)
        event_ctl.set()
        
    # Parameter settings

    ## Driver selection

    def set_driver(self, driver_id):
        """Set driver

        Arguments:
        driver_id -- id of the driver as returned by drivers()
        """
        assert isinstance(driver_id, str)
        raise ErrorNotSupportedByDriver

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


# ----------------------------------------------------------------

class Event(object):
    """Class for passing events between the Core and the Controller thread."""
    
    _attributes = {
        'type': ("Type of the event",
            ("say_text", "say_deferred", "say_key", "say_icon", "cancel", "defer", "discard")),
        'text': ("Text of message",  ("say_text",)),
        'format': ("Format of the message (event say_text)", ("say_text",)),
        'position': ("Position in text", ("say_text", "say_deferred")),
        'position_type': ("Type of position", ("say_text", "say_deferred")),
        'index_mark': ("Index mark position", ("say_text", "say_deferred")),
        'character': ("Character position", ("say_text", "say_deferred")),
        'key': ("Key to speak", ("say_key",)),
        'icon': ("Icon to speak", ("say_icon",)), 
        'message_id': ("ID of message to speak", ("say_deferred", "defer"))
    }
    
    def __init__(self):
        self.lock = threading.Lock()
        self.clear()
    
    def safe_read(self):
        """Get the current value of the event"""
        self.lock.acquire()
        ret = copy(self)
        self.lock.release()
        return ret
        
    def clear(self):
        for a in self._attributes:
            setattr(self, a[0], None)
    
    def set(self, **args):
        """Set a value of the event"""
        self.lock.acquire()
        self.clear()
        if not args.has_key('type'):
            raise UnknownError
        type_arg = args['type']
        for name, value in args.iteritems():
            if not self._attributes.has_key(name):
                raise "Invalid attribute"
            if type_arg not in self._attributes[name][1]:
                raise "This argument is not allowed for this message type or invalid message type"
            setattr(self, name, value)
        self.lock.release()

class Controller(threading.Thread):
    """Controlls the speech synthesis process in a separate thread"""

    def __init__(self):
        global event, event_ctl
        event = Event()
        event_ctl = threading.Event()
        event.clear() # Put in default None values
        threading.Thread.__init__(self, group=None, name="driver_thread")
        self.start()

    def wait_for_event(self):
        """Wait for a new event"""
        event_ctl.wait()
        event_ctl.clear()
        
    def last_event(self):
        """Return last event"""
        ret = event.safe_read()
        return ret
        
    def run(self):
        print "Thread running!"
        while True:
            self.wait_for_event()
            e = self.last_event()
            if e.type == 'say_text':
                self.say_text(e.text, e.format, e. position, e.position_type, e.index_mark, e.character)
            elif e.type == 'say_deferred':
                self.say_deferred(e.message_id, e. position, e.position_type, e.index_mark, e.character)
            elif e.type == 'say_key':
                self.say_key(e.key)
            elif e.type == 'say_icon':
                self.say_icon(e.icon)
            elif e.type == 'cancel':
                self.cancel()
            elif e.type == 'defer':
                self.defer()
            elif e.type == 'discard':
                self.discard(e.message_id)
            else:
                raise "Unknown event type"
    
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
    
def main_loop(Core, Controller):
    """Main function and core read-process-notify loop of a driver"""
    global log
    log = logging.Logger('tts-api-driver', level=logging.DEBUG)
    log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    log_handler = logging.StreamHandler(sys.stderr)
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)
    
    driver_core = Core()
    driver_core.set_controller(Controller())
    
    driver_comm = ttsapi.server.TCPConnection(provider=driver_core,
                                              logger=log, method='pipe')

    while True:
        driver_comm.process_input()
