#!/usr/bin/env python
#
# server.py - Server core
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
# $Id: server.py,v 1.3 2006-12-29 22:32:47 hanke Exp $

import sys
import socket
import threading

# TTS API module
import ttsapi

# Provider (core of implementation)
import provider

# Logging object
import logs
from configuration import Configuration
from copy import copy

# Configuration object
# Automatically fills conf with default values and parses command line options
#from configuration import conf

# Audio output
import audio

def serve_client(method, socket=None):
    """Runs one connection to TTS API Provider
    
    Arguments:
    method -- currently only 'socket'
    socket -- if method = 'socket', the client socket of the connection"""

    if method == 'socket':
        print socket
        assert socket != None
        log.debug("starting in server_client")
        p = provider.Provider(logger=log, configuration=conf, audio=audio)
        log.debug("testik")
        log.debug("tt2")
        connection = ttsapi.server.TCPConnection(provider=p,
                                                method='socket',
                                                 client_socket=socket,
                                                 logger=log)
        log.debug("Connection initialized, listening");
    while True:
        try:
            connection.process_input()
        except ttsapi.server.ClientGone:
            break
    return

def audio_event_delivery():
    """Listens for events reported from audio server and send them
    to the appropriate clients"""

    while True:
#TODO:        

def main():
    """Initialization, configuration reading, start of server
    over sockets on given port"""
    global conf, log
    # TODO: Check/Create pid file
    # TODO: Register signals
    #   SIGINT, SIGPIPE?, others?
    
    log = logs.Logging()
    
    log.info("Starting server")
    conf = Configuration(logger=log)
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", conf.port))
    server_socket.listen(conf.max_simultaneous_connections)
    
    log.init_stage2(conf)
    log.info("Configuration loaded")
    
    log.info("Starting audio server")
    audio.init(logger=log)
    audio.port = conf.audio_port
    audio.host = '127.0.0.1'

    log.info("Starting audio event delivery thread")
    audio_event_delivery_thread = threading.Thread(target=audio_event_delivery,
                        name="Audio event delivery")
    audio_event = event.AudioEvent()
    audio_event_ctl = threading.AudioEvent()
    
    log.info("Waiting for connections")

    client_threads = []
    while True:
        (client_socket, address) = server_socket.accept()        
        client_provider = threading.Thread(target=serve_client,
                         name="Provider ("+str(client_socket.fileno())+")",
                         kwargs={'method':'socket', 'socket':client_socket})
        client_threads.append(client_provider)
        client_provider.start()
        log.info("Accepted new client, thread started")
#        start_new_thread(serve_client, ('socket', client_socket))

if __name__ == "__main__":
    sys.exit(main())
else:
    main()

