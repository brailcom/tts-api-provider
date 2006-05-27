#
# tts-api.py - Python implementation of TTS API
#   
# Copyright (C) 2001, 2002, 2003 Brailcom, o.p.s.
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
# $Id: ttsapi.py,v 1.1 2006-05-27 21:14:51 hanke Exp $
 
"""Python implementation of TTS API"""

# --------------- Exceptions --------------------------

class _CommunicationError(Exception):
    def __init__ (self, code, msg, data):
        Exception.__init__(self, "%s: %s" % (code, msg))
        self._code = code
        self._msg = msg
        self._data = data

    def code (self):
        """Return the server response error code as integer number."""
        return self._code
        
    def msg (self):
        """Return server response error message as string."""
        return self._msg

class TTSAPIError (_CommunicationError):
    """Error in TTS API request"""


# --------------- Data types ----------------------

class DriverDescription:
    """Description of a driver"""

    driver_id = None
    driver_version = None
    synthesizer_name = None
    synthesizer_version = None

class DriverCapabilities:
    """Descriptions of features supported by a driver"""

    # Prosody parameters
    can_list_voices = False
    can_set_voice_by_properties = False
    can_get_current_voice = False

    rate_settings = list()
    """List of supported methods for setting rate.
    Recognized values: 'relative', 'absolute'"""
    can_get_rate_default = False

    pitch_settings = list()
    """List of supported methods for setting pitch.
    Recognized values: 'relative', 'absolute'"""
    can_get_pitch_default = False

    pitch_range_settings = list()
    """List of supported methods for setting pitch range.
    Recognized values: 'relative', 'absolute'"""
    can_get_pitch_range_default = False

    volume_settings = list()
    """List of supported methods for setting volume.
    Recognized values: 'relative', 'absolute'"""
    can_get_volume_default = False

    # Style parameters
    supported_punctuation_modes = list()
    """List of supported punctuation modes.
    Recognized values: all, none, some"""

    can_set_punctuation_detail = False

    capital_letters_modes = list([])
    """List of supported modes for reading capital letters.
    Recognized values: 'spelling', 'icon', 'pitch'"""

    can_set_number_grouping = False

    # Say commands
    can_say_text_from_position = False
    can_say_char = False
    can_say_key = False
    can_say_icon = False

    # Dictionaries
    can_set_dictionary = False

    # Audio playback/retrieval
    audio_methods = list()
    """List of supported audio output methods.
    Recognized values: 'retrieval', 'playback'"""
    
    # Events and index marking
    events = list()
    """List of supported audio events.
    Recognized values are: 'by_sentences', 'by_words', 'index_marks'"""

    # Performance guidelines
    honors_performance_guidelines = 0
    """Degree of compliance with performance guidelines.
    0 means no compliance, 1 means SHOULD HAVE compliance
    and 2 means NICE TO HAVE compliance. """

    # Defering messages
    can_defer_message = False

    # SSML Support
    can_parse_ssml = False

    # Multilingual utterences
    supports_multilingual_utterances = False

class VoiceDescription:
    name = None
    """Name of the voice as UTF-32 string"""
    language = None
    """ISO language code"""
    dialect = None
    """Dialect of the voice"""
    gender = 'unknown'
    """Gender of the voice.
    Recognized values are 'male', 'female' and 'unknown'"""
    age = 0
    """Age of the speaker in years"""


# --------------- TTS API --------------------------

