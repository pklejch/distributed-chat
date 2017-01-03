import os
import sys
from asyncio.queues import Queue

sys.path.append(str(os.path.abspath(os.path.dirname(__file__))))
import click

import hashlib

import threading
import socketserver
import pickle
import socket
import time

from queue import Queue

node = None
verbose_level = 0

try:
    import readline
except:
    # readline not available
    pass



@click.group()
def interface():
    pass


@interface.command()
def gui():
    raise Exception


@interface.command()
@click.argument("ip_port")
@click.option("--ip_port_next", "-i", help="Ip and port.")
@click.option('--verbose', '-v', count="True", help='Enables verbose output.')
def cli(ip_port, ip_port_next, verbose):
    ip, port = ip_port.split(":")
    global verbose_level
    verbose_level=verbose


    leader=False
    if ip_port_next is None:
        leader = True
        ip_port_next = ip_port

    ip_next, port_next = ip_port_next.split(":")



    id = hashlib.sha224(ip_port.encode('ascii')).hexdigest()

    global node
    node = Node(id,ip,ip_next,port,port_next, id)

    # initialize leader
    if leader:
        node.state = 'ALONE'
        node.leader = True
    node.start()
    print("Enter name of your node: ")
    node_name = input(">")
    node.name = node_name

    try:
        while True:
            print("Enter name or ID of target node: ")
            node_id = input(">")
            print("Message: ")
            msg = input(">")

            #TODO for debug
            if msg == 'exit':
                raise KeyboardInterrupt
            if len(msg) > 4050:
                print("Max length of message is 4050 characters.")
                continue


            new_msg = node.client.create_message('MSG', node_name + " says: " + msg)

            # replace target
            new_msg['to']=node_id
            node.client.send_data(pickle.dumps(new_msg,-1))

    except KeyboardInterrupt:
        print("Pressed Ctrl+C, exiting....")

        # TODO graceful exit

        node.queue.put(None)
        node.server.socket.shutdown()
        node.server.socket.server_close()

        print(threading.active_count())

        exit(0)





def main():
    interface()


class message_handler(socketserver.BaseRequestHandler):

    def handle(self):
        while True:
            global node
            self.data = self.request.recv(4096)
            if len(self.data) == 0:
                continue
            #self.request.sendall(self.data)
            #continue
            #print("node ID: " + str(self.id))

            message = pickle.loads(self.data)

            #print(message)
            node.queue.put(message)


class Node:
    def __init__(self, id, ip, ip_next, port, port_next, name):

        self.id = id
        self.state = 'DISCONNECTED'
        self.ip = ip
        self.ip_next = ip_next
        self.port = port
        self.port_next = port_next
        self.queue = Queue()
        self.name=name
        self.leader=False
        self.leader_id=None

        self.server = Server(id, self)
        self.client = Client(id, self, 'CONNECTING', '')

    def debug(self, message):
        if verbose_level > 0:
            print("***************")
            print("ID: " + str(self.id))
            print("Name: " + self.name)
            print("Status: " + self.state)
            print("IP:port: " + self.ip + ":" + self.port)
            print("IP_next:port_next: " + self.ip_next + ":" + self.port_next)
            print("Message: ")
            print(message)
            print("***************")

    def start(self):
        self.server.start()
        self.client.start()




class Server(threading.Thread):
    allow_reuse_address = True
    def __init__(self, id, node):

        threading.Thread.__init__(self)
        self.name = 'Server'
        self.id = id
        self.ip = node.ip
        self.port = int(node.port)
        self.daemon = True
        self._create_socket()

    def _create_socket(self):
        if verbose_level > 0:
            print("Starting server on: "+self.ip+":"+str(self.port))
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        self.socket = socketserver.ThreadingTCPServer((self.ip,self.port), message_handler)

    def run(self):
        self.socket.serve_forever()
        print("Server exiting...")





class Client(threading.Thread):
    def __init__(self, id, node, state, body):

        threading.Thread.__init__(self)
        self.name = 'Client'
        self.daemon = True
        self.state = state
        self.body = body
        self.node = node
        self.id = id
        self.create_socket()


    def create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.node.ip_next, int(self.node.port_next)))
        if verbose_level > 0:
            print("CLIENT: Conected to: " + self.node.ip_next + ":" + self.node.port_next)

    def close_socket(self):
        self.socket.close()

    def send_data(self,data):
        self.socket.sendall(data)


    def create_message(self, state, body):
        message = {
            'from' : self.node.ip + ":" + self.node.port,
            'to' : self.node.ip_next+ ":" +self.node.port_next,
            'state':  state,
            'body': body,
            'at_leader' : False
        }

        return message

    def run(self):
        global node
        time.sleep(1)

        #initial message
        message = self.create_message(self.state,self.body)
        self.send_data(pickle.dumps(message,-1))

        while True:
            message = node.queue.get()
            end = self.do_task(message)
            node.queue.task_done()
            if end:
                self.close_socket()
                print("Size of queue: "+str(node.queue.qsize()))
                return


    def do_task(self, message):
        global node
        if message is None:
            print("EXITING client")
            return True

        if message['state'] == 'CONNECTING':
            if message['from'] != message['to']:

                ip, port = message['from'].split(":")

                # diffrence between connecting into standalone node, or connecting between two nodes in ring
                if node.state == 'ALONE':
                    answer = node.client.create_message('SET', 'ALONE')
                else:
                    answer = node.client.create_message('SET', '')
                    answer['to'] = node.ip_next + ":" + node.port_next
                node.state = 'CONNECTED'

                # MUTEX TODO
                node.ip_next = ip
                node.port_next = port
                node.client.close_socket()

                node.client.create_socket()


                self.send_data(pickle.dumps(answer, -1))
                #print("Sending answer...")
                #print(answer)

            else:
                if verbose_level > 0:
                    print('Connected to itself')


        elif message['state'] == 'SET':
            if verbose_level > 0:
                print("Setting next node...")

            # diffrence between connecting into standalone node, or connecting between two nodes in ring
            if message['body'] == 'ALONE':
                ip, port = message['from'].split(":")
            else:
                ip, port = message['to'].split(":")

            # MUTEX TODO
            node.ip_next = ip
            node.port_next = port
            node.client.close_socket()

            node.client.create_socket()
            node.state = 'CONNECTED'
            answer = node.client.create_message('DONE', '')
            self.send_data(pickle.dumps(answer, -1))

        elif message['state'] == 'PING':
            self.request.sendall(b'PONG')


        elif message['state'] == 'DONE':
            if verbose_level > 0:
                print("Connection established...")

        elif message['state'] == 'MSG':
            # if im the leader
            if node.leader:
                # if its message for me, display it
                if (message['to'] == self.node.id or message['to'] == self.node.name):
                    print(" !!! NEW MESSAGE ARRIVED !!!!")
                    print(message['body'])
                # if its message for unknown user
                elif message['at_leader']:
                    print("NONEXISTENT USER, destroying message...")
                # if not, mark it and send to next node
                else:
                    message['at_leader'] = True
                    self.send_data(pickle.dumps(message, -1))
            else:
                # if it is message for me and it already passed through leader, display it
                if (message['to'] == self.node.id or message['to'] == self.node.name) and message['at_leader']:
                    print(" !!! NEW MESSAGE ARRIVED !!!!")
                    print(message['body'])
                # if its not for me, just pass it to next node
                else:
                    self.send_data(pickle.dumps(message,-1))
        else:
            print("UNKNOWN MESSAGE: ")
            print(str(self.data))

        #self.request.sendall(b'PING')
        node.debug(message)
        return False

if __name__=='__main__':
    main()