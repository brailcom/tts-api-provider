#
# ttsapi_types.py - Data classes for TTS API
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
# $Id: structures.py,v 1.3 2006-08-20 21:11:49 hanke Exp $


class Structure (object):
    """Simple data structures.
    Attribute names of the instance are listed in the sequence '_attributes'.
    Each element of '_attributes' is a tuple of the form
(attribute_name, documentation, default_value).  default_value may be
    omitted, in such a case the attribute value must be provided to the
    constructor call.
    """

    _attributes = ()
    
    def __init__ (self, **args):
        for a in self._attributes:
            name = a[0]
            if len (a) > 2:
                value = args.get
                if args.has_key (name):
                    value = args[name]
                else:
                    value = a[2]
            else:
                value = args[name]
            setattr (self, name, value)

    def attributes_dictionary(self):
        """Returns a dictionary of attribute names and their values"""
        dict = {}
        for a in self._attributes:
            dict[a[0]] = getattr(self, a[0])
        return dict

class DriverDescription(Structure):
    """Description of a driver"""

    _attributes = (
        ("driver_id", "ID string unique to the driver", None),
        ("synthesizer_name", "Name of the synthesizer", None),
        ("driver_version", "Version of the driver as a string", None),
        ("synthesizer_version", "Version of the synthesizer as a string", None)
        )


class DriverCapabilities(Structure):
    """Descriptions of features supported by a driver"""    

    _attributes = (
        ('can_list_voices', "", False),
        ('can_set_voice_by_properties', "", False),
        ('can_get_current_voice', "", False),
        ('rate_settings', "Rate settings: 'relative' and/or 'absolute'", []),
        ('can_get_default_rate', "", False),
        ('pitch_settings', "Pitch settings: 'relative' and/or 'absolute'", []),
        ('can_get_default_pitch', "", False),
        ('pitch_range_settings', "Pitch range settings: 'relative' and/or 'absolute'", []),
        ('can_get_default_pitch_range', "", False),
        ('volume_settings', "Volume settings: 'relative' and/or 'absolute'", []),
        ('can_get_default_volume', "", False),
        # Style parameters
        ('punctuation_modes',
         """List of supported punctuation modes.
         Recognized values: all, none, some""",
         []),
        ('can_set_punctuation_detail', "", False),
        ('capital_letters_modes',         
         """List of supported modes for reading capital letters.
         Recognized values: 'spelling', 'icon', 'pitch'""",
         []
        ),
        ('can_set_number_grouping', "", False),        
        # Say commands
        ('can_say_text_from_position', "", False),
        ('can_say_char', "", False),
        ('can_say_key', "", False),
        ('can_say_icon', "", False),
        # Dictionaries
        ('can_set_dictionary', "", False),        
        # Audio playback/retrieval
        ('audio_methods',
        """List of supported audio output methods.
        Recognized values: 'retrieval', 'playback'""",
        []),        
        # Events and index marking
        ('events',
        """List of supported audio events.
        Recognized values are: 'by_sentences', 'by_words', 'index_marks'""",
         []),
        # Performance guidelines
        ('performance_level',         
        """Degree of compliance with performance guidelines.
        'none' means no compliance, 'good' means SHOULD HAVE compliance
        and 'excelent' means NICE TO HAVE compliance. """,
         None),        
        # Defering messages
        ('can_defer_message', "", False),
        # SSML Support
        ('can_parse_ssml', "", False),        
        # Multilingual utterences
        ('supports_multilingual_utterances', "", False)
    )

class VoiceDescription(Structure):

    _attributes = (        
        ('name', "Name of the voice", None),
        ('language', "ISO language code", None),
        ('dialect', "Dialect of the voice", None),
        ('gender',
         """Gender of the voice.
         Recognized values are 'male', 'female' and 'unknown'""",
         'unknown', None),
        ('age', "Age of the speaker in years or None", None)
    )
