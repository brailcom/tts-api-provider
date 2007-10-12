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
# $Id: connection.py,v 1.12 2007-10-12 08:11:25 hanke Exp $

# --------------- Connection handling ------------------------

import socket as socket_
import string
import sys
import os
from copy import copy

try:
    import threading
except:
    import dummy_threading as threading

import thread

from errors import *

def parse_list (data):
    """Sends a command which expects reply in the form of a list and
    returns the parsed reply.
     Returns a nested list. Each atom in the main list corresponds with one
    line of the reply and contains a list of constants on that line.
    """
    result = []
    for line in data:
        j = 0
        constr, quotes = False, False
        result_line = []
        for i in range(0, len(line)):
            if constr == True:
                if (line[i] == ' ' and quotes == False):
                    result_line.append(_nil_to_None(line[j:i]))
                    constr = False
                elif (line[i] == '"' and quotes == True):
                    result_line.append(line[j:i])
                    constr, quotes = False, False
            elif constr == False:
                if line[i] == '"':
                    j = i+1
                    constr, quotes = True, True
                elif line[i] != ' ':
                    j = i
                    constr, quotes = True, False
        result_line.append(line[j:].rstrip('"'))
        result.append(result_line)
    return result   

def _nil_to_None(str):
    if str == 'nil':
        return None
    else:
        return str