class ttsapi:
    """TTS API Python implementation class

    Bindings to the text protocol version of TTS API.
    For precise documentation of methods, method arguments
    and attributes please see the appropriate method,
    arguments and attributes in the TTS API specifications
    available from
    http://www.freebsoft.org/doc/tts-api/
    """

    def __init__ (self, host='127.0.0.1', port='6570'):
        """Initialize the instance and connect to the server

        Arguments:

        host -- server hostname or IP address as a string
        port -- server port as a number
          
        """
        self._conn = _TCP_TTSAPI_Connection(host, port)

    # Driver discovery

    def list_drivers (self):
        """Return a list of DriverDescription objects containing
        information about the available drivers
        """
        
    def driver_capabilities (self, driver_id):
        """Return a DriverCapabilities object for the
        given driver.

        Arguments:
        driver_id -- identification of the driver
        """
        
    # Voice discovery
    
    def list_voices (self, driver_id):
        """Return a list of voices available to the given
        driver as a list of VoiceDescription objects.

        Arguments:
        driver_id -- identification of the driver
        """

    # Speech Synthesis commands

    def say_text (self, text, format='plain'):
        """Synthesize the whole message of given format.

        Arguments:
        format -- either 'plain' or 'ssml'
        text -- text of the message encoded in UTF-32          
        """
        
    def say_text_from_event (self, text, position, format='plain'):
        """Synthesise the whole message starting at the given
        position.

        Arguments:
        format -- either 'plain' or 'ssml'
        text -- text of the message encoded in UTF-32
        position -- a positive number indicating the position
        position_type -- one of: 'message_begin', 'sentence_start',
        'sentence_end', 'word_start', 'word_end'          
        """
        
    def say_text_from_index_mark (self, index_mark, format='plain'):
        """Synthesise the whole message starting at the given
        index mark.

        Arguments:
        format -- either 'plain' or 'ssml'
        text -- text of the message encoded in UTF-32
        index_mark -- name of the index mark where synthesis
        should start          
        """
        
    def say_text_from_character (self, text, position,
                                format='plain'):               
        """Synthesise the whole message starting at the given
        position.

        Arguments:
        format -- either 'plain' or 'ssml'
        text -- text of the message encoded in UTF-32
        position -- a positive value indicating the position
        of character where synthesis should start          
        """
        
    def say_deferred (self, message_id):        
        """Synthesize the whole message deffered message.

        Arguments:
        message_id -- unique identification number of the message        
        """

    def say_deferred_from_event(self, message_id, position):
        """Synthesise the deferred message starting at the given
        position.

        Arguments:
        message_id -- unique identification number of the message
        position -- a positive number indicating the position
        position_type -- one of: 'message_begin', 'sentence_start',
        'sentence_end', 'word_start', 'word_end'          
        """
        
    def say_deferred_from_index_mark (self, message_id, index_mark):
        """Synthesise the deferred message starting at the given
        index mark.

        Arguments:
        message_id -- unique identification number of the message
        index_mark -- name of the index mark where synthesis
        should start          
        """
           
    def say_deferred_from_character (self, mesage_id, position):
        """Synthesise the deferred message starting at the given
        character position.

        Arguments:
        message_id -- unique identification number of the message
        position -- a positive value indicating the position
        of character where synthesis should start          
        """
        
    def say_key (self, key):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        
    def say_char (self, character):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        
    def say_icon (self, icon):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        
    # Speech Controll commands

    def cancel (self):
        """Cancel current synthesis process and audio output."""
        
    def defer (self):
        """Defer current message."""
        
    def discard (self, message_id):
        """Discard a previously deferred message.

        Arguments:
        message_id -- unique identification of the message to discard          
        """
        
    # Parameter settings

    ## Voice selection

    def set_voice_by_name(self, voice_name):
        """Set voice.

        Arguments:
        voice_name -- name of a voice as obtained by list_voices()          
        """
        
    def set_voice_by_properties(self, voice_description, variant):
        """Choose and set a voice best matching the given description.

        Arguments:
        voice_description -- VoiceDescription object
        variant -- a positive number meaning variant
        of the voice from those matching voice_description          
        """
        
    def get_current_voice(self):
        """Return VoiceDescription of the current voice."""
        

    ## Prosody parameters
        
    def set_rate(self, rate, method='relative'):
        """Set relative or absolute rate.

        Arguments:
        rate -- desired rate change with respect to default represented
        as a number in percents for relative change or as a positive number
        in words per minute for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        
    def get_rate_absolute_default(self):
        """Returns default absolute rate for the given voice
        as a positive number in words per minute.
        """
        
    def set_pitch(self, pitch, method='relative'):
        """Set relative or absolute pitch.

        Arguments:
        pitch -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        
    def get_pitch_absolute_default(self):
        """Returns default absolute pitch for the given voice
        as a positive number in Hertzs.
        """
        
    def set_pitch_range(self, range, method='relative'):
        """Set relative or absolute pitch range.

        Arguments:
        range -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        
    def set_volume(self, volume, method='relative'):
        """Set relative or absolute volume.

        Arguments:
        volume -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        between 0 and 100 for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        
    def get_volume_absolute_default(self):
        """Returns default absolute volume for the given voice
        as a positive number between 0 and 100.
        """        

    ## Style parameters

    def set_punctuation_mode(self, mode):
        """Set punctuation reading mode.

        Arguments:
        punctuation -- one of 'none', 'all', 'some'          
        """

    def set_punctuation_detail(self, detail):
        """Set punctuation detail.

        Arguments:
        detail -- a list of punctuation characters that
        should be explicitly indicated by the synthesizer          
        """

    def set_capital_letters_mode(self, mode):
        """Set mode for reading capital letters.

        Arguments:
        mode -- one of 'no', 'spelling', 'icon', 'pitch'          
        """

    def set_number_grouping(self, grouping):
        """Set grouping of digits for reading numbers.

        Arguments:
        grouping -- 0 for default or a positive value
        specifying how many digits should be read together          
        """

    # Dictionaries
    
    def set_dictionary(self):
        """Set user dictionary. Exact behavior yet undefined."""
        pass

    # Audio Output
    
    def set_audio_output(self, method='playback'):
        """Set audio output method as described in TTS API.

        Arguments:
        method -- one of 'playback', 'retrieval'          
        """

    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """

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
        
