#
# tts-api.py - Python implementation of TTS API
#   
# Copyright (C) 2006 Brailcom, o.p.s.
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
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# 
# $Id: ttsapi.py,v 1.3 2006-07-03 20:56:57 hanke Exp $
 
"""Python implementation of TTS API"""

import connection
import sys
from types import *;

# --------------- Exceptions --------------------------

class _CommunicationError(Exception):
    def __init__ (self, code, msg, data):
        Exception.__init__(self, "%s: %s" % (code, msg))
        self.code = code
        self.msg = msg
        self.data = data

    def code (self):
        """Return the server response error code as integer number."""
        return self.code
        
    def msg (self):
        """Return server response error message as string."""
        return self.msg

class TTSAPIError (_CommunicationError):
    """Error in TTS API request"""
    def __init__(self, error, code = None, msg = None, data = None):
        self.error_description = error
        self.code = code
        self.msg = msg
        self.data = data

# --------------- Data 'types' ----------------------

class DriverDescription(object):
    """Description of a driver"""

    driver_id = None
    synthesizer_name = None
    driver_version = None
    synthesizer_version = None

    def __init__(self, id, synth_name, driver_version, synth_version):
        """Initialize object with given values"""
        self.driver_id = id
        self.synthesizer_name = synth_name
        self.driver_version = driver_version
        self.synthesizer_version = synth_version

class DriverCapabilities(object):
    """Descriptions of features supported by a driver"""

    # Prosody parameters
    def __init__(self):
        self.can_list_voices = False
        self.can_set_voice_by_properties = False
        self.can_get_current_voice = False
    
        self.rate_settings = []
        """List of supported methods for setting rate.
        Recognized values: 'relative', 'absolute'"""
        self.can_get_default_rate = False
        
        self.pitch_settings = []
        """List of supported methods for setting pitch.
        Recognized values: 'relative', 'absolute'"""
        self.can_get_default_pitch = False

        self.pitch_range_settings = []
        """List of supported methods for setting pitch range.
        Recognized values: 'relative', 'absolute'"""
        self.can_get_default_pitch_range = False

        self.volume_settings = []
        """List of supported methods for setting volume.
        Recognized values: 'relative', 'absolute'"""
        self.can_get_default_volume = False

        # Style parameters
        self.punctuation_modes = []
        """List of supported punctuation modes.
        Recognized values: all, none, some"""

        self.can_set_punctuation_detail = False
        
        self.capital_letters_modes = []
        """List of supported modes for reading capital letters.
        Recognized values: 'spelling', 'icon', 'pitch'"""
        
        self.can_set_number_grouping = False

        # Say commands
        self.can_say_text_from_position = False
        self.can_say_char = False
        self.can_say_key = False
        self.can_say_icon = False

        # Dictionaries
        self.can_set_dictionary = False
        
        # Audio playback/retrieval
        self.audio_methods = []
        """List of supported audio output methods.
        Recognized values: 'retrieval', 'playback'"""
        
        # Events and index marking
        self.events = []
        """List of supported audio events.
        Recognized values are: 'by_sentences', 'by_words', 'index_marks'"""

        # Performance guidelines
        self.performance_level = None
        """Degree of compliance with performance guidelines.
        'none' means no compliance, 'good' means SHOULD HAVE compliance
        and 'excelent' means NICE TO HAVE compliance. """

        # Defering messages
        self.can_defer_message = False
        
        # SSML Support
        self.can_parse_ssml = False
        
        # Multilingual utterences
        self.supports_multilingual_utterances = False

class VoiceDescription(object):
    name = None
    """Name of the voice in unicode"""
    language = None
    """ISO language code"""
    dialect = None
    """Dialect of the voice"""
    gender = 'unknown'
    """Gender of the voice.
    Recognized values are 'male', 'female' and 'unknown'"""
    age = None
    """Age of the speaker in years"""

    def __init__(self, name, language, dialect, gender, age):
        self.name = name
        self.language = language
        self.dialect = dialect
        self.gender = gender
        self.age = age


