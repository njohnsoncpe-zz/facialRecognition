import socket
import threading
import select
import queue
import time


class ThreadedServer(object):
    """ Threading example class
    The run() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, host, port, interval=1):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval
        self.host = host
        self.port = port
        self.isClientReady = False
        self.isClientConnected = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(0)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.inputs = [self.sock]
        self.outputs = []
        self.message_queues = {}
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        self.sock.listen(5)
        # print("listening")

        while self.inputs:
            readable, writeable, errored = select.select(
                self.inputs, self.outputs, self.inputs)
            # print(self.inputs, self.outputs)

            for s in readable:
                if s is self.sock:
                    client, address = self.sock.accept()
                    self.inputs.append(client)
                    print("connection from:", address)
                    client.settimeout(60)
                    client.setblocking(0)
                    self.message_queues[client] = queue.Queue()
                else:
                    data = s.recv(1024)
                    if data:
                        print(data.decode('utf-8'))
                        # A readable client socket has data
                        if b'HELLO' in data:
                            self.isClientConnected = True
                            print("Hello Client at: " + str(s.getpeername()
                                                            [0]) + ':' + str(s.getpeername()[1]))
                            print(self.inputs, self.outputs)
                            if s not in self.outputs:
                                self.outputs.append(s)
                            # Add output channel for response
                            self.message_queues[s].put(data)

                        elif b'READY' in data:
                            self.isClientReady = True
                            print("Client at: " + str(s.getpeername()
                                                      [0]) + ':' + str(s.getpeername()[1]) + " is ready")
                            # Add output channel for response
                            self.message_queues[s].put(data)

                        elif b'GOODBYE' in data:
                            self.isClientReady = False
                            self.isClientConnected = False
                            print("Removing client at " + str(s.getpeername()
                                                              [0]) + ':' + str(s.getpeername()[1]))
                            if s in self.inputs:
                                self.inputs.remove(s)
                            if s in self.outputs:
                                self.outputs.remove(s)
                            # print("Client at: " + str(s.getpeername()
                            #                           [0]) + ':' + str(s.getpeername()[1]) + " is disconnecting")

            for s in writeable:
                # print("writeables:")
                # print(writeable)
                try:
                    next_msg = self.message_queues[s].get_nowait()
                except queue.Empty:
                    pass
                    # print(">>Output Queue is empty for")
                    # print(s.getpeername())
                    # self.outputs.remove(s)
                else:
                    # print("Sending: " + next_msg.decode('utf-8') +
                    #       " to " + str(s.getpeername()[0]) + ':' + str(s.getpeername()[1]))
                    totalsent = 0
                    sizeObj = len(next_msg)
                    # print(self.isClientReady)
                    while (totalsent < sizeObj and self.isClientReady and self.isClientConnected):
                        # print(self.isClientConnected)
                        # print(self.isClientReady)

                        sent = s.send(next_msg[totalsent:])
                        # print(next_msg.decode('utf-8'))
                        # print(sent)
                        s.send(b'\n')
                        if sent == 0:
                            raise RuntimeError('Socket is broke')
                        totalsent += sent
                    # print("sent msg")

            for s in errored:
                print('>>handling exceptional condition for')
                print(s.getpeername())
                self.inputs.remove(s)
                if s in self.outputs:
                    self.outputs.remove(s)
                s.close()

                del self.message_queues[s]

    def appendToMessageBuff(self, data):
        for s in self.outputs:
            print(data)
            # print("appended to obuff for " + s.getpeername()[0])
            self.message_queues[s].put(data)

