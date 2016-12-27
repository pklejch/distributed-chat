import socket
import threading


class Server(threading.Thread):
    def __init__(self, id, ip, port):
        threading.Thread.__init__(self)
        self.id = id
        self.ip = ip
        self.port = port
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.ip, self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    print('Connected by', addr)
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        conn.sendall(data)