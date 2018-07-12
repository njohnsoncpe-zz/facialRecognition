import socket
import os
import time
from utils.network_utils import ThreadingExample

server = ThreadingExample('', 20004)

try:
    while True:
        server.appendToMessageBuff(b'hey')
        time.sleep(5)
except KeyboardInterrupt:
    server.sock.close()
