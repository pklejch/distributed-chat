import click
import hashlib
import logging
import threading
import socketserver
import pickle
import socket
import time
import tty
import sys
import termios

from queue import Queue

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from PyQt5 import QtWidgets

node = None
verbose_level = 0
rootLogger = logging.getLogger()
gui = False
error = 0


# for history in input()
try:
    import readline
except ImportError:
    # readline not available
    pass


def create_id(ip, port):
    return hashlib.sha224((ip + ":" + port).encode('ascii')).hexdigest()


def validate_ip(ctx, param, value):

    if value is None:
        return

    try:
        _, _ = value.split(":")
        return value
    except ValueError:
        raise click.BadParameter("IP and port must be in the following format: <ip/hostname>:<port>")

def send_message_from_qui(window):
    node_id = window.findChild(QtWidgets.QLineEdit,'node_id').text()
    msg = window.findChild(QtWidgets.QPlainTextEdit, 'message').toPlainText()

    new_msg = node.client.create_message('MSG', node.name + " says: " + msg)

    # replace target
    new_msg['to'] = node_id
    node.client.send_data(pickle.dumps(new_msg, -1))


class QPlainTextEditLogger(logging.StreamHandler):
    def __init__(self, window):
        super().__init__()
        self.window = window

    @pyqtSlot(str)
    def emit(self, record):
        msg = self.format(record)
        recv_messages = self.window.findChild(QtWidgets.QPlainTextEdit, 'logs')
        recv_messages.appendPlainText(msg)


@pyqtSlot(str, name='msg')
def message_received(msg):
    recv_messages = node.window.findChild(QtWidgets.QPlainTextEdit, 'recv_messages')
    recv_messages.appendPlainText(msg)

@pyqtSlot(str, name='log')
def log_received(msg):
    recv_messages = node.window.findChild(QtWidgets.QPlainTextEdit, 'logs')
    recv_messages.appendPlainText(msg)

@click.group()
def interface():
    pass


@interface.command()
def gui():
    global verbose_level
    verbose_level = 2
    global gui
    gui = True
    from gui import gui_main
    from PyQt5 import QtWidgets
    [app, window, ip, port, ip_next, port_next, leader, name] = gui_main()
    node_id = hashlib.sha224((ip + ":" + port).encode('ascii')).hexdigest()


    # create node
    global node
    node = Node(node_id, ip, ip_next, port, port_next, node_id, window)

    node.name = name
    # initialize leader
    if leader:
        node.state = 'ALONE'
        node.leader = True
        node.leader_id = node_id

    try:
        node.start()
    except:
        error_print("Error while starting node.")
        exit(1)

    btn = window.findChild(QtWidgets.QPushButton,'button_send')
    btn.clicked.connect(lambda: send_message_from_qui(window))

    node.signal_message.connect(message_received)
    node.signal_log_message.connect(log_received)

    window.show()
    return app.exec()


@interface.command()
@click.argument("ip_port",  callback=validate_ip)
@click.option("--ip_port_next", "-i", help="Ip and port.", callback=validate_ip)
@click.option('--verbose', '-v', count="True", help='Enables verbose output.')
def cli(ip_port, ip_port_next, verbose):
    global verbose_level
    global rootLogger
    verbose_level = verbose

    ip, port = ip_port.split(":")
    leader = False
    if ip_port_next is None:
        leader = True
        ip_port_next = ip_port

    ip_next, port_next = ip_port_next.split(":")

    # calculate ID
    node_id = hashlib.sha224(ip_port.encode('ascii')).hexdigest()

    # init logger
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    file_handler = logging.FileHandler("{0}/{1}.log".format('.', node_id))
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    rootLogger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.ERROR)
    rootLogger.addHandler(console_handler)

    rootLogger.setLevel(logging.DEBUG)

    start_node(node_id, ip, port, ip_next, port_next, leader)


def start_node(node_id, ip, port, ip_next, port_next, leader):
    # create node
    global node
    node = Node(node_id, ip, ip_next, port, port_next, node_id)

    # initialize leader
    if leader:
        node.state = 'ALONE'
        node.leader = True
        node.leader_id = node_id

    try:
        node.start()
    except:
        error_print("Error while starting node.")
        exit(1)

    print("Enter name of your node: ")
    node_name = input("> ")
    node.name = node_name

    # get char
    getch = GetchUnix()

    first = True
    try:
        while True:

            if error:
                error_print("Something went wrong.")
                exit(1)

            if first:
                print("To send message press Enter, to quit press ESC")
                first = False

            pressed_key = ord(getch.get_key())

            # ESC = 27, Ctrl-C = 3

            # ESC or Ctrl-C
            if pressed_key == 27 or pressed_key == 3:
                raise KeyboardInterrupt
            # Enter
            elif pressed_key == 13:
                send_message(node_name)

    except KeyboardInterrupt:
        print("Pressed ESC or Ctrl+C, exiting....")

        # send closing message
        end_msg = node.client.create_message('CLOSE', node.ip_next + ":" + node.port_next)
        end_msg['to'] = node.id
        node.client.send_data(pickle.dumps(end_msg, -1))

        # TODO BETTER

        time.sleep(2)
        # close client thread
        node.queue.put(None)

        # close main server thread
        node.server.socket.shutdown()
        node.server.socket.server_close()

        exit(0)


