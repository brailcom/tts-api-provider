#!/usr/bin/env python
#
# server.py - Server core
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
# $Id: server.py,v 1.7 2007-09-20 09:06:56 hanke Exp $

import sys
import socket
import threading
import thread
import traceback
import fcntl
import os
from copy import copy

# Import daemon functionality
import daemon

# TTS API module
import ttsapi

# Provider (core of implementation)
import provider

# Logging object
import logs

# Configuration import
from configuration import Configuration

# Audio output
import audio

class GlobalState(object):
    """Global state variables of TTS API provider"""

    # Id of last message received
    _last_message_id = 0

    # Index of messages and associated TTS API Provider
    # objects
    _messages = {}

    def __init__(self):
        """Initialize global state"""

        self._lock = thread.allocate_lock()

    def delete_messages_from_provider(self):
        raise NotImplementedError

    def message_provider(self, id):
        self._lock.acquire()
        id =  self._messages[id]
        self._lock.release()        
        return id

    def new_message_id(self, provider):
        self._lock.acquire()
        # Increment message id of last message
        self._last_message_id += 1
        id = self._last_message_id
        # Include the new message into the messages register
        self._messages[id] = provider
        self._lock.release()    
        # Return id of the new message
        return id

def serve_client(method, global_state, socket=None):
    """Runs one connection to TTS API Provider
    
    Arguments:
    method -- currently only 'socket'
    socket -- if method = 'socket', the client socket of the connection"""

    if method == 'socket':
        assert socket != None
        p = provider.Provider(logger=log,
                              configuration=conf,
                              audio=audio,
                              global_state=global_state)
        connection = ttsapi.server.TCPConnection(provider=p,
                                                 method='socket',
                                                 client_socket=socket,
                                                 logger=log)
        p.set_connection(connection)
        log.debug("Connection initialized, listening");
    else:
        raise NotImplementedError

    while True:
        try:
            connection.process_input()
        except ttsapi.server.ClientGone:
            # TODO: Better client identification in log message
            log.debug("Client on socket " + str(socket) + " gone")
            break

def audio_event_delivery(global_state):
    """Listens for events reported from audio server and send them
    to the appropriate clients"""


    log.info("Waiting for events in main")
    while True:
        try:
            log.info("WAITING NEXT EVENT")
            event = audio.audio_events.pop()
            log.info("EVENT RECEIVED")
            provider = global_state.message_provider(event.message_id)
            log.info("DISPATCHING EVENT")
            provider.dispatch_audio_event(event)
            log.info("EVENT DISPATCHED")
        except:
            print "EXCEPTION IN LATERAL THREAD, SEE LOGS\n"
            log.info("Exception in lateral thread: " + traceback.format_exc())

def create_pid_file():

    try:
        pidfile = open(conf.pidpath + "/" + conf.pidfile, 'w')
    except:
        log.error("Can't create pid file")
        raise

    try:
        fcntl.lockf(pidfile, fcntl.LOCK_EX)
    except:
        log.error("Can't lock pid file. TTS API Provider already running?")
        raise

    pidfile.write(str(os.getpid()))

    pidfile.close()

def destroy_pid_file():

    try:
        pidfile = open(conf.pidpath + "/" + conf.pidfile, 'rw')
    except:
        log.error("Can't open pid file")
        raise

    try:
        fcntl.lockf(pidfile, fcntl.LOCK_UN)
    except:
        log.error("Can't unlock pid file. TTS API Provider already running?")
        raise

    pidfile.close()
    os.remove(conf.pidpath + "/" + conf.pidfile)    

def main():
    """Initialization, configuration reading, start of server
    over sockets on given port"""
    global conf, log
    # TODO: Register signals
    #   SIGINT, SIGPIPE?, others?

    # At this stage, logging on stdout
    log = logs.Logging()

    log.info("Starting server")
    conf = Configuration(logger=log)

    # Create primary pid file
    create_pid_file()

    # Create global state
    global_state = GlobalState()

    if conf.mode == 'daemon':
        # Destroy pid file, will be re-created after fork
        destroy_pid_file()
        # Fork, detach pipes, chdir to '/' etc...
        daemon.createDaemon()
        create_pid_file()
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", conf.port))
    server_socket.listen(conf.max_simultaneous_connections)
        
    # Redirect logging to logfile
    log.init_stage2(conf)
    log.info("Configuration loaded")

    # Create pidfile
    
    log.info("Starting audio server")
    audio.port = conf.audio_port
    audio.host = conf.audio_host
    audio.init(logger=log)

    log.info("Starting audio event delivery thread")
    audio_event_delivery_thread = threading.Thread(target=audio_event_delivery,
                        name="Audio event delivery",
                        kwargs={'global_state':global_state})
    audio_event_delivery_thread.start()
    
    log.info("Waiting for connections")

    client_threads = []
    while True:
        (client_socket, address) = server_socket.accept()        
        client_provider = threading.Thread(target=serve_client,
                         name="Provider ("+str(client_socket.fileno())+")",
                         kwargs={'method':'socket',
                                 'socket':client_socket,
                                 'global_state':global_state})
        client_threads.append(client_provider)
        client_provider.start()
        log.info("Accepted new client, thread started")

if __name__ == "__main__":
    sys.exit(main())
else:
    main()

