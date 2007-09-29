# audio.py - Audio subsystem for TTS API Provider
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
# $Id: audio.py,v 1.6 2007-09-29 11:15:28 hanke Exp $

"""Audio server, accepts connections with audio data and events, plays
audio data and emits events.

Audio server runs in two threads:
    1) The main thread accepts connections and maintains the audio buffers
    2) The secondary thread accepts events and takes care of playback and
        output events emission"""

import threading
import socket
import select
import datetime
import time
import sleep

#Import OpenAL Python bindings
import pyopenal

import event
import ttsapi

from ttsapi.connection import *
from ttsapi.structures import AudioEvent
from configuration import Configuration

messages_in_sources_sleeper = sleep.Sleeper()

class MessageNotInPlayback(Exception):
    pass

class PlaybackInfo(object):
    """Information about playback of a track"""
    # datetime object

    # Time when audio was started or None if not yet started playback
    started = None
    
    # Time when audio was stopped or None if not stopped
    # stopped = None

    # If the track was rewinded, the rewinded time is saved here
    rewinded = datetime.timedelta()

    # Audio source
    source = None

# Dictionary of message_id:PlaybackInfo() entries
messages_in_playback = {}

# --- AUDIO FUNCTIONALITY ---

class CtrlRequest(event.Event):
    _attributes = {
        'type': ("Type of the event",
            ("accept", "play", "stop", "discard")),
        'message_id': ("ID of the message",
                       ("accept", "play", "stop", "discard"))
    }

class Audio(object):
    """Audio output through Pyopenal"""
    awaiting_message_data = []
    sources = {} # dictionary message_id:source
    
    def __init__(self):
        """Initialize audio"""
        pyopenal.init()
        self.listener = pyopenal.Listener(44100)
        
    def accept(self, message_id):
        """Accept a track for message_id. This function 
        initializes the necessary data structures and tells
        the audio server to wait for incomming data."""
        global messages_in_sources_sleeper
        
        if message_id in self.awaiting_message_data:
            raise "Message already in accept list"

        log.debug("Adding message" +str(message_id)+"into awaiting_message_data :"
                  +str(self.awaiting_message_data))
        self.awaiting_message_data.append(message_id)
        
        source = pyopenal.Source()
        self.sources[message_id] = source
        log.debug("Message " + str(message_id)  +" accepted for playback")
        messages_in_sources_sleeper.interrupt()        

    def play(self, message_id):
        """Start playback of the given message_id. Do nothing if it is
        already being played."""

        if messages_in_playback.has_key(message_id):
            pass

        # Start playback
        source = self.sources[message_id]
        source.play()

        # Save playback info
        messages_in_playback[message_id] = PlaybackInfo()
        messages_in_playback[message_id].source = source
        messages_in_playback[message_id].started = datetime.datetime.now()
        
        log.debug("Source for message " + str(message_id)  +" playing")
    
    def stop(self, message_id):
        """Stop playback of track assigned to given message_id
        and discard it (seee Audio.discard())"""

        if not messages_in_playback.has_key(message_id):
            raise MessageNotInPlayback

        # Stop playback
        source = self.sources[message_id]
        source.stop()
        
        # Remove playback info
        del messages_in_playback[message_id]

        # Discard this track
        self.discard(message_id)
    
    def discard(self, message_id):
        """Discard track assigned to message_id"""

        # If still playing, stop
        if messages_in_playback.has_key(message_id):
            self.stop(message_id)
    
        # Remove playback info, not awaiting data any more, remove source,
        # clean-up
        if message_id in self.awaiting_message_data:
            self.awaiting_message_data.remove(message_id)
        if message_id in self.sources:
            del self.sources[message_id]

    def set_volume(self, message_id, volume):
        """Set audio volume. Volume is a floating point number.
        0.0 is silent, 1.0 is the default volume. Value greater
        than 1.0 means amplification, but may be truncated at some
        value to prevent overflows."""

        log.debug("Setting volume for " + str(message_id) + " to " + str(volume))
        if message_id not in self.sources:
            raise "Unknown source"

        source = self.sources[message_id]
        try:
            # Set volume through PyOpenAL
            source.gain = float(volume)
        except Exception, e:
            log.error("Can't set volume. Received exception: " + str(e))

    def add_data(self, message_id, data, format, sample_rate,
                 channels, encoding):
        """Add new data to track assigned to message_id with the
        given format, sample_rate, number of channels and encoding.
        Currently only handles raw PCM."""
        
        log.debug("Adding data with length " + str(len(data)))
        if message_id not in self.awaiting_message_data:
            log.debug("Data for " + str(message_id) + " rejected. " \
                          "Message not in awaiting_message_data list")
            return

        if channels == 1:
            format = pyopenal.AL_FORMAT_MONO16
        elif channels == 2:
            format = pyopenal.AL_FORMAT_STEREO16
        else:
            raise "Unsupported number of channels " + str(channels)

        # Generate a new buffer and fill it with the data
        buffer = pyopenal.alGenBuffers(1)
        pyopenal.alBufferData(buffer, format, data, sample_rate)

        # Queue the buffer for the message_id track source
        source = self.sources[message_id]
        source.queue_buffers(buffer)
        log.debug("Data added for message " + str(message_id) )

        # If state is not AL_PLAYING (playback ran out of data), we must first
        # unqueue old buffers or otherwise playback would start from the
        # beginning again.
        # WARNING: This might be a problem for rewinding if done on audio level.
        state = source.get_state()
        if state != pyopenal.AL_PLAYING:
            log.debug("Unqueueing audio data")
            # TODO: Unfortunatelly this is not supported in pyopenal, I've contacted
            # the author. It will hopefully be fixed later.
            #n = pyopenal.alGetSourcei(source, pyopenal.AL_BUFFERS_PROCESSED)
            # WARNING: ...so we just use a number that looks big enough, relying on
            # the fact that only already processed buffers are unqueued with the
            # Source.unqueue_buffers method
            source.unqueue_buffers(256)
            self.play(message_id)