class Connection(object):
    NEWLINE = "\r\n"
    """New line delimiter """

    END_OF_DATA_SINGLE = "."
    """Data end marker single in a message"""

    END_OF_DATA_BEGIN = END_OF_DATA_SINGLE + NEWLINE
    """Data end marker on the beginning of a message"""

    END_OF_DATA = NEWLINE + END_OF_DATA_SINGLE + NEWLINE    
    """Data end marker (full)"""

    END_OF_DATA_ESCAPED_SINGLE = ".."
    "Escaping for END_OF_DATA_SINGLE"

    END_OF_DATA_ESCAPED_BEGIN = END_OF_DATA_ESCAPED_SINGLE + NEWLINE
    "Escaping for END_OF_DATA_BEGIN"

    END_OF_DATA_ESCAPED = NEWLINE + END_OF_DATA_ESCAPED_SINGLE + NEWLINE
    "Escaping for END_OF_DATA"    


    def __init__ (self, logger=None, side='client', provider=None):
        self._data_transfer = False
        self._server_side_buf = ''
        self.logger = logger
        self.provider = provider

        assert side in ('client', 'server')
        self._side = side

        if side == 'client':
            self._com_buffer = []
            self._reply_semaphore = threading.Semaphore(0)
            self._communication_thread = \
                threading.Thread(target=self._communication, kwargs={},
                                 name="Client communication thread")
            self._communication_thread.start()

    def _communication(self):
        """Handle incomming socket communication.

        Listens for all incomming communication on the socket, dispatches
        events and puts all other replies into self._com_buffer list in the
        already parsed form as (code, msg, data).  Each time a new item is
        appended to the _com_buffer list, the corresponding semaphore
        'self._reply_semaphore' is incremented.

        This method is designed to run in a separate thread.  The thread can be
        interrupted by closing the socket on which it is listening for
        reading."""

        while True:
            try:
                code, msg, data = self._recv_message()
            except IOError:
                # If the socket has been closed, exit the thread
                sys.exit()
            if code/100 != 7:
                # This is not an index mark nor an event
                self._com_buffer.append((code, msg, data))
                self._reply_semaphore.release()
                continue
            else: # code of type 7**
                # This is an event
                if self.provider:
                    self.provider.raise_event(code, msg, data)
                else:
                    raise "Can't raise event, no provider specified"

    def _recv_message(self):
        """Read server response or a callback
        and return the triplet (code, msg, data)."""
        data = []
        c = None
        while True:
            line = self._read_line()
            assert len(line) >= 4, "Malformed data received from server:" + line
            code, sep, text = line[:3], line[3], line[4:]
            assert code.isalnum() and (c is None or code == c) and \
                   sep in ('-', ' '), "Malformed data received from server:"  + line
            if sep == ' ':
                msg = text
                return int(code), msg, tuple(data)
            data.append(text)

    def _recv_response(self):
        """Read server response from the communication thread
        and return the triplet (code, msg, data)."""
        # TODO: This check is dumb but seems to work.  The main thread
        # hangs without it, when the Speech Dispatcher connection is lost.
        if not self._communication_thread.isAlive():
            raise "Communication error"
        self._reply_semaphore.acquire()
        # The list is sorted, read the first item
        response = self._com_buffer[0]
        del self._com_buffer[0]
        return response

    def _read_line(self):
        """Read one whole line from the communication channel.

        Read from the socket until the newline delimeter (given by the
        `NEWLINE' constant).  Blocks until the delimiter is read.
        
        """
        raise NotImplementedError

    def _arg_to_str(self, arg):
        if arg == None:
            return 'nil'
        else:
            str_arg = str(arg)
            if str_arg.find(' ') != -1:
                return '"'+str_arg+'"'
            else:
                return str_arg
                
    def _write(self, data):
        """Write data to output.

        data -- contains the data to be written including the
        necessary newlines and carriage return characters."""
        
        raise NotImplementedError
    

    def send_command (self, command, *args):
        """Send command with given arguments and read server response.

        Arguments can be of any data type -- they are all stringified before
        being sent to the server.

        Return a triplet (code, msg, data), where 'code' is a numeric 
        response code as an integer, 'msg' is a response message as string
        and 'data' is a tuple of strings (all lines of response data) when a
        response contains some data.
        
        Raise an exception in case of error response (non 2xx code).
        
        """        

        cmd = str.join(' ', [command,] + map(self._arg_to_str, args)) \
            + self.NEWLINE
        self._write(cmd)
        code, msg, data = self._recv_response()
        if code/100 != 2:
            raise TTSAPIError(code, msg, cmd)
        return code, msg, parse_list(data)

    def send_command_without_reply(self, command, *args):
        """Send command but do not wait for reply, see send_command()"""
        cmd = str.join(' ', [command,] + map(self._arg_to_str, args)) \
              + self.NEWLINE
        self._write(cmd)

    def send_reply(self, code, text, args = None):
        """Send reply to the client

        Arguments:
        code -- three digit number reply code
        args -- arguments as a list or None (for no arguments);
        each of them will be put on a separate
        line in the reply"""
        assert isinstance(code, int) and len(str(code)) == 3
        assert isinstance(text, str)
        reply = ''

        if not args == None:
            for a in args:
                if isinstance(a, tuple) or isinstance(a, list):
                    body = str.join(' ', map(self._arg_to_str, a))
                else:
                    body = str(a)
                reply += str(code) + '-' + body + self.NEWLINE
        reply += str(code) + ' ' + text + self.NEWLINE
        self._write(reply)


    def receive_line (self):
        """Receive one line of TTS API communication
        from client

        data -- the data including the trailing newline"""

        data = self._read_line()

        self.logger.debug("receive_line: received" + str(data))
        
        if not self._data_transfer:
            # TODO: Doublequotes
            
            return data.split(' ')
        else:
            if data == '.':
                _server_side_buf = self._server_side_buf.rstrip(self.NEWLINE)
                return ['.']
            elif data[:2] == '..':
                self._server_side_buf += '.' + self.NEWLINE
            else:
                self._server_side_buf += data + self.NEWLINE
                return None

    def data_transfer_on(self):
        assert self._data_transfer == False
        self._data_transfer = True
        self._server_side_buf = ''

    def data_transfer_off(self):
        assert self._data_transfer == True
        self._data_transfer = False

    def get_data(self):
        return self._server_side_buf
        

    def send_data (self, data):
        """Send multiline data and read server responsse.

        Returned value is the same as for 'send_command()' method.

        """

        # Escape the end-of-data sequence even if presented on the beginning
        if data[0:3] == self.END_OF_DATA_BEGIN:
            data = self.END_OF_DATA_ESCAPED_BEGIN + data[3:]

        if (len(data) == 1) and (data[0] == '.'):
            data = self.END_OF_DATA_ESCAPED_SINGLE

        data = string.replace(data, self.END_OF_DATA, self.END_OF_DATA_ESCAPED)
        self._write(data + self.END_OF_DATA)
        code, msg, rep_data = self._recv_response()
        if code/100 != 2:
            raise TTSAPIError(code, msg, data)
        return code, msg, rep_data

    def close (self):
        """Close the connection."""
        # Wait for the other thread to terminate
        
        if self._side == 'client':
            self._communication_thread.join()

