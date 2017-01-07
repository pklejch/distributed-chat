import os
import sys
#from asyncio.queues import Queue

sys.path.append(str(os.path.abspath(os.path.dirname(__file__))))
import click

import hashlib

import threading
import socketserver
import pickle
import socket
import time
import tty, sys, termios
from queue import Queue

node = None
verbose_level = 0

try:
    import readline
except:
    # readline not available
    pass

def create_id(ip,port):
    return hashlib.sha224((ip+":"+port).encode('ascii')).hexdigest()


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
        node.leader_id = id
    node.start()
    debug_print("Enter name of your node: ")
    node_name = input(">\n")
    node.name = node_name

    getch = GetchUnix()

    first=True
    try:
        while True:
            if first:
                debug_print("To send message press Enter, to quit press ESC")
                first=False

            pressed_key = ord(getch.get_key())

            #pressed_key = 27

            # ESC or Ctrl-C
            if pressed_key == 27 or pressed_key == 3:
                raise KeyboardInterrupt
            # Enter
            elif pressed_key == 13:
                sendMessage(node_name)



    except KeyboardInterrupt:
        debug_print("Pressed ESC or Ctrl+C, exiting....")

        # TODO graceful exit

        print(threading.active_count())


        # close server handling thread
        endMsg = node.client.create_message('CLOSE','')
        endMsg['to'] = node.id
        node.client.send_data(pickle.dumps(endMsg,-1))

        #TODO BETTER

        time.sleep(2)
        # close client thread
        node.queue.put(None)

        # close main server thread
        node.server.socket.shutdown()
        node.server.socket.server_close()

        print(threading.active_count())


        exit(0)

def debug_print(msg='',end=''):
    print(msg,end='')
    print('\n',end='')
    sys.stdout.flush()

def sendMessage(node_name):
    debug_print("Enter name or ID of target node: ")
    node_id = input(">\n")
    debug_print("Message: ")
    msg = input(">\n")

    # TODO for debug
    if msg == 'exit':
        raise KeyboardInterrupt
    if len(msg) > 4050:
        debug_print("Max length of message is 4050 characters.")
        return

    new_msg = node.client.create_message('MSG', node_name + " says: " + msg)

    # replace target
    new_msg['to'] = node_id
    node.client.send_data(pickle.dumps(new_msg, -1))

def main():
    interface()


class message_handler(socketserver.BaseRequestHandler):

    def handle(self):
        global node
        self.data = self.request.recv(4096)
        if len(self.data) == 0:
            return

        message = pickle.loads(self.data)

        if message['state'] == 'DIE':
            if verbose_level > 0:
                debug_print("RECEIVED DIE")
            return
        elif message['state'] == 'PING':
            if verbose_level > 1:
                debug_print("RECEIVED PING MESSAGE from: "+message['from'])
            node.ping_queue.put(message)
        else:
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
        self.ping_queue = Queue()
        self.name=name
        self.leader=False
        self.leader_id=0
        self.voting = False

        self.server = Server(id, self)
        self.client = Client(id, self, 'CONNECTING', '')
        self.pinger = Pinger(self)

    def debug(self, message):
        if verbose_level > 0:
            debug_print("***************")
            debug_print("ID: " + str(self.id))
            debug_print("Name: " + self.name)
            debug_print("Status: " + self.state)
            debug_print("Leader: " + str(self.leader))
            debug_print("Leader ID: " + str(self.leader_id))
            debug_print("IP:port: " + self.ip + ":" + self.port)
            debug_print("IP_next:port_next: " + self.ip_next + ":" + self.port_next)
            debug_print("Message: ")
            debug_print(message)
            debug_print("***************")

    def start(self):
        self.server.start()
        self.client.start()
        self.pinger.start()




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
            debug_print("Starting server on: "+self.ip+":"+str(self.port))
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        self.socket = socketserver.ThreadingTCPServer((self.ip,self.port), message_handler)
        self.socket.daemon_threads = True

    def run(self):
        self.socket.serve_forever()
        debug_print("Server exiting...")





