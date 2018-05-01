#!/usr/bin/env python
import socket
import numpy as np

port = 10000
buf = 1024
fName = 'img.jpg'
timeOut = 0.05


def foo():
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', port))
        f = open(fName, 'wb')

        data, address = s.recvfrom(buf)
        try:
            while (data):
                f.write(data)
                s.settimeout(timeOut)
                data, address = s.recvfrom(buf)
        except:
            f.close()
            s.close()


if __name__ == '__main__':
    foo()