class SocketConnection(Connection):

    _buffer = ''
    _data_transfer = False

    def __init__(self, host="127.0.0.1", port=6567, socket=None, logger=None,
                 provider=None, side='client'):
        """Init a connection to the server"""

        #self.logger = logger

        self._lock = thread.allocate_lock()
        
        if socket is None:
            if logger:
                logger.debug("Opening new socket")
            self._socket = socket_.socket(socket_.AF_INET, socket_.SOCK_STREAM)
            self._socket.setsockopt(socket_.SOL_SOCKET, socket_.SO_REUSEADDR, 1)
            self._socket.connect((socket_.gethostbyname(host), port))
        else:
            if logger:
                logger.debug("Using existing socket")
            self._socket = socket

        Connection.__init__(self, logger=logger, side=side, provider=provider)

    def _read_line(self):
        """Read one whole line from the socket.
        
        Read from the socket until the newline delimeter (given by the
        `NEWLINE' constant).  Blocks until the delimiter is read.
        
        """
        pointer = self._buffer.find(self.NEWLINE)
        while pointer == -1:
            res = self._socket.recv(1024)
            # WARNING: I don't know if this is correct, python library
            # documentation is unclear here, but it seems to work
            if res == "":
                raise IOError
            self._buffer += res
            pointer = self._buffer.find(self.NEWLINE)
        line = self._buffer[:pointer]
        self._buffer = self._buffer[pointer+len(self.NEWLINE):]
        if self.logger:
            self.logger.debug("Received over socket: %s",  line)
        return line

    def read_data(self, bytes):
        """Read the specified amount of data"""
        if bytes > len(self._buffer):
            # First read data from buffer
            result  = self._buffer
            bytes_to_read = bytes-len(self._buffer)
            self._buffer = ""
            # Calculate how much more data do we have to read
        else:
            # Data waiting in buffer is larger than what
            # we actually want to read now
            result = copy(self._buffer[:bytes])
            # Strip the already read data from buffer
            self._buffer = self._buffer[bytes:]
            bytes_to_read = 0

        while bytes_to_read > 4096:
            data = self._socket.recv(4096)
            result += data
            bytes_to_read -= len(data) 
        
        while bytes_to_read > 0:
            data = self._socket.recv(bytes_to_read)
            result += data
            bytes_to_read -= len(data) 
        
        return result

    def _write(self, data):
        """Write data to output.

        data -- contains the data to be written including the
        necessary newlines and carriage return characters."""
 
        try:
            self._lock.acquire()
            try:
                self._socket.send(data)
            except:
                raise IOError
            # WARNING: Seems not to bee needed, but may be cause
            # of problems too. I don't know.
            #self._socket.flush()
            if self.logger: 
                self.logger.debug("Sent over socket: %s",  data)
        finally:
            self._lock.release()
        
    def fileno(self):
        return self._socket.fileno()
    
    def close (self):
        """Close the connection."""
        try:
            socket_.socket.shutdown(self._socket, os.O_RDWR)
        except:
            self.logger.debug("Can't shutdown socket")
            raise IOError
        if self.logger:
            self.logger.debug("Socket connection closed")
        Connection.close(self)

class PipeConnection(Connection):
    """Connection through pipes"""
    
    NEWLINE = "\r\n"

    def __init__(self, pipe_in=sys.stdin, pipe_out=sys.stdout, logger=None, side='client',
                 provider=None):
        """Setup pipes for communication

        pipe_in -- pipe for incomming communication (replies)
        pipe_out -- pipe for outcomming communication (commands, data)
        """
        self.pipe_in=pipe_in
        self.pipe_out=pipe_out

        Connection.__init__(self, logger=logger, side=side, provider=provider)

    def _read_line(self):
        """Read one whole line from the socket.
        
        Read from the socket until the newline delimeter (given by the
        `NEWLINE' constant).  Blocks until the delimiter is read.
        
        """
        
        line = self.pipe_in.readline().rstrip(self.NEWLINE)
        if self.logger:
            self.logger.debug("Received over pipe: %s",  line)

        if len(line) == 0:
            raise IOError
            
        return line
        
    def _write(self, data):
        """Write data to output.
        data -- contains the data to be written including the
        necessary newlines and carriage return characters."""
        self.pipe_out.write(data)
        self.pipe_out.flush()
        if self.logger: 
            self.logger.debug("Sent over pipe: %s",  data)

    def close (self):
        """Close the connection."""
        self.pipe_out.close()
        self.pipe_in.close()
        Connection.close(self)