def info_print(msg=''):
    if not gui:
        global rootLogger
        rootLogger.info(msg)
    else:
        global node
        if node is not None:
            node.signal_log_message.emit(msg)


def debug_print(msg=''):
    if not gui:
        global rootLogger
        rootLogger.debug(msg)
    else:
        global node
        if node is not None:
            node.signal_log_message.emit(msg)


def error_print(msg=''):
    if not gui:
        global rootLogger
        rootLogger.error(msg)
    else:
        global node
        if node is not None:
            node.signal_log_message.emit(msg)


def send_message(node_name):
    print("Enter name or ID of target node: ")
    node_id = input("> ")
    print("Message: ")
    msg = input("> ")

    if len(msg) > 4050:
        print("Max length of message is 4050 characters.")
        return

    new_msg = node.client.create_message('MSG', node_name + " says: " + msg)

    # replace target
    new_msg['to'] = node_id
    node.client.send_data(pickle.dumps(new_msg, -1))


def main():
    interface()


class MessageHandler(socketserver.BaseRequestHandler):

    def handle(self):
        global node
        data = self.request.recv(4096)
        if len(data) == 0:
            return

        message = pickle.loads(data)

        # its a DIE message, return
        if message['state'] == 'DIE':
            if verbose_level > 0:
                info_print("RECEIVED DIE")
            return
        # its a PING message, put it in the ping_queue
        elif message['state'] == 'PING':
            if verbose_level > 1:
                debug_print("RECEIVED PING MESSAGE from: " + message['from'])
            node.ping_queue.put(message)
        # some other message (MSG, CLOSE, ELECTION, ...) put in the message queue
        else:
            node.queue.put(message)


class Node(QObject):
    signal_message = pyqtSignal(str,  name='msg')
    signal_log_message = pyqtSignal(str,  name='log')
    def __init__(self, node_id, ip, ip_next, port, port_next, name, window = None):
        QObject.__init__(self)
        self.id = node_id
        self.state = 'DISCONNECTED'
        self.ip = ip
        self.ip_next = ip_next
        self.port = port
        self.port_next = port_next
        self.queue = Queue()
        self.ping_queue = Queue()
        self.name = name
        self.leader = False
        self.leader_id = 0
        self.voting = False
        self.clock = 0
        self.server = Server(id, ip, port)
        self.client = Client(id, 'CONNECTING', '')
        self.pinger = Pinger()
        self.window = window

    def debug(self, message):
        if verbose_level > 0:
            debug_print("***************")
            debug_print("Timestamp: " + str(self.clock))
            debug_print("ID: " + str(self.id))
            debug_print("Name: " + self.name)
            debug_print("Status: " + self.state)
            debug_print("Leader: " + str(self.leader))
            debug_print("Leader ID: " + str(self.leader_id))
            debug_print("IP:port: " + self.ip + ":" + self.port)
            debug_print("IP_next:port_next: " + self.ip_next + ":" + self.port_next)
            debug_print("Message: ")
            debug_print(str(message))
            debug_print("***************")

    def increment_clock(self):
        mutex = threading.Lock()
        with mutex:
            self.clock += 1
        return self.clock

    def set_clock(self, other_clock):
        mutex = threading.Lock()
        with mutex:
            self.clock = max(self.clock, other_clock) + 1

    def start(self):
        self.server.start()
        self.client.start()
        self.pinger.start()


class Server(threading.Thread):
    allow_reuse_address = True

    def __init__(self, node_id, ip, port):
        threading.Thread.__init__(self)
        self.name = 'Server'
        self.id = node_id
        self.ip = ip
        self.port = int(port)
        self.daemon = True
        self._create_socket()

    def _create_socket(self):
        if verbose_level > 0:
            debug_print("Starting server on: "+self.ip+":"+str(self.port))
        socketserver.ThreadingTCPServer.allow_reuse_address = True

        try:
            self.socket = socketserver.ThreadingTCPServer((self.ip, self.port), MessageHandler)
        except OSError:
            error_print("Cannot start server, perhaps port is in use.")
            global error
            error = 1
        try:
            self.socket.daemon_threads = True
        except AttributeError:
            pass

    def run(self):
        try:
            self.socket.serve_forever()
        except AttributeError:
            pass
        info_print("Server exiting...")


