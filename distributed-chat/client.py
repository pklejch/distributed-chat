import socket
import threading
import time


class Client(threading.Thread):
    def __init__(self, id, ip, port):
        threading.Thread.__init__(self)
        self.id = id
        self.next_ip = ip
        self.next_port = port

    def run(self):
        time.sleep(10)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.next_ip, self.next_port))
            s.sendall(b'Hello, world')
            data = s.recv(1024)
        print('Received', repr(data))