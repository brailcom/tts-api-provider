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
# $Id: server.py,v 1.2 2006-08-09 12:06:04 hanke Exp $

import sys
import socket
import thread

# TTS API module
import ttsapi

# Provider (core of implementation)
import provider

# Logging object
from logs import log

# Configuration object
# Automatically fills conf with default values and parses command line options
from configuration import conf

def serve_client(method, socket=None):
    """Runs one connection to TTS API Provider
    
    Arguments:
    method -- currently only 'socket'
    socket -- if method = 'socket', the client socket of the connection"""

    if method == 'socket':
        print socket
        assert socket != None
        p = provider.Provider()    
        connection = ttsapi.server.TCPConnection(provider=p,
                                                 client_socket=socket,
                                                 logger=log)
    while True:
        try:
            connection.process_input()
        except ttsapi.server.ClientGone:
            break
    return

def main():
    """Initialization, configuration reading, start of server
    over sockets on given port"""

    # TODO: Check/Create pid file
    # TODO: Register signals
    #   SIGINT, SIGPIPE?, others?
    
    log.info("Starting server")
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", conf.port))
    server_socket.listen(conf.max_simultaneous_connections)
    
    log.init_stage2(conf)
    log.info("Configuration loaded")
    
    log.info("Waiting for connections")
    
    while True:
        (client_socket, address) = server_socket.accept()        
        thread.start_new_thread(serve_client, ('socket',client_socket))

print __name__

if __name__ == "__main__":
    sys.exit(main())
else:
    main()