# --- AUDIO SERVER IMPLEMENTATION ---

def init(logger):
    """Initialize the audio subsystem."""
    global audio_ctrl_request
    global audio_events
    global conf, log
    global event_list

    log = logger
    conf = Configuration(logger=log)

    # Setup audio_ctrl_request for communication
    # of the audio subsystem with outside world
    event_list = {}
    audio_ctrl_request = event.EventQueue()
    audio_events = event.EventQueue()

    # Sleeper for events dispatching
    event_sleeper = sleep.Sleeper()

    # Start playback thread
    playback_thread = threading.Thread(target=playback,
                                    name="Audio-playback")
    playback_thread.start()

    # Start audio events handling thread
    events_thread = threading.Thread(target=events,
                                     name="Audio-events",
                                     kwargs = {'sleeper' : event_sleeper})
    events_thread.start()

    # Start connection handling thread
    connection_handling_thread = threading.Thread(
        target=connection_handling,
        name="Audio-connections",
        kwargs = {'event_sleeper' : event_sleeper})
    connection_handling_thread.start()
    
    global audio
    audio = Audio()
    
def receive_data(socket, event_sleeper):
    """Receive a block of data as defined in TTS API
    over socket"""

    header = socket.receive_line()

    # HEADER
    if len(header) != 3:
        raise "Bad syntax on audio socket"
    head = header[0]
    msg_id = int(header[1])
    block_number = int(header[2])
    
    if head != "BLOCK":
        raise "Bad syntax on audio socket (BLOCK expected)"
    
    log.info("Receiving audio block number " + str(block_number)
    + " for message id " + str(msg_id))

    # PARAMETERS SECTION
    param_header = socket.receive_line()
    if param_header != ['PARAMETERS']:
        raise "Ommited PARAMETERS section on audio socket"
    
    data_length = None
    while True:
        parameter_line = socket.receive_line()
        log.debug("Parameter line: " + str(parameter_line));
        if parameter_line == ['END', 'OF', 'PARAMETERS']:
            break
        if parameter_line[0] == 'data_length':
            data_length = int(parameter_line[1])
            log.debug("Setting data lenght to " + str(data_length))
        if parameter_line[0] == 'sample_rate':
            sample_rate = int(parameter_line[1])
            log.debug("Setting sample rate to " + str(sample_rate))
    
    if data_length == None:
        raise "Unspecified data length"

    # EVENTS SECTION
    event_header = socket.receive_line()
    event_lines = []
    global event_list

    if not event_list.has_key(msg_id):
        event_list[msg_id] = []
    if event_header == ['EVENTS']:
        while True:
            event_line = socket.receive_line()
            if event_line == ['END', 'OF', 'EVENTS']:
                break
            event_lines.append(event_line)

        for entry in event_lines:
            log.debug("Event line being processed:" + str(entry))
            if entry[0] in ('message_start', 'message_end'):
                event_list[msg_id].append(AudioEvent(type=entry[0],
                                                     pos_text=int(entry[2]),
                                                     pos_audio=int(entry[3]),
                                                     message_id=msg_id))
            elif entry[0] in ('word_start', 'word_end', 'sentence_start',
                              'sentence_end'):
                event_list[msg_id].append(AudioEvent(type=entry[0],
                                                     n = int(entry[1]),
                                                     pos_text = int(entry[2]),
                                                     pos_audio = int(entry[3]),
                                                     message_id=msg_id))
            elif entry[0] == 'index_mark':
                event_list[msg_id].append(AudioEvent(type=entry[0],
                                                     name = entry[1],
                                                     pos_text = int(entry[2]),
                                                     pos_audio = int(entry[3]),
                                                     message_id=msg_id))
        if len(event_lines) > 0:
            # Interrupt event sleeper and give it a chance
            # to recalculate when the next callback should be
            # sent
            event_sleeper.interrupt()

        data_header = socket.receive_line()
    else:
        data_header = event_header

    # DATA SECTION
    if data_header != ['DATA']:
        raise "Missing DATA section"
    
    if (data_length != 0):
        audio_data = socket.read_data(data_length)
    else:
        audio_data = ""
    data_footer = socket.receive_line()
    log.debug("Data footer: " + str(data_footer))
    if data_footer != ['END', 'OF', 'DATA']:
        raise "Missing END OF DATA"
    
    # Block of data read, add data to audio
    log.debug("OK data received, sending to audio")
    audio.add_data(msg_id, audio_data, "raw", sample_rate, 1, "S16_LE")
    