# --------------- TTS API --------------------------

class Connection(object):
    """TTS API Python implementation class

    Bindings to the text protocol version of TTS API.
    For precise documentation of methods, method arguments
    and attributes please see the appropriate method,
    arguments and attributes in the TTS API specifications
    available from
    http://www.freebsoft.org/doc/tts-api/
    """

    def __init__ (self, method, host='127.0.0.1', port='6570',
                  pipe_in = sys.stdin, pipe_out = sys.stdout):
        """Initialize the instance and connect to the server

        Arguments:

        method -- either 'socket' or 'pipe'
        host -- server hostname or IP address as a string
        port -- server port as a number
          
        """
        assert method in ['socket', 'pipe']
        
        if method == 'socket':
            self._conn = connection.SocketConnection(host, port)
        elif method == 'pipe':
            self._conn = connection.PipeConnection(pipe_in, pipe_out)
            
    # Driver discovery

    def drivers (self):
        """Return a list of DriverDescription objects containing
        information about the available drivers
        """
        code, msg, data = self._conn.send_command("LIST DRIVERS")
        raw = self._conn.parse_list(data)
        driver_descr = []
        for driver in raw:
            driver_descr.append(
                DriverDescription(id = driver[0], synth_name = driver[1],
                                  driver_version = driver[2], synth_version = driver[3]))

        return driver_descr
        
    def driver_capabilities (self, driver_id):
        """Return a DriverCapabilities object for the
        given driver.

        Arguments:
        driver_id -- identification of the driver
        """

        def to_bool(arg):
            """Converts text protocol truth values into Python constants"""
            if arg == "true":
                return True
            elif arg == "false":
                return false
            else:
                TTSAPIError("Truth value expected"
                            "in driver capabilities response")

        code, msg, data = self._conn.send_command("DRIVER CAPABILITIES", driver_id)
        raw = self._conn.parse_list(data)

        result = DriverCapabilities()

        for capability in raw:
            if (len(capability) < 2):
                raise TTSAPIError("Malformed driver capability")
            if not result.__dict__.has_key(capability[0]):
                raise TTSAPIError("Unknown capability reported by driver")

            entry = capability[0]

            if isinstance(result.__dict__[entry], bool):
                result.__dict__[entry] = to_bool(capability[1])
            elif isinstance(result.__dict__[entry], str):
                result.__dict__[entry] = Str(capability[1])
            elif isinstance(result.__dict__[entry], list):
                # List is empty?
                if capability[1] == 'nil':
                    result.__dict__[entry] = []
                # if not, fill in the attribute with supplied values
                else:
                    result.__dict__[entry] = capability[1:]

        return result

    def voices (self, driver_id):
        """Return a list of voices available to the given
        driver as a list of VoiceDescription objects.

        Arguments:
        driver_id -- identification of the driver
        """
        code, msg, data = self._conn.send_command("LIST VOICES")
        raw = self._conn.parse_list(data)

        res = []
        for voice in raw:
            if len(voice) < 4:
                raise TTSAPIError("Malformed list of voices: too few parameters") 
            print voice            
            res.append(
                VoiceDescription(name=voice[0], language=voice[1],
                                 dialect=voice[2], gender=voice[3].lower(),
                                 age=int(voice[4])))
        return res

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

        if (position == None and index_mark == None
            and character == None):
            self._conn.send_command("SAY TEXT", format);
        elif position != None:
            assert position_type != None
            self._conn.send_command("SAY TEXT", format, "FROM POSITION",
                                    str(position), position_type);
        elif index_mark != None:
            self._conn.send_command("SAY TEXT", format, "FROM INDEX MARK",
                                    '"'+index_mark+'"')
        elif character != None:
            self._conn.send_command("SAY TEXT", format, "FROM CHARACTER",
                                    str(character))
            
        
        code, msg, data = self._conn.send_data(text);

        if len(data) < 1 or not data[0].isdigit():
            raise TTSAPIError("Incorrect reply on 'SAY TEXT' command, data section.")

        return int(data[0])
        
        
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

        if (position == None and index_mark == None
            and character == None):
            code, msg, data = self._conn.send_command("SAY DEFERRED");
        elif position != None:
            assert position_type != None
            code, msg, data \
                  = self._conn.send_command("SAY DEFERRED", str(message_id),
                                            "FROM POSITION", str(position),
                                            position_type);
        elif index_mark != None:
            code, msg, data \
                  = self._conn.send_command("SAY DEFERRED", str(message_id),
                                            "FROM INDEX MARK", '"'+index_mark+'"')
        elif character != None:
            code, msg, data \
                  = self._conn.send_command("SAY DEFERRED", str(message_id),
                                            "FROM CHARACTER", str(character))
    
        if len(data) < 1 or not data[0].isdigit():
            raise TTSAPIError("Incorrect reply on 'SAY TEXT' command, data section.")

        return int(data[0])

    def say_key (self, key):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        assert isinstance(key, str)
        self._conn.send_command("SAY KEY", key)
        
    def say_char (self, character):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        assert len(character) == 1
        self._conn.send_command("SAY CHAR", character)
        
    def say_icon (self, icon):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        self._conn.send_command("SAY ICON", icon)
        
    # Speech Controll commands

    def cancel (self):
        """Cancel current synthesis process and audio output."""
        self._conn.send_command("CANCEL")
        
    def defer (self):
        """Defer current message."""
        self._conn.send_command("DEFER")
        
    def discard (self, message_id):
        """Discard a previously deferred message.

        Arguments:
        message_id -- unique identification of the message to discard          
        """
        assert isinstance(message_id, int)
        self._conn.send_command("DISCARD", message_id)
        
    # Parameter settings

    ## Driver selection

    def set_driver(self, driver_id):
        """Set driver

        Arguments:
        driver_id -- id of the driver as returned by drivers()
        """
        assert isinstance(driver_id, str)
        self._conn.send_command("SET DRIVER", driver_id)

    ## Voice selection

    def set_voice_by_name(self, voice_name):
        """Set voice.

        Arguments:
        voice_name -- name of a voice as obtained by voices()          
        """
        assert isinstance(voice_name, str)
        self._conn.send_command("SET VOICE BY NAME", '"'+voice_name+'"')
        
    def set_voice_by_properties(self, voice_description, variant):
        """Choose and set a voice best matching the given description.

        Arguments:
        voice_description -- VoiceDescription object
        variant -- a positive number meaning variant
        of the voice from those matching voice_description          
        """
        assert isinstance(voice_description, VoiceDescription)
        assert isinstance(variant, int)

        self._conn.send_command("SET VOICE BY PROPERTIES",
                                voice_description.language,
                                '"'+voice_description.dialect+'"',
                                voice_description.gender,
                                voice_description.age,
                                variant)        
        
    def current_voice(self):
        """Return VoiceDescription of the current voice."""
        code, msg, data = self._conn.send_command("GET CURRENT VOICE")
        raw = self._conn.parse_list(data)
        v = raw[0]
        assert len(raw) > 0
        voice_descr = \
            VoiceDescription(name=v[0], language=v[1],
                             dialect=v[2], gender=v[3].lower(),
                             age=v[4])

        return driver_descr        
        

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
        self._conn.send_command("SET", method, "RATE", rate)
        
    def default_absolute_rate(self):
        """Returns default absolute rate for the given voice
        as a positive number in words per minute.
        """
        code, msg, data = self._conn.send_command("GET ABSOLUTE DEFAULT RATE")
        assert len(data) > 0
        return int(data[0])
        
    def set_pitch(self, pitch, method='relative'):
        """Set relative or absolute pitch.

        Arguments:
        pitch -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(pitch, int)
        self._conn.send_command("SET", method, "PITCH", pitch)
        
    def default_absolute_pitch(self):
        """Returns default absolute pitch for the given voice
        as a positive number in Hertzs.
        """
        code, msg, data = self._conn.send_command("GET ABSOLUTE DEFAULT PITCH")
        assert len(data) > 0
        return int(data[0])
        
    def set_pitch_range(self, range, method='relative'):
        """Set relative or absolute pitch range.

        Arguments:
        range -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(range, int)
        self._conn.send_command("SET", method,  "PITCH RANGE", range)
        
    def set_volume(self, volume, method='relative'):
        """Set relative or absolute volume.

        Arguments:
        volume -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        between 0 and 100 for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(volume, int)
        self._conn.send_command("SET", method, "VOLUME", volume)
        
    def default_absolute_volume(self):
        """Returns default absolute volume for the given voice
        as a positive number between 0 and 100.
        """
        code, msg, data = self._conn.send_command("GET ABSOLUTE DEFAULT VOLUME")
        assert len(data) > 0
        return int(data[0])

    ## Style parameters

    def set_punctuation_mode(self, mode):
        """Set punctuation reading mode.


        Arguments:
        mode -- one of 'none', 'all', 'some'          
        """
        assert mode in ('none', 'all', 'some')
        self._conn.send_command("SET PUNCTUATION MODE", mode)

    def set_punctuation_detail(self, detail):
        """Set punctuation detail.

        Arguments:
        detail -- a list of punctuation characters that
        should be explicitly indicated by the synthesizer          
        """
        assert isinstance(detail, str)
        self._conn.send_command("SET PUNCTUATION DETAIL", detail)

    def set_capital_letters_mode(self, mode):
        """Set mode for reading capital letters.

        Arguments:
        mode -- one of 'no', 'spelling', 'icon', 'pitch'          
        """
        assert mode in ('no', 'spelling', 'icon', 'pitch')
        self._conn.send_command("SET CAPITAL LETTERS MODE", mode)

    def set_number_grouping(self, grouping):
        """Set grouping of digits for reading numbers.

        Arguments:
        grouping -- 0 for default or a positive value
        specifying how many digits should be read together          
        """
        assert isinstance(grouping, int)
        self._conn.send_command("SET NUMBER GROUPING", grouping)

    # Dictionaries
    
    def set_dictionary(self):
        """Set user dictionary. Exact behavior yet undefined."""
        raise ErrorNotImplemented

    # Audio Output
    
    def set_audio_output(self, method='playback'):
        """Set audio output method as described in TTS API.

        Arguments:
        method -- one of 'playback', 'retrieval'          
        """
        assert method in ('playback', 'retrieval')
        self._conn.send_command("SET AUDIO OUTPUT", method)

    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """
        assert isinstance(host, str)
        assert isinstance(port, int) and port > 0
        self._conn.send_command("SET AUDIO RETRIEVAL DESTINATION", host, port)

    # Callbacks
    
    def register_callback(self, callback):
        """Register a function to be called whenever
        an event is received from server (message begin/end,
        word start/end etc). This function will be called asynchronously
        from a separate thread without any additional synchronization
        mechanisms.

        Arguments:
        callback -- a function to call when an event
        is received.

        The callback function must have this form
          
        callback(event_type, n, text_position, name)

        where meaning of the arguments is the following:
        event_type -- one of 'message_begin', 'message_end',
        'sentence_begin', 'sentence_end', 'word_begin', 'word_end',
        'index_mark'
        n -- a positive number specifying order of the event of the
        given type (1 for first event of this type in the message,
        2 for second etc)
        text_position -- a positive number representing the position
        in the original text where the event occured in number of
        characters (UTF-32) from the beginning of the message
        name -- for events of type 'index_mark' this variable contains
        the name of the index mark as a string otherwise it contains
        the value None          
        """
        # TODO: Implement asynchronicity and callbacks
        raise ErrorNotImplemented
