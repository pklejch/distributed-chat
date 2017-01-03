import threading
import socketserver
import pickle
import socket
import time

node = None

class message_handler(socketserver.BaseRequestHandler):

    def handle(self):
        global node
        self.data = self.request.recv(1024).strip()
        #print("node ID: " + str(self.id))
        print("Data: ")
        message = pickle.loads(self.data)
        print(message)

        if message['state'] == 'CONNECTING':
            if message['from'] != message['to']:
                answer = self.client.create_message('SET','')
                self.request.sendall(pickle.dumps(answer, -1))

                ip, port = message['from'].split(":")
                node.ip_next = ip
                node.port_next = port
                node.client.close_socket()

                node.client = Client(id,node)
                node.state = 'CONNECTED'
            else:
                print('Connected to itself')


        elif message['state'] == 'SET':
            ip, port = message['to'].split(":")
            node.ip_next = ip
            node.port_next = port
            node.client.close_socket()

            node.client = Client(id,node)
            node.state = 'CONNECTED'


        node.debug()


class Node:
    def __init__(self, id, ip, ip_next, port, port_next):

        self.id = 0
        self.state = 'DISCONNECTED'
        self.ip = ip
        self.ip_next = ip_next
        self.port = port
        self.port_next = port_next

        self.server = Server(id, self)
        self.client = Client(id, self)

    def debug(self):
        print("***************")
        print("ID: " + self.id)
        print("Status: " + self.state)
        print("IP:port: " + self.ip + ":" + self.port)
        print("IP_next:port_next: " + self.ip_next + ":" + self.port_next)
        print("***************")

    def start(self):
        self.server.start()
        self.client.start()




class Server(threading.Thread):
    def __init__(self, id, node):
        threading.Thread.__init__(self)
        self.id = id

        print(node.ip)
        self.ip = node.ip
        self.port = int(node.port)

        self._create_socket()

    def _create_socket(self):
        self.socket = socketserver.TCPServer((self.ip, self.port), message_handler)
        self.socket.allow_reuse_address = True

    def run(self):
        self.socket.serve_forever()





class Client(threading.Thread):
    def __init__(self, id, node):
        threading.Thread.__init__(self)
        print(node)
        self.node = node
        self.id = id
        self.create_socket()


    def create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.node.ip_next, int(self.node.port_next)))

    def close_socket(self):
        self.socket.close()

    def send_data(self,data):
        self.socket.sendall(data)

    def create_message(self, state, body):
        message = {
            'from' : self.node.ip + ":" + self.node.port,
            'to' : self.node.ip_next+ ":" +self.node.port_next,
            'state':  state,
            'body': body
        }

        return message

    def run(self):
        time.sleep(1)
        message = self.create_message('CONNECTING','')

        self.send_data(pickle.dumps(message,-1))