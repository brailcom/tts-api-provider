import ttsapi
import time
import logging
import sys

log = logging.Logger('Test', level=logging.DEBUG)
stdout_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(message)s")
stdout_handler.setFormatter(formatter)
log.addHandler(stdout_handler)

log.info("Trying to connect")
c = ttsapi.client.TCPConnection()
log.info("Connected")

c.set_driver('festival')

log.info("Testing first message");
c.say_text("Testing first message");
time.sleep(3)

log.info("Sending real TEST message")
c.say_text("""
Hello, this is just a test message, ok? Hello, this is just a test message, ok?
"""
)
log.info("TEST message sent");

time.sleep(3)
log.info("Closing connection");
c.close()
log.info("Connection closed");