class Client(threading.Thread):
    def __init__(self, node_id, state, body):

        threading.Thread.__init__(self)
        self.name = 'Client'
        self.daemon = True
        self.state = state
        self.body = body
        self.id = node_id
        self.socket = None

    def create_socket(self):
        global node
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((node.ip_next, int(node.port_next)))

    def close_socket(self):
        self.socket.close()

    def send_data(self, data):
        self.create_socket()
        self.socket.sendall(data)

    def create_message(self, state, body):
        global node
        if state == 'PING':
            # dont increment clock
            message = {
                'from': node.ip + ":" + node.port,
                'to': node.ip_next + ":" + node.port_next,
                'state':  state,
                'body': body,
                'at_leader': False,
                'clock': node.clock
            }
        else:
            message = {
                'from': node.ip + ":" + node.port,
                'to': node.ip_next + ":" + node.port_next,
                'state':  state,
                'body': body,
                'at_leader': False,
                'clock': node.increment_clock()
            }

        return message

    def run(self):
        global node
        time.sleep(0.5)

        # initial message
        message = self.create_message(self.state, self.body)
        try:
            self.send_data(pickle.dumps(message, -1))
        except:
            # cannot init connect
            global error
            error_print("Cant connect to target node, perhaps target node is not running.")
            error = 1
            return

        while True:
            message = node.queue.get()
            end = self.do_task(message)
            node.queue.task_done()
            if end:
                self.close_socket()
                return

    def display_message(self, msg):
        if not gui:
            sys.stdout.write('\n')
            sys.stdout.write('\r!!! NEW MESSAGE ARRIVED !!!\n')
            sys.stdout.write("\r"+msg+"\n")
            sys.stdout.write('\r')
        else:
            global node
            node.signal_message.emit(msg)

    def initiate_voting(self):
        global node
        node.voting = True

        voting_message = self.create_message('ELECTION', '')
        voting_message['from'] = node.id
        self.send_data(pickle.dumps(voting_message, -1))

    def do_task(self, message):
        global node
        if message is None:
            info_print("EXITING client")
            return True

        node.set_clock(message['clock'])

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
                if message['to'] == node.id or message['to'] == node.name:
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
                    self.send_data(pickle.dumps(message, -1))

        elif message['state'] == 'CLOSE':
            debug_print("RECEIVED CLOSING MESSAGE")
            next_id = create_id(node.ip_next, node.port_next)

            # message is for me
            if message['to'] == node.id:
                die_msg = self.create_message('DIE', '')
                self.send_data(pickle.dumps(die_msg, -1))

            # message is for next node (the right one)
            elif message['to'] == next_id:
                ip_port = message['body']
                ip, port = ip_port.split(":")

                die_msg = self.create_message('DIE', '')
                self.send_data(pickle.dumps(die_msg, -1))

                node.ip_next = ip
                node.port_next = port

                self.initiate_voting()
            # its not for me or next node, pass it to next node
            else:
                self.send_data(pickle.dumps(message, -1))

        elif message['state'] == 'WHO_IS_DEAD':
            try:
                self.send_data(pickle.dumps(message, -1))
            except:
                # my next node is dead, repair connection
                ip_port = message['body']
                ip, port = ip_port.split(":")
                node.ip_next = ip
                node.port_next = port

                error_print("I found dead node, trying to repair connection.")
                msg = self.create_message('REPAIRED', '')
                self.send_data(pickle.dumps(msg, -1))

        elif message['state'] == 'REPAIRED':
            if verbose_level > 0:
                debug_print('Connection repaired.')
                debug_print('Initiate voting new leader.')
            self.initiate_voting()

        elif message['state'] == 'ELECTION':
            if int(message['from'], 16) > int(node.id, 16):
                node.voting = True
                # pass message to next node
                self.send_data(pickle.dumps(message, -1))
            if (int(message['from'], 16) < int(node.id, 16)) and not node.voting:
                voting_message = self.create_message('ELECTION', '')
                voting_message['from'] = node.id
                self.send_data(pickle.dumps(voting_message, -1))

                node.voting = True

            if int(message['from'], 16) == int(node.id, 16):
                elected_message = self.create_message('ELECTED', '')
                elected_message['from'] = node.id
                self.send_data(pickle.dumps(elected_message, -1))

        elif message['state'] == 'ELECTED':
            node.leader_id = message['from']
            node.voting = False
            node.leader = True

            if verbose_level > 0:
                debug_print("NEW LEADER IS " + node.leader_id)
            if node.id != message['from']:
                node.leader = False
                # pass message to next node
                self.send_data(pickle.dumps(message, -1))

        else:
            debug_print("UNKNOWN MESSAGE: ")
            debug_print(str(message))

        node.debug(message)
        return False


class Pinger(threading.Thread):
    def __init__(self):
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
            p = node.client.create_message('PING', '')
            try:
                node.client.send_data(pickle.dumps(p, -1))
            except:
                pass

            time.sleep(self.interval)

            # number of tries exceeded limit
            # start sending who is dead message
            if self.errors > self.attempts:
                error_print("NODE BEHIND ME IS DEAD")
                dead_message = node.client.create_message('WHO_IS_DEAD', node.ip + ":" + node.port)
                try:
                    node.client.send_data(pickle.dumps(dead_message, -1))
                # next node is dead, im alone
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
                self.errors += 1


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

if __name__ == '__main__':
    main()