def connection_handling(event_sleeper):
    """Handle incomming connections and read data into buffers
    in a separate thread."""
    
    log.info("Starting audio server")

    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", conf.audio_port))
    server_socket.listen(conf.max_simultaneous_connections)

    log.info("Waiting for audio connections")

    client_list = [server_socket,]
    while True:
        log.debug("Waiting for activity")
        ready_to_read, ready_to_write, in_error = select.select(client_list, (), client_list)
        log.info("Socket activity: " + str(ready_to_read) + " " + str(ready_to_write) + " " \
                 + str(in_error))
        for sock in in_error:
            if sock.fileno() == server_socket.fileno():
                log.error("Master server audio socket in error, aborting.")
                raise "Master server audio socket in error"
            else:
                log.info("Audio client on socket " + str(sock.fileno()) + " in error.")
                client_list.remove(sock)        

        for sock in ready_to_read:
            if sock.fileno() == server_socket.fileno():
                (client_socket, address) = server_socket.accept()
                log.info("Adding new audio client on socket " + str(client_socket.fileno()))
                client_list.append(SocketConnection(socket=client_socket,
                                                    logger=log, side='server'))
            else:
                try:
                    log.info("Receiving data from socket " + str(sock.fileno()))
                    receive_data(sock, event_sleeper)
                except IOError:
                    log.info("Audio client on socket " + str(sock.fileno()) + " gone.")
                    client_list.remove(sock)        

def playback():
    """Listen for events and play tracks in a separate thread."""

    while True:
        log.debug("Waiting for controll request")
        ev = audio_ctrl_request.pop()
        log.debug("Received event " + ev.type +" "+ str(ev.message_id))
        
        if ev.type == 'accept':
            audio.accept(ev.message_id)
        elif ev.type == 'play':
            audio.play(ev.message_id)
            pass
        elif ev.type == 'stop':
            audio.stop(ev.message_id)
        elif ev.type == 'discard':
            audio.discard(ev.message_id)
        else:
            raise "Unknown event"

def events(sleeper):
    """Keep track of actual playing time of all messages, messages currently in
    playback and calculate positions of events. When a message event gets
    negative position in time, dispatch the appropriate notice event."""

    # message_event.clear()

    while True:
        #log.debug("Loop in events")
        now = datetime.datetime.now()
        # NOTE: This is roughly a day in miliseconds
        NOT_ASSIGNED = 86000000
        min = NOT_ASSIGNED

        for id, message in messages_in_playback.iteritems():
            state = message.source.get_state()
            #TODO: Possible race with message.started
            if message.started != None:
                since_start = now-message.started
            else:
                continue

            if state == pyopenal.AL_STOPPED:
                if message.started != None:
                    message.rewinded += since_start
                    message.started = None
                else:
                    # If we detected stop in the previous cycle already,
                    # there is no need to check events again
                    continue
                
            playback_time = since_start + message.rewinded
            for event in event_list[id]:
                if not event.dispatched:
                    dte = datetime.timedelta(milliseconds=event.pos_audio)-playback_time
                    log.debug("For event " + event.type + " dte =" + str(dte))
                    # Convert dte into microseconds
                    ms = (dte.days*24*3600 + dte.seconds)*1000 + dte.microseconds/1000
                    log.debug("For event " + event.type + " ms =" + str(ms))
                    if ms < 0:
                        audio_events.push(event)
                        event.dispatched=True
                    elif ms < min:
                        min = ms

        # Sleep as long as we can, but not less than 5 miliseconds.
        if min > 5:
            # The following sleep is interrupted each time new
            # events are added to the event_list, so that
            # the sleeping time can be recalculated
            log.debug("Sleeping " + str(min) +" ms")
            sleeper.sleep(min/1000.0)
        else:
            log.debug("Sleeping 5ms")
            sleeper.sleep(0.005)
        
        #TODO: Calculate callback timing errors, check the performance

def post_event(type, message_id, blocking=False):
    """Post event to controll audio server"""
    global messages_in_sources_sleeper

    log.debug("Posting event " + type + " " + str(message_id))
    audio_ctrl_request.push(CtrlRequest(type=type, message_id=message_id))
    
    if blocking:
        # Wait until the request is processed
        while message_id not in audio.sources:
            messages_in_sources_sleeper.sleep(2*60)
