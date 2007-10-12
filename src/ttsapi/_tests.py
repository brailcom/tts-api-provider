#!/usr/bin/env python

# Copyright (C) 2007 Brailcom, o.p.s.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public Licensex1 as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Tests of TTS API functionality using unittest module"""

import unittest
import time

import ttsapi
import logging
import sys

class _TTSAPITest(unittest.TestCase):
        
    def setUp(self):
        stdout_handler = logging.StreamHandler(sys.stdout)
        self.logger = logging.Logger('TTS API Tests',
                                     level=logging.DEBUG)
        #self.logger.addHandler(stdout_handler)
        self._client = ttsapi.client.TCPConnection(method='socket',
                                                   logger=self.logger)

    def tearDown(self):
        self._client.close()


received_callbacks = []


def _my_callback(event):        
    global received_callbacks
    print """Received callback %(type)s for message %(message_id)s . 
  Position in text and audio %(pos_text)s %(pos_audio)s.
  Event number %(n)s
  Index mark name %(name)s""" % event.attributes_dictionary()
    received_callbacks += [event]


class CallbackTest(_TTSAPITest):
    """A set of tests which may be evaluated automatically.

    Please put all tests which require a user to listen to their output to the
    VoiceTest below.

    """

    received_callbacks = []

    def test_callbacks(self):
        "Testing callbacks"

        expected_callbacks = {}

        # Register callbacks
        self._client.register_callback(['message_start', 'message_end'],
                                       _my_callback)
        
        # Say some messages
        id1 = self._client.say_text("This is a callbacks test!")
        expected_callbacks[id1] = ['message_start', 'message_end']

        id2 = self._client.say_text("This is a second callbacks message.")
        expected_callbacks[id2] = ['message_start', 'message_end']


        # Wait so that we are sure we have received the callbacks
        time.sleep(10)

        global received_callbacks
        received_callbacks_names = {}
        # Check that we received all callbacks
        for callback in received_callbacks:
            if callback.message_id not in received_callbacks_names:
                received_callbacks_names[callback.message_id] = []
            received_callbacks_names[callback.message_id] += [callback.type]
        
        err = ""

        for id, list in expected_callbacks.iteritems():
            for callback_name in list:
                if callback_name not in received_callbacks_names[str(id)]:
                    err += "Callback " + callback_name + " was not received for message id " + str(id)

        self.logger.info("LIST OF CALLBACKS EXPECTED: " + str(received_callbacks_names))
        self.logger.info("LIST OF CALLBACKS RECEIVED: " + str(received_callbacks_names))

        if len(err)>0:
            err += "THIS FAILURE ONLY INDICATES A POSSIBLE ERROR. It is timing dependent and may" \
                   "fail on very slow synthesizers"
            raise err

class AutomaticTest(_TTSAPITest):
    """This set of tests requires a user to listen to it.

    The success or failure of the tests defined here can not be detected
    automatically.

    """
    
    def test_drivers_list(self):
        """Driver listing test"""

        drivers_list = self._client.drivers()
        self.logger.debug("Available drivers:")

        for description in drivers_list:
            self.logger.debug(str(description))

    def test_drivers_capabilities(self):
        """Retrieve driver capabilities for all available drivers"""
        drivers_list = self._client.drivers()
        for driver in drivers_list:
            self.logger.debug("Capabilities of " + driver.synthesizer_name)
            self._client.set_driver(driver.driver_id)
            capabilities = self._client.driver_capabilities()
            self.logger.debug(capabilities)


class VoiceTest(_TTSAPITest):
    """This set of tests requires a user to listen to it.

    The success or failure of the tests defined here can not be detected
    automatically.
    """
    
    def test_speech(self):
        self._client.say_text("Hello, this is plain text.")
        self._client.say_text("<speak>Hello, this is plain SSML.</speak>")
        
    def test_prosody_parameters(self):
        """Test rate, pitch and volume settings"""
        self._client.set_rate(100)
        self._client.set_pitch(100)
        self._client.set_volume(100)
        self._client.say_text("Rate and pitch set to 100")
    
    def test_punctuation_modes(self):
        """Test supported punctuation modes"""
        for mode in self._client.driver_capabilities().punctuation_modes:
            self._client.set_punctuation_mode(mode)
            self._client.say_text("Punctuation ?!.<>;")
    
    def test_punctuation_detail(self):
        """Test punctuation detail settings"""
        if self._client.driver_capabilities().can_set_punctuation_detail:
            self._client.set_punctuation_detail("?>.")
            self._client.say_text("Punctuation ?!.<>")

    def test_capital_letters_mode(self):
        """Test supported capitall letters modes"""
        for mode in ['no', 'spelling', 'icon', 'pitch']:
            self._client.set_capital_letters_mode(mode)
            self._client.say_text("This is a sentence with FIRST capital.")

if __name__ == '__main__':
    unittest.main()


