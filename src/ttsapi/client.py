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
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301, USA.
# 
# $Id: client.py,v 1.7 2007-09-19 12:57:05 hanke Exp $
 
"""Python implementation of TTS API over text protocol"""

import sys

import connection
from structures import *
from errors import TTSAPIError

# --------------- TTS API --------------------------

class TCPConnection(object):
    """TTS API Python implementation class

    Bindings to the text protocol version of TTS API.
    For precise documentation of methods, method arguments
    and attributes please see the appropriate method,
    arguments and attributes in the TTS API specifications
d    available from
    http://www.freebsoft.org/doc/tts-api/
    """

    _callbacks = {
        'message_start' : [],
        'message_end' : [],
        'sentence_start' : [],
        'sentence_end' : [],
        'word_start' : [],
        'word_end' : [],
        'index_mark' : []
        }

    def __init__ (self, method='socket', host='127.0.0.1', port=6567,
                  pipe_in = sys.stdin, pipe_out = sys.stdout, logger=None):
        """Initialize the instance and connect to the server

        Arguments:

        method -- either 'socket' or 'pipe'
        host -- server hostname or IP address as a string
        port -- server port as a number
          
        """
        assert method in ['socket', 'pipe']
        self.logger = logger
        if method == 'socket':
            self._conn = connection.SocketConnection(host, port, logger=logger, provider=self)
        elif method == 'pipe':
            self._conn = connection.PipeConnection(pipe_in, pipe_out, logger=logger, provider=self)
            
    # Driver discovery

    def init(self):
        """Initialize"""
        self._conn.send_command("INIT")

    def quit(self):
        """Quit"""
        self._conn.send_command_without_reply("QUIT")
    
    def drivers (self):
        """Return a list of DriverDescription objects containing
        information about the available drivers
        """
        code, msg, raw = self._conn.send_command("LIST DRIVERS")
        driver_descr = []
        
        for driver in raw:
            driver_descr.append(
                DriverDescription(driver_id = driver[0], synthesizer_name = driver[1],
                                  driver_version = driver[2],
                                  synthesizer_version = driver[3]))

        return driver_descr
        
    def driver_capabilities (self):
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
                return False
            else:
                TTSAPIError("Truth value expected"
                            "in driver capabilities response")

        code, msg, raw = self._conn.send_command("DRIVER CAPABILITIES")

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

    def voices (self):
        """Return a list of voices available to the currently set
        driver as a list of VoiceDescription objects.

        Arguments:
        driver_id -- identification of the driver
        """
        code, msg, raw = self._conn.send_command("LIST VOICES")

        res = []
        for voice in raw:
            if len(voice) < 4:
                raise TTSAPIError("Malformed list of voices: too few parameters") 
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
            raise TTSAPIError("Incorrect reply on 'SAY TEXT' command, message id missing.")

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

    def set_message_id(self, message_id):
        """Set message identification number"""
        assert isinstance(message_id, int)
        self._conn.send_command("SET MESSAGE ID", message_id)
        
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
        code, msg, raw = self._conn.send_command("GET CURRENT VOICE")
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
        raise NotImplementedError

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
        self._conn.send_command("SET AUDIO RETRIEVAL", host, port)

    # Callbacks
    
    def register_callback(self, event_type, callback):
        """Register a function to be called whenever
        an event is received from server (message begin/end,
        word start/end etc). This function will be called asynchronously
        from a separate thread without any additional synchronization
        mechanisms. If more functions are specified for a given
        callback type, they will be called one by one, but the execution
        order is not specified.

        Arguments:
        event_type -- one of 
           'all' : apply for all events
           event : where event is an event identifier defined by TTS API
                   (e.g. 'message_start')
           [event1, event2,...] : list of events
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


        if event_type == 'all':
            types = self._callbacks.keys()
        if isinstance(event_type, str):
            types = [event_type, ]
        elif isinstance(event_type, list) or isinstance(event_type, tuple):
            types = event_type
        else:
            assert 0, "Unknown callback type"

        for type in types:
                self._callbacks[type].append(callback)


    def raise_event(self, code, msg, data):
        """Call the appropriate provider function for the given event"""

        event = AudioEvent()

        line = data[0].split()

        event.type = line[0]
        event.message_id = line[1]
        if event.type in ['message_start', 'message_end']:
            event.pos_text, event.pos_audio = map(float, line[2:])
        elif event.type in ['sentence_start', 'sentence_end', 'word_start', 'word_end']:
            event.n, event.pos_text, event.pos_audio = map(float, line[1:])
        elif type == 'index_mark':
            name = line[1].strip('"')
            event.pos_text, event.pos_audio = map(fload, line[2:])
        else:
            raise "Unknown index mark"

        # Call all registered callbacks in random order
        if event.type in self._callbacks:
            for callback in self._callbacks[event.type]:
                callback(event)

    def close(self):
        """Close this connection"""
        self._conn.close()
        
