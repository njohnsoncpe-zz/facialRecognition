# import cv2
# from threading import Thread
# import socket, select

# BUFFER_SIZE = 16
# MSGLEN = 20


# class DetectionDataSocket:
#     def __init__(self):
#         self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     #def getConnections(self):


#     def connect(self, port):
#         port = port
#         self.server_socket.bind(('', port))
#         print(">>Listening on port", self.server_socket.getsockname()[1])
#         read_list = [self.server_socket]
#         while True:
#             readable, writeable, errored = select.select(read_list, [], [])
#             for s in readable:
#                 if s is self.server_socket:
#                     client_socket, address = self.server_socket.accept()
#                     read_list.append(client_socket)
#                     print("Connection from", address)
                

#     def send(self, data, dataLen):
#         totalSent = 0
#         while totalSent < dataLen:
#             sent = self.server_socket.send(data[totalSent:])
#             totalSent += sent

#     def recv(self):
#         chunks = []
#         bytes_recv = 0
#         while bytes_recv < MSGLEN:
#             chunk = self.server_socket.recv(min(MSGLEN - bytes_recv, 2048))
#             if chunk == b'':
#                 raise RuntimeError("Socket Broke")
#             chunks.append(chunk)
#             bytes_recv += len(chunk)
#         return b''.join(chunks)

import errno
import queue
import select
import socket
import sys

class TCPServer:
    # Mode specifies the IP address the server socket binds to.
    # mode can be one of two special values:
    # localhost -> (127.0.0.1)
    # public ->    (0.0.0.0)
    # otherwise, mode is interpreted as an IP address.
    # port specifies the port that the server socket binds to.
    # read_callback specifies the function that is called when
    # the server reads incoming data.
    # read_callback must be a function that takes three arguments:
    # The first argument must be a string which represents the IP
    # address that data was received from.
    # The second argument must be a queue (a queue.Queue()) which
    # is a tunnel of data to send to the socket that it receieved from.
    # The third argument must be data, which is a string of bytes
    # that the server received.
    def __init__(self, mode, port, read_callback,
                 maximum_connections=5, recv_bytes=2048):
        self.serversocket = ServerSocket(
            mode, port, read_callback, maximum_connections, recv_bytes
        )

    def run(self):
        self.serversocket.run()

    @property
    def ip(self):
        return self.serversocket.ip

    @property
    def port(self):
        return self.serversocket.port

class ServerSocket:

    def __init__(self, mode, port, read_callback, max_connections, recv_bytes):
        # Handle the socket's mode.
        # The socket's mode determines the IP address it binds to.
        # mode can be one of two special values:
        # localhost -> (127.0.0.1)
        # public ->    (0.0.0.0)
        # otherwise, mode is interpreted as an IP address.
        if mode == "localhost":
            self.ip = mode
        elif mode == "public":
            self.ip = socket.gethostname()
        else:
            self.ip = mode
        # Handle the socket's port.
        # This should be a high (four-digit) for development.
        self.port = port
        if type(self.port) != int:
            print("port must be an int", file=sys.stderr)
            raise ValueError
        # Actually create an INET, STREAMing socket.socket.
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("socket created")
        # Make it non-blocking.
        self._socket.setblocking(0)
        print('socket nonblocking')
        # Bind the socket, so it can listen.
        self._socket.bind((self.ip, self.port))
        print('socket bound')
        # Save the callback
        self.callback = read_callback
        # Save the number of maximum connections.
        self._max_connections = max_connections
        if type(self._max_connections) != int:
            print("max_connections must be an int", file=sys.stderr)
            raise ValueError
        # Save the number of bytes to be received each time we read from
        # a socket
        self.recv_bytes = recv_bytes

    def run(self):
        # Start listening
        self._socket.listen(self._max_connections)
        print('listening')
        # Create a list of readers (sockets that will be read from) and a list
        # of writers (sockets that will be written to).
        readers = [self._socket]
        writers = []
        # Create a dictionary of queue.Queues for data to be sent.
        # This dictionary maps sockets to queue.Queue objects
        queues = dict()
        # Create a similar dictionary that stores IP addresses.
        # This dictionary maps sockets to IP addresses
        IPs = dict()
        # Now, the main loop.
        while readers:
            # Block until a socket is ready for processing.
            read, write, err = select.select(readers, writers, readers)
            # Deal with sockets that need to be read from.
            for sock in read:
                if sock is self._socket:
                    # We have a viable connection!
                    client_socket, client_ip = self._socket.accept()
                    # Make it a non-blocking connection.
                    client_socket.setblocking(0)
                    # Add it to our readers.
                    readers.append(client_socket)
                    # Make a queue for it.
                    queues[client_socket] = queue.Queue()
                    # Store its IP address.
                    IPs[client_socket] = client_ip
                else:
                    # Someone sent us something! Let's receive it.
                    try:
                        data = sock.recv(self.recv_bytes)
                    except socket.error as e:
                        if e.errno is errno.ECONNRESET:
                            # Consider 'Connection reset by peer'
                            # the same as reading zero bytes
                            data = None
                        else:
                            raise e
                    if data:
                        # Call the callback
                        self.callback(IPs[sock], queues[sock], data)
                        # Put the client socket in writers so we can write to it
                        # later.
                        if sock not in writers:
                            writers.append(sock)
                    else:
                        # We received zero bytes, so we should close the stream
                        # Stop writing to it.
                        if sock in writers:
                            writers.remove(sock)
                        # Stop reading from it.
                        readers.remove(sock)
                        # Close the connection.
                        sock.close()
                        # Destroy is queue
                        del queues[sock]
            # Deal with sockets that need to be written to.
            for sock in write:
                try:
                    # Get the next chunk of data in the queue, but don't wait.
                    data = queues[sock].get_nowait()
                except queue.Empty:
                    # The queue is empty -> nothing needs to be written.
                    writers.remove(sock)
                else:
                    # The queue wasn't empty; we did, in fact, get something.
                    # So send it.
                    sock.send(data)
            # Deal with erroring sockets.
            for sock in err:
                # Remove the socket from every list.
                readers.remove(sock)
                if sock in writers:
                    writers.remove(sock)
                # Close the connection.
                sock.close()
                # Destroy its queue.
                del queues[sock]