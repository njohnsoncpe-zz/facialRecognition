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
        self.oldData = ''
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        self.sock.listen(5)
        # print("listening")

        while self.inputs:
            # print(self.inputs[0].getsockname())
            readable, writeable, errored = select.select(
                self.inputs, self.outputs, self.inputs)

            for s in readable:
                if s is self.sock:
                    client, address = self.sock.accept()
                    self.inputs.append(client)
                    print("connection from:", address)
                    client.settimeout(5)
                    client.setblocking(0)
                    self.message_queues[client] = queue.Queue(maxsize=2)
                    print(len(self.inputs))
                    print(len(self.outputs))
                    print(len(self.message_queues))
                else:
                    data = s.recv(64)
                    if data:
                        print(data.decode('utf-8'))
                        # A readable client socket has data
                        if b'HELLO' in data:
                            self.isClientConnected = True
                            print("Hello Client at: " + str(s.getpeername()
                                                            [0]) + ':' + str(s.getpeername()[1]))
                            # print(self.inputs, self.outputs)
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
                                print("removed from inputs")
                            if s in self.outputs:
                                self.outputs.remove(s)
                                print("removed from outputs")
                            
                            for k in self.message_queues.keys():
                                print(k)
                                print(type(k))
                            
                            # del self.message_queues[s.getpeername()[0]]

            for s in writeable:
                try:
                    next_msg = self.message_queues[s].get_nowait()
                except queue.Empty:
                    pass
                else:
                    totalsent = 0
                    sizeObj = len(next_msg)
                    while (totalsent < sizeObj and self.isClientReady and self.isClientConnected):
                        sent = s.send(next_msg[totalsent:])
                        s.send(b'\n')
                        if sent == 0:
                            raise RuntimeError('Socket is broke')
                        totalsent += sent

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
            if self.message_queues[s].full() == False:
                self.message_queues[s].put(data)
            else:
                print("Msg Queue is full")
            # print("appended to obuff for " + s.getpeername()[0])
            


