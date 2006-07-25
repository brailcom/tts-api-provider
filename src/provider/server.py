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
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# 
# $Id: server.py,v 1.1 2006-07-25 12:56:17 hanke Exp $

import sys
import socket
import thread

import provider
import ttsapi

class configuration(object):
    port = 6562
    max_simultaneous_connections = 5

def serve_client(socket):
    """Runs one connection to TTS API Provider
    
    Arguments:
    socket -- the client socket of the connection"""

    p = provider.Provider()    
    connection = ttsapi.server.TCPConnection(provider=p, client_socket=socket)

    while True:
        connection.process_input()
    
    # When the end of the world comes...
    socket.close()
    

def main():
    """Initialization, configuration reading, start of server"""
    # TODO: Parse command line options
    # TODO: Check/Create pid file
    # TODO: Register signals
    #   SIGINT, SIGPIPE?, others?

    print "Server starting"
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", configuration.port))
    server_socket.listen(configuration.max_simultaneous_connections)
    print "Waiting for connections"
    
    while True:
        (client_socket, address) = server_socket.accept()        
        thread.start_new_thread(serve_client, (client_socket,))
      

print __name__

if __name__ == "__main__":
    sys.exit(main())
else:
    main()