class Client(threading.Thread):
    def __init__(self, id, node, state, body):

        threading.Thread.__init__(self)
        self.name = 'Client'
        self.daemon = True
        self.state = state
        self.body = body
        self.node = node
        self.id = id


    def create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.node.ip_next, int(self.node.port_next)))

    def close_socket(self):
        #self.socket.shutdown(2)
        self.socket.close()

    def send_data(self,data):
        self.create_socket()
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
        time.sleep(0.5)

        #initial message
        message = self.create_message(self.state,self.body)
        self.send_data(pickle.dumps(message,-1))

        while True:
            message = node.queue.get()
            end = self.do_task(message)
            node.queue.task_done()
            if end:
                self.close_socket()
                return

    def display_message(self, msg):
        debug_print()
        debug_print('!!! NEW MESSAGE ARRIVED !!!')
        debug_print(msg)
        debug_print('>', end='')

    def chang_roberts(self):
        pass

    def initiate_voting(self):
        global node
        node.voting = True

        voting_message = self.create_message('ELECTION','')
        voting_message['from'] = node.id
        self.send_data(pickle.dumps(voting_message,-1))

    def do_task(self, message):
        global node
        if message is None:
            debug_print("EXITING client")
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

                node.ip_next = ip
                node.port_next = port



                self.send_data(pickle.dumps(answer, -1))


            else:
                if verbose_level > 0:
                    debug_print('Connected to itself')


        elif message['state'] == 'SET':
            if verbose_level > 0:
                debug_print("Setting next node...")

            # diffrence between connecting into standalone node, or connecting between two nodes in ring
            if message['body'] == 'ALONE':
                ip, port = message['from'].split(":")
            else:
                ip, port = message['to'].split(":")

            # MUTEX TODO
            node.ip_next = ip
            node.port_next = port
            #node.client.close_socket()

            #node.client.create_socket()
            node.state = 'CONNECTED'
            answer = node.client.create_message('DONE', '')
            self.send_data(pickle.dumps(answer, -1))


        elif message['state'] == 'DONE':

            self.initiate_voting()

            if verbose_level > 0:
                debug_print("Connection established...")
                debug_print("Initiate voting new leader")

        elif message['state'] == 'MSG':
            # if im the leader
            if node.leader:
                # if its message for me, display it
                if (message['to'] == node.id or message['to'] == node.name):
                    self.display_message(message['body'])
                # if its message for unknown user
                elif message['at_leader']:
                    debug_print("NONEXISTENT USER, destroying message...")
                # if not, mark it and send to next node
                else:
                    message['at_leader'] = True
                    self.send_data(pickle.dumps(message, -1))
            else:
                # if it is message for me and it already passed through leader, display it
                if (message['to'] == node.id or message['to'] == node.name) and message['at_leader']:
                    self.display_message(message['body'])
                # if its not for me, just pass it to next node
                else:
                    self.send_data(pickle.dumps(message,-1))

        elif message['state'] == 'CLOSE':
            debug_print("GOT CLOSING MESSAGE")
            next_id = create_id(node.ip_next,node.port_next)

            # message is for me
            if message['to'] == node.id:
                die_msg = self.create_message('DIE','')
                self.send_data(pickle.dumps(die_msg,-1))

            # message is for next node (the right one)
            elif message['to'] == next_id:
                get_message = self.create_message('GET_NEXT','')
                get_message['from'] = node.id
                self.send_data(pickle.dumps(get_message,-1))
            # its not for me or next node, pass it to next node
            else:
                self.send_data(pickle.dumps(message, -1))


        elif message['state'] == 'GET_NEXT':
            msg = self.create_message('PREPARE_TO_DIE',node.ip_next+":"+node.port_next)
            msg['to'] = message['from']
            self.send_data(pickle.dumps(msg, -1))

        elif message['state'] == 'PREPARE_TO_DIE':
            if message['to'] == node.id:
                ip_port = message['body']
                ip, port = ip_port.split(":")


                die_msg = self.create_message('DIE','')
                self.send_data(pickle.dumps(die_msg,-1))

                node.ip_next = ip
                node.port_next = port

                self.initiate_voting()
            else:
                self.send_data(pickle.dumps(message, -1))

        elif message['state'] == 'WHO_IS_DEAD':
            try:
                self.send_data(pickle.dumps(message,-1))
            except:
                # my next node is dead, repair connection
                ip_port = message['body']
                ip, port = ip_port.split(":")
                node.ip_next = ip
                node.port_next = port

                debug_print("TRYING TO REPAIR")
                msg = self.create_message('REPAIRED','')
                self.send_data(pickle.dumps(msg,-1))

        elif message['state'] == 'REPAIRED':
            if verbose_level > 0:
                debug_print('Connection repaired.')
                debug_print('Initiate voting new leader.')
            self.initiate_voting()

        elif message['state'] == 'ELECTION':
            if int(message['from'],16) > int(node.id,16):
                node.voting = True
                # pass message to next node
                self.send_data(pickle.dumps(message,-1))
            if (int(message['from'],16) < int(node.id,16)) and not node.voting:
                voting_message = self.create_message('ELECTION','')
                voting_message['from'] = node.id
                self.send_data(pickle.dumps(voting_message,-1))

                node.voting = True

            if int(message['from'],16) == int(node.id,16):
                elected_message = self.create_message('ELECTED','')
                elected_message['from'] = node.id
                self.send_data(pickle.dumps(elected_message,-1))

        elif message['state'] == 'ELECTED':
            node.leader_id = message['from']
            node.voting = False
            node.leader = True

            if verbose_level > 0:
                debug_print("NEW LEADER IS "+node.leader_id)
            if node.id != message['from']:
                node.leader = False
                # pass message to next
                self.send_data(pickle.dumps(message,-1))

        else:
            debug_print("UNKNOWN MESSAGE: ")
            debug_print(str(self.data))

        node.debug(message)
        return False

class Pinger(threading.Thread):
    def __init__(self,node):
        threading.Thread.__init__(self)
        self.interval = 2
        self.errors = 0
        self.attempts = 2
        self.daemon = True

    def check_ping(self, ping):
        pass

    def run(self):
        global node

        time.sleep(1)

        while True:
            p = node.client.create_message('PING','')
            try:
                node.client.send_data(pickle.dumps(p,-1))
            except:
                pass

            time.sleep(self.interval)

            # number of tries exceeded limit
            # start sending who is dead message
            if self.errors > self.attempts:
                debug_print("NODE BEHIND ME IS DEAD")
                dead_message = node.client.create_message('WHO_IS_DEAD',node.ip+":"+node.port)
                try:
                    node.client.send_data(pickle.dumps(dead_message,-1))
                #next node is dead, im alone
                except:
                    node.queue.put(dead_message)
                self.errors = 0
            # there is something in the ping queue, node behind us is alive
            elif node.ping_queue.qsize() > 0:
                self.errors = 0
                node.ping_queue.get()
                node.ping_queue.task_done()
            # there is nothing in the ping queue, increment error counter
            else:
                self.errors+=1



class GetchUnix:

    def get_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

if __name__=='__main__':
    main()