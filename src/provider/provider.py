#
# tts-api.py - Python implementation of TTS API
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
# $Id: provider.py,v 1.12 2007-11-21 12:42:07 hanke Exp $
 
"""TTS API Provider core logic"""

import sys
import subprocess
from copy import copy
import random

from ttsapi.structures import *
from ttsapi.errors import *
import ttsapi.client

current_message_id = None

class Driver(object):
    """TTS API driver"""
    "Name (id) of the driver"
    name = None,
    "Process object for the driver"
    process = None,
    "Communication object for the driver (ttsapi.Client object)"
    com = None,
    "Audio output. One of 'playback', 'retrieval', 'emulated_playback'"
    audio_output = None,
    "Real (without any emulateion) capabilities as reported by the driver"
    real_capabilities = None
    
    def __init__(self, name, process, com):
        """Init the main attributes"""
        self.name = name
        self.process = process
        self.com = com

class Provider(object):
    """TTS API implementation class (main process)
    """

    _connection = None
    _registered_callbacks = {}
    _audio_volume = 1.0

    def __init__ (self, logger, configuration, audio,
                  global_state):
        """Initialize the instance, load all output modules"""
        global log, conf
        log = logger
        conf = configuration
        # Load all available drivers, fill in the self.drivers and
        # self.current_driver attributes
        self.audio = audio
        self.global_state = global_state
        self.loaded_drivers = {}
        for entry in conf.available_drivers:
            if len(entry) == 2:
                name, executable = entry
                args = ["",]
            elif len(entry) == 3:
                name, executable, args = entry
            else:
                raise "Invalid number of output module parameters"

            id = random.randrange(1,10000,1)
            logfile = open(conf.log_dir+name+"-"+str(id)+".log", "w")
            process = subprocess.Popen(args=[executable]+args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=logfile)
                # bufsize = 1 means line buffered
            log.debug("Subprocess for driver" + name + "initalized")
            self.loaded_drivers[name] = Driver(process=process, name=name,
                com = ttsapi.client.TCPConnection(method = 'pipe',
                                                  pipe_in = process.stdout,
                                                  pipe_out = process.stdin,
                                                  logger=log))
            log.debug("Driver instance for driver" + name + "created")
            try:
                self.loaded_drivers[name].com.init()
            except TTSAPIError, error:
                log.debug("Can't initialize driver " + name)
                # Cleanup
                logfile.close()
                del self.loaded_drivers[name]
                #TODO: Join process
                continue
            log.debug("Driver instance for driver" + name + "initalized")
            self.loaded_drivers[name].real_capabilities \
               = self.loaded_drivers[name].com.driver_capabilities()
            log.debug("Real capabilities for driver" + name + "filled in")
            # Now comes the playback/retrieval question
            if self.loaded_drivers[name].real_capabilities.audio_methods == 'retrieval':
                # Audio output is retrieval
                self.loaded_drivers[name].audio_output = 'emulated_playback'
            else:
                # Audio output is playback
                self.loaded_drivers[name].audio_output = 'playback'
                # Dispatch incomming events
                log.debug("Registering callbacks for driver " + name)
                self.loaded_drivers[name].com.register_callback(
                    'all', self.dispatch_audio_event)

        if self.loaded_drivers.has_key(conf.default_driver):
            self.current_driver = self.loaded_drivers[conf.default_driver]
        else:
            log.error("Can't load default driver, not available")
            # TODO: Fallback on some other module
            driver_list = self.loaded_drivers.items()
            if len(driver_list) > 0:
                # Select the first driver in the list of
                # available drivers
                driver_name, driver_value = driver_list[0]
                self.current_driver = driver_value
                log.info("Loaded fallback driver " + str(driver_name))
            else:
                self.current_driver = None
                log.info("No driver available")

    def init(self):
        """Called on the INIT TTS API command."""
        raise ErrorInvalidCommand

    def quit(self):
        """Terminate all child threads and processes and exit"""

        log.info("Terminaning all loaded drivers")
    
        for name, driver in self.loaded_drivers.iteritems():
            log.debug("Terminating " + name + " driver")
            driver.com.quit()
            log.debug("Waiting for driver process to terminate (" + name + ")")
            driver.process.wait()
            log.debug("Driver process terminated (" + name + ")")

    def set_connection(self, connection):
        """Set the associated connection. Necessary for
        dispatching audio events"""
        self._connection=connection
    
    # Driver discovery

    def drivers (self):
        """Return a list of DriverDescription objects containing
        information about the available drivers
        """
        res = []
        for name, driver in self.loaded_drivers.iteritems():
            dscr = driver.com.drivers()
            dscr[0].driver_id = name
            res += dscr
        return res

    def driver_capabilities (self):
        """Return a DriverCapabilities object for the
        given driver.

        Arguments:
        """
        if not self.current_driver:
            raise ErrorDriverNotAvailable
        capabilities = copy(self.current_driver.real_capabilities)
        
        # If retrieval is available, then by emulation also playback
        # is available
        if 'retrieval' in capabilities.audio_methods:
            capabilities.audio_methods.append('playback')
            
        return capabilities

    def voices (self):
        """Return a list of voices available to the given
        driver as a list of VoiceDescription objects.

        Arguments:
        """
        if not self.current_driver:
            raise ErrorDriverNotAvailable
        return self.current_driver.com.voices()
        
    # Speech Synthesis commands

    def _prepare_for_message(self, message_id):
        """Prepare the driver and possibly audio output for synthesis
        of a new message in the driver."""

        # Put the message_id into our list of processed messages.
        # (In the head of the list for performance reasons.)
        
        # If we are emulating playback, let the audio server
        # know there will be an incomming message and set the
        # proper destination on the driver.
        log.debug("Audio output method: " + str (self.current_driver.audio_output))
        
        # Decide what kind of audio output to use
        self.set_audio_output()
        # Make preparations for this kind of audio output
        if self.current_driver.audio_output == 'emulated_playback':
            self.audio.post_event('accept', message_id, blocking=True)
            try:
                log.debug("Setting audio retrieval destination")
                self.current_driver.com.set_audio_retrieval_destination(host=self.audio.host,
                    port=self.audio.port)
            except TTSAPIError, error:
                log.error("Error in output module: " + str(error))
                raise DriverError

            self.audio.audio.set_volume(message_id, self._audio_volume)

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
        assert isinstance(text, str) or isinstance(text, unicode)
        assert format in ('plain', 'ssml')
        assert position == None or isinstance(position, int)
        assert position_type in (None, 'message_begin', 'sentence_start',
                                 'sentence_end', 'word_start', 'word_end')
        assert index_mark == None or isinstance(index_mark, str) \
            or isinstance(text, unicode)
        assert character == None or isinstance(character, int)
        global current_message_id

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        message_id = self.global_state.new_message_id(self)
        current_message_id = message_id
        self.current_driver.com.set_message_id(message_id)
        self._prepare_for_message(message_id)

        # TODO: Escape '<' and '>'
        # Plain text emulation
        cap_message_format = self.current_driver.real_capabilities.message_format
        if format not in cap_message_format:
            if (format == 'plain') and ('ssml' in cap_message_format):
                log.debug("Converting from PLAIN to SSML")                
                text = "<speak>" + text + "</speak>"
                format = 'ssml'
            elif (format == 'ssml') and ('plain' in cap_message_format):
                log.debug("Converting from SSML to PLAIN")                
                # TODO: text = strip_ssml(text)
                format = 'plain'
            else:
                raise "Format not supported in driver or invalid format. Requested: " + str(format) + \
                    " Offered: " + str(cap_message_format)

        self.current_driver.com.say_text(text, format, position, position_type,
                                         index_mark, character)
        
        return message_id
        
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
        assert index_mark == None or isinstance(index_mark, str) \
            or isinstance(index_mark, unicode)
        assert character == None or isinstance(character, int)

        raise ErrorNotSupportedByServer

    def say_key (self, key):
        """Synthesize a key event.

        Arguments:
        key -- a string containing a key identification as defined
        in TTS API          
        """
        global current_message_id
        assert isinstance(key, str) or isinstance(key, unicode)

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        message_id = self.global_state.new_message_id(self)
        current_message_id = message_id
        self.current_driver.com.set_message_id(message_id)
        self._prepare_for_message(message_id)
                
        self.current_driver.com.say_key(key)
        
        return message_id
        
        
    def say_char (self, character):
        """Synthesize a character event.

        Arguments:
        character -- a single UTF-32 character.          
        """
        assert isinstance(character, str) or isinstance(character, unicode)
        assert len(character) == 1
        global current_message_id

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        message_id = self.global_state.new_message_id(self)
        current_message_id = message_id
        self.current_driver.com.set_message_id(message_id)
        self._prepare_for_message(message_id)
                
        self.current_driver.com.say_char(character)
        
        return message_id
        
    def say_icon (self, icon):
        """Synthesize a sound icon.

        Arguments:
        icon -- name of the icon as defined in TTS API.          
        """
        assert isinstance(icon, str)
        global current_message_id

        if not self.current_driver:
            raise ErrorDriverNotAvailable
        
        message_id = self.global_state.new_message_id(self)
        current_message_id = message_id
        self.current_driver.com.set_message_id(message_id)
        self._prepare_for_message(message_id)
        
        self.current_driver.com.say_icon(icon)
        
        return message_id
        
    # Speech Controll commands

    def cancel (self):
        """Cancel current synthesis process and audio output."""

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        log.debug("Cancelling current message (id == "+str(current_message_id)+")")
        # Cancel playback in audio
        # Strictly speaking, we should only do this if 'emulated_playback' is used
        if current_message_id != None:
            self.audio.post_event('discard', current_message_id)
            
        # NOTE: We are not waiting until the cancel is completed in the driver
        return self.current_driver.com.cancel()
        
    def defer (self):
        """Defer current message."""

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        return self.current_driver.com.defer()
        
    def discard (self, message_id):
        """Discard a previously deferred message.

        Arguments:
        message_id -- unique identification of the message to discard          
        """
        assert isinstance(message_id, int)

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        return self.current_driver.com.discard(message_id)
        
    # Parameter settings

    ## Driver selection

    def set_driver(self, driver_id):
        """Set driver

        Arguments:
        driver_id -- id of the driver as returned by drivers()
        """
        assert isinstance(driver_id, str)
        if self.loaded_drivers.has_key(driver_id):
            self.current_driver = self.loaded_drivers[driver_id]
            log.info("Driver switched to " + driver_id)
        else:
            raise ErrorDriverNotLoaded
    
    def set_message_id(self, message_id):
        """Set an identification number for the next message. Invalid in server,
        only used for communication with output modules."""
        raise ErrorInvalidCommand
    
    ## Voice selection

    def set_voice_by_name(self, voice_name):
        """Set voice.

        Arguments:
        voice_name -- name of a voice as obtained by voices()          
        """
        assert isinstance(voice_name, str)

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_voice_by_name(voice_name)
        
    def set_voice_by_properties(self, voice_description, variant):
        """Choose and set a voice best matching the given description.

        Arguments:
        voice_description -- VoiceDescription object
        variant -- a positive number meaning variant
        of the voice from those matching voice_description          
        """
        assert isinstance(voice_description, VoiceDescription)
        assert isinstance(variant, int)

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_voice_by_name(voice_description)
        
    def current_voice(self):
        """Return VoiceDescription of the current voice."""

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        return self.current_driver.com.current_voice()
        
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

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_rate(rate, method)
        
    def default_absolute_rate(self):
        """Returns default absolute rate for the given voice
        as a positive number in words per minute.
        """

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        return self.current_driver.com.default_absolute_rate()
        
    def set_pitch(self, pitch, method='relative'):
        """Set relative or absolute pitch.

        Arguments:
        pitch -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(pitch, int)

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        return self.current_driver.com.set_pitch(pitch, method)
        
    def default_absolute_pitch(self):
        """Returns default absolute pitch for the given voice
        as a positive number in Hertzs.
        """

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        return self.current_driver.com.default_absolute_pitch()
        
    def set_pitch_range(self, range, method='relative'):
        """Set relative or absolute pitch range.

        Arguments:
        range -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        in Hertzs for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(range, int)
        
        
    def set_volume(self, volume, method='relative'):
        """Set relative or absolute volume. This setting only
        affects the following messages, not the message currently
        in playback.

        Arguments:
        volume -- desired pitch change with respect to default represented
        as a number in percents for relative change or as a positive number
        between 0 and 100 for absolute change.
        method -- either 'relative' or 'absolute'          
        """
        assert isinstance(volume, int)
        global current_message_id

        if method == 'relative':
            self._audio_volume = volume / 100.0
        elif method == 'absolute':
            self._audio_volume = 2 * volume / 100.0
        else:
            raise "Unknown method"

    def default_absolute_volume(self):
        """Returns default absolute volume for the given voice
        as a positive number between 0 and 100.
        """
        assert len(data) > 0
        raise ErrorNotSupportedByServer

    ## Style parameters

    def set_punctuation_mode(self, mode):
        """Set punctuation reading mode.
        Arguments:
        mode -- one of 'none', 'all', 'some'
        """
        assert mode in ('none', 'all', 'some')

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_punctuation_mode(mode)

    def set_punctuation_detail(self, detail):
        """Set punctuation detail.

        Arguments:
        detail -- a list of punctuation characters that
        should be explicitly indicated by the synthesizer          
        """
        assert isinstance(detail, str) or isinstance(detail, unicode)

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_punctuation_detail(detail)

    def set_capital_letters_mode(self, mode):
        """Set mode for reading capital letters.

        Arguments:
        mode -- one of 'no', 'spelling', 'icon', 'pitch'          
        """
        assert mode in ('no', 'spelling', 'icon', 'pitch')

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_capital_letters_mode(mode)

    def set_number_grouping(self, grouping):
        """Set grouping of digits for reading numbers.

        Arguments:
        grouping -- 0 for default or a positive value
        specifying how many digits should be read together          
        """
        assert isinstance(grouping, int)

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_number_grouping(grouping)

    # Dictionaries
    
    def set_dictionary(self):
        """Set user dictionary. Exact behavior yet undefined."""

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        raise ErrorNotSupportedByServer

    # Audio Output
    
    def set_audio_output(self, method='playback'):
        """Set audio output method as described in TTS API.

        Arguments:
        method -- one of 'playback', 'retrieval'          
        """
        assert method in ('playback', 'retrieval')

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        # if possible, do not use output modules own playback
        # but use retrieval and o audio output here
        log.debug("REAL CAPABILITIES: " + str(self.current_driver.name))
        log.debug("REQUESTED: " + str(method) + " OFFERED: " + str(self.current_driver.real_capabilities))
        if method == 'playback':
            if 'retrieval' in self.current_driver.real_capabilities.audio_methods:
                self.current_driver.com.set_audio_output('retrieval')
                self.current_driver.audio_output = 'emulated_playback'
            else:
                self.current_driver.com.set_audio_output('playback')
                self.current_driver.audio_output = 'playback'
        elif method == 'retrieval':
            self.current_driver.com.set_audio_output('retrieval')
            self.current_driver.audio_output = 'retrieval'
        

    def set_audio_retrieval_destination(self, host, port):
        """Set destination for audio retrieval socket.

        Arguments:
        host -- IP address of the host machine as a string
        containing groups of three digits separated by a dot
        port -- a positive number specifying the host port          
        """
        assert isinstance(host, str)
        assert isinstance(port, int) and port > 0

        if not self.current_driver:
            raise ErrorDriverNotAvailable

        self.current_driver.com.set_audio_retrieval_destination(host, port)

    # Callbacks

    def dispatch_audio_event(self, event):
        """Method to be called whenever an audio
        event is available. Takes care of dispatching
        the audio event through the associated connection."""
        try:
            self._connection.send_audio_event(event)
        except ttsapi.server.ClientGone:
            pass
        
        

