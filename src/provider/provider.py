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
# $Id: provider.py,v 1.2 2006-08-09 12:06:12 hanke Exp $
 
"""TTS API Provider core logic"""

import sys
from ttsapi.structures import *
from ttsapi.errors import *
#from logs import log

class Provider(object):
    """TTS API implementation class (main process)
    """

    def __init__ (self):
        """Initialize the instance and connect to the server"""
        pass
            
    # Driver discovery

    def drivers (self):
        """Return a list of DriverDescription objects containing
        information about the available drivers
        """
        raise ErrorNotSupportedByServer
        
    def driver_capabilities (self, driver_id):
        """Return a DriverCapabilities object for the
        given driver.

        Arguments:
        driver_id -- identification of the driver
        """
        pass

    def voices (self, driver_id):
        """Return a list of voices available to the given
        driver as a list of VoiceDescription objects.

        Arguments:
        driver_id -- identification of the driver
        """
        return [["kal", 'en', 'nil', 'MALE', 30],
                ["ked", 'en', 'nil', 'MALE', 30],
                ["czech_ph", 'cs', 'nil', 'MALE', 30],
                ["el_diphone", 'es', 'nil', 'MALE', 48],
                ["lp_diphone", 'it', None, 'MALE', 30],
                ["pc_diphone", 'it', None, 'FEMALE', 30]
                ]

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

        pass
        
        
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

        print "say_deferred called with message_id " + str(message_id) \
              + " position " + str(position) + " pos_type " \
              + str(position_type) + " index mark " + str(index_mark) + " character "  \
              + str(character)
        

        pass

    def say_key (self, key):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        assert isinstance(key, str)
        pass
        
    def say_char (self, character):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        assert len(character) == 1
        pass
        
    def say_icon (self, icon):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)
        pass
        
    # Speech Controll commands

    def cancel (self):
        """Cancel current synthesis process and audio output."""
        pass
        
    def defer (self):
        """Defer current message."""
        pass
        
    def discard (self, message_id):
        """Discard a previously deferred message.

        Arguments:
        message_id -- unique identification of the message to discard          
        """
        assert isinstance(message_id, int)
        pass
        
    # Parameter settings

    ## Driver selection

    def set_driver(self, driver_id):
        """Set driver

        Arguments:
        driver_id -- id of the driver as returned by drivers()
        """
        assert isinstance(driver_id, str)
        pass

    ## Voice selection

    def set_voice_by_name(self, voice_name):
        """Set voice.

        Arguments:
        voice_name -- name of a voice as obtained by voices()          
        """
        assert isinstance(voice_name, str)
        pass
        
    def set_voice_by_properties(self, voice_description, variant):
        """Choose and set a voice best matching the given description.

        Arguments:
        voice_description -- VoiceDescription object
        variant -- a positive number meaning variant
        of the voice from those matching voice_description          
        """
        assert isinstance(voice_description, VoiceDescription)
        assert isinstance(variant, int)

        pass
        
    def current_voice(self):
        """Return VoiceDescription of the current voice."""
        pass
        

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
        pass
        
    def default_absolute_rate(self):
        """Returns default absolute rate for the given voice
        as a positive number in words per minute.
        """
        pass
        
    def set_pitch(self, pitch, method='relative'):
        """Set relative or absolute pitch.

        Arguments:
        pitch -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(pitch, int)
        pass
        
    def default_absolute_pitch(self):
        """Returns default absolute pitch for the given voice
        as a positive number in Hertzs.
        """
        pass
        
    def set_pitch_range(self, range, method='relative'):
        """Set relative or absolute pitch range.

        Arguments:
        range -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(range, int)
        pass
        
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
        pass

    ## Style parameters

    def set_punctuation_mode(self, mode):
        """Set punctuation reading mode.


        Arguments:
        mode -- one of 'none', 'all', 'some'          
        """
        assert mode in ('none', 'all', 'some')
        pass

    def set_punctuation_detail(self, detail):
        """Set punctuation detail.

        Arguments:
        detail -- a list of punctuation characters that
        should be explicitly indicated by the synthesizer          
        """
        assert isinstance(detail, str)
        pass

    def set_capital_letters_mode(self, mode):
        """Set mode for reading capital letters.

        Arguments:
        mode -- one of 'no', 'spelling', 'icon', 'pitch'          
        """
        assert mode in ('no', 'spelling', 'icon', 'pitch')
        pass

    def set_number_grouping(self, grouping):
        """Set grouping of digits for reading numbers.

        Arguments:
        grouping -- 0 for default or a positive value
        specifying how many digits should be read together          
        """
        assert isinstance(grouping, int)
        pass

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
        pass

    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """
        assert isinstance(host, str)
        assert isinstance(port, int) and port > 0
        pass

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
