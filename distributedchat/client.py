import threading
import socket
import time
import pickle
import sys

from cryptography.fernet import Fernet

import distributedchat.settings
import distributedchat.functions



class Client(threading.Thread):
    """
    This class represents client thread, it fetches messages from queue and then process them.
    """
    def __init__(self, node_id, state, body):
        threading.Thread.__init__(self)
        self.name = 'Client'
        self.daemon = True
        self.state = state
        self.body = body
        self.id = node_id
        self.socket = None

    def create_socket(self):
        """
        This function will create IPv4 TCP socket and then connects to the next node.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((distributedchat.settings.node.ip_next, int(distributedchat.settings.node.port_next)))

    def close_socket(self):
        """
        This function close created socket.
        """
        self.socket.close()

    def send_data(self, data):
        """
        This function will send data to socket.

        :param data: Data to be send.
        """
        self.create_socket()
        self.socket.sendall(data)

    def create_message(self, state, body):
        """
        This function will create message. Message is dictionary with following properties: from, to, state,
        body, at_leader, clock and encrypted.

        :param string state: State of message, eg. MSG, PING, SCAN, etc.

        :param string body: Body of message.

        :return: Created message.
        """
        if state == 'PING':
            # message is PING message, dont increment clock
            message = {
                'from': distributedchat.settings.node.ip + ":" + distributedchat.settings.node.port,
                'to': distributedchat.settings.node.ip_next + ":" + distributedchat.settings.node.port_next,
                'state':  state,
                'body': body,
                'at_leader': False,
                'clock': distributedchat.settings.node.clock,
                'encrypted': False
            }
        else:
            # for other messages increment clock
            message = {
                'from': distributedchat.settings.node.ip + ":" + distributedchat.settings.node.port,
                'to': distributedchat.settings.node.ip_next + ":" + distributedchat.settings.node.port_next,
                'state':  state,
                'body': body,
                'at_leader': False,
                'clock': distributedchat.settings.node.increment_clock(),
                'encrypted': False
            }

        return message

    def run(self):
        """
        This is main function of Client thread.

        It fetches messages from queue and then processes them.
        """
        time.sleep(0.5)

        # initial message
        message = self.create_message(self.state, self.body)
        try:
            self.send_data(pickle.dumps(message, -1))
        except (OSError, ConnectionRefusedError):
            # cannot init connect
            distributedchat.functions.error_print("Cant connect to target node, perhaps target node is not running.")
            distributedchat.settings.error = 1
            return

        while True:
            # get message from queue
            message = distributedchat.settings.node.queue.get()

            # do something with message
            end = self.do_task(message)

            # finnish the task
            distributedchat.settings.node.queue.task_done()

            # if task was end message, close socket and exit
            if end:
                self.close_socket()
                return

    def display_message(self, msg, encrypted=False):
        """
        This function will display incoming message from other node.
        In CLI mode it just prints message into console.

        In GUI mode it will emit signal for GUI thread.

        :param string msg: Message to be printed.

        :param bool encrypted: This value says if message is encrypted and if needs to be decrypted before printing.
        """
        # if message arrived encrypted, try to decrypt
        if encrypted:
            try:
                # load your key, if you have it
                cipher_key = distributedchat.settings.node.keys[distributedchat.settings.node.name]

                # decrypt message with key
                cipher = Fernet(cipher_key)
                msg = (cipher.decrypt(msg)).decode('utf-8')
            # if you dont have key, emit error signal to GUI
            except KeyError:
                distributedchat.settings.node.signal_error.emit(1)
                return

        # print message in CLI mode
        if not distributedchat.settings.gui:
            sys.stdout.write('\n')
            sys.stdout.write('\r!!! NEW MESSAGE ARRIVED !!!\n')
            sys.stdout.write("\r"+msg+"\n")
            sys.stdout.write('\r')
        # send signal with message to GUI
        else:
            distributedchat.settings.node.signal_message.emit(msg)

    def initiate_voting(self):
        """
        This function will start the Chang-Roberts algorithm for leader election.
        """
        distributedchat.settings.node.voting = True

        # start Chang-Roberts algorithm
        voting_message = self.create_message('ELECTION', '')
        voting_message['from'] = distributedchat.settings.node.id
        self.send_data(pickle.dumps(voting_message, -1))

    def do_task(self, message):
        """
        This is the main processing function. Based on the information in the incoming message and inner state,
        it decides what to do next.

        :param message: Recieved message.
        """

        # if recieved message was None, exit
        if message is None:
            distributedchat.functions.info_print("EXITING client")
            return True

        # increment clock
        distributedchat.settings.node.set_clock(message['clock'])

        if message['state'] == 'CONNECTING':
            # if someone is trying to connect into ring using me
            if message['from'] != message['to']:
                ip, port = message['from'].split(":")

                # diffrence between connecting into standalone node, or connecting between two nodes in ring
                if distributedchat.settings.node.state == 'ALONE':
                    answer = distributedchat.settings.node.client.create_message('SET', 'ALONE')
                else:
                    answer = distributedchat.settings.node.client.create_message('SET', '')
                    answer['to'] = distributedchat.settings.node.ip_next + ":" + distributedchat.settings.node.port_next
                distributedchat.settings.node.state = 'CONNECTED'

                # update your next node
                distributedchat.settings.node.ip_next = ip
                distributedchat.settings.node.port_next = port

                self.send_data(pickle.dumps(answer, -1))
            # if you connected into ring with yourself
            else:
                if distributedchat.settings.verbose_level > 0:
                    distributedchat.functions.debug_print('Connected to itself')

        elif message['state'] == 'SET':
            if distributedchat.settings.verbose_level > 0:
                distributedchat.functions.debug_print("Setting next node...")

            # diffrence between connecting into standalone node, or connecting between two nodes in ring
            if message['body'] == 'ALONE':
                ip, port = message['from'].split(":")
            else:
                ip, port = message['to'].split(":")

            # update your next node
            distributedchat.settings.node.ip_next = ip
            distributedchat.settings.node.port_next = port

            # send him the answer
            distributedchat.settings.node.state = 'CONNECTED'
            answer = distributedchat.settings.node.client.create_message('DONE', '')
            self.send_data(pickle.dumps(answer, -1))

        elif message['state'] == 'DONE':
            # if new node was sucessfully connected into a ring, then initiate voting for new leader
            self.initiate_voting()

            if distributedchat.settings.verbose_level > 0:
                distributedchat.functions.debug_print("Connection established...")
                distributedchat.functions.debug_print("Initiate voting new leader")

        elif message['state'] == 'MSG':
            # if im the leader
            if distributedchat.settings.node.leader:
                # if its message for me, display it
                if message['to'] == distributedchat.settings.node.id \
                        or message['to'] == distributedchat.settings.node.name:
                    if message['encrypted']:
                        self.display_message(message['body'], True)
                    else:
                        self.display_message(message['body'])
                # if its message for unknown user
                elif message['at_leader']:
                    distributedchat.functions.debug_print("NONEXISTENT USER, destroying message...")
                # if not, mark it and send to next node
                else:
                    message['at_leader'] = True
                    self.send_data(pickle.dumps(message, -1))
            else:
                # if it is message for me and it already passed through leader, display it
                if (message['to'] == distributedchat.settings.node.id
                    or message['to'] == distributedchat.settings.node.name)\
                        and message['at_leader']:
                    if message['encrypted']:
                        self.display_message(message['body'], True)
                    else:
                        self.display_message(message['body'])
                # if its not for me, just pass it to next node
                else:
                    self.send_data(pickle.dumps(message, -1))

        elif message['state'] == 'CLOSE':
            # if recieved closing message
            distributedchat.functions.debug_print("RECEIVED CLOSING MESSAGE")
            next_id = distributedchat.functions.create_id(
                distributedchat.settings.node.ip_next,
                distributedchat.settings.node.port_next
            )

            # message is for me
            if message['to'] == distributedchat.settings.node.id:
                die_msg = self.create_message('DIE', '')
                self.send_data(pickle.dumps(die_msg, -1))

            # message is for next node (the right one)
            elif message['to'] == next_id:
                ip_port = message['body']
                ip, port = ip_port.split(":")
                die_msg = self.create_message('DIE', '')

                try:
                    self.send_data(pickle.dumps(die_msg, -1))
                except (OSError,ConnectionRefusedError):
                    pass

                distributedchat.settings.node.ip_next = ip
                distributedchat.settings.node.port_next = port

                self.initiate_voting()

            # its not for me or next node, pass it to next node
            else:
                self.send_data(pickle.dumps(message, -1))

        # recieved who is dead message, nodes will pass it to the next node, until they find out the dead one
        elif message['state'] == 'WHO_IS_DEAD':
            # try to send it to the next node
            try:
                self.send_data(pickle.dumps(message, -1))
            except (OSError, ConnectionRefusedError):
                # my next node is dead, repair connection
                ip_port = message['body']
                ip, port = ip_port.split(":")
                distributedchat.settings.node.ip_next = ip
                distributedchat.settings.node.port_next = port

                distributedchat.functions.error_print("I found dead node, trying to repair connection.")
                msg = self.create_message('REPAIRED', '')
                self.send_data(pickle.dumps(msg, -1))

        # connection was repaired, initiate voting for new leader
        elif message['state'] == 'REPAIRED':
            if distributedchat.settings.verbose_level > 0:
                distributedchat.functions.debug_print('Connection repaired.')
                distributedchat.functions.debug_print('Initiate voting new leader.')
            self.initiate_voting()

        elif message['state'] == 'SCAN':
            if message['to'] == distributedchat.settings.node.id:
                distributedchat.settings.node.signal_scan.emit(message['body'])
            else:
                users = message['body']
                users += distributedchat.settings.node.name + ";"
                message['body'] = users
                self.send_data(pickle.dumps(message, -1))

        # received election message
        elif message['state'] == 'ELECTION':
            # if id of node who send me election message is bigger then mine, pass message
            if int(message['from'], 16) > int(distributedchat.settings.node.id, 16):
                distributedchat.settings.node.voting = True
                # pass message to next node
                self.send_data(pickle.dumps(message, -1))
            # if id of node who send me election message is lower then mine and im not voting, destroy his message
            # and create new election message with my ID
            if (int(message['from'], 16) < int(distributedchat.settings.node.id, 16)) \
                    and not distributedchat.settings.node.voting:
                voting_message = self.create_message('ELECTION', '')
                voting_message['from'] = distributedchat.settings.node.id
                self.send_data(pickle.dumps(voting_message, -1))
                distributedchat.settings.node.voting = True
            # if i recieved my election message (it means that i have the highest ID)
            # send them elected message
            if int(message['from'], 16) == int(distributedchat.settings.node.id, 16):
                elected_message = self.create_message('ELECTED', '')
                elected_message['from'] = distributedchat.settings.node.id
                self.send_data(pickle.dumps(elected_message, -1))
        # new leader was elected, set it
        elif message['state'] == 'ELECTED':
            distributedchat.settings.node.leader_id = message['from']
            distributedchat.settings.node.voting = False
            distributedchat.settings.node.leader = True

            if distributedchat.settings.verbose_level > 0:
                distributedchat.functions.debug_print("NEW LEADER IS " + distributedchat.settings.node.leader_id)

            # if im not leader, i pass the message to the next node
            if distributedchat.settings.node.id != message['from']:
                distributedchat.settings.node.leader = False
                # pass message to next node
                self.send_data(pickle.dumps(message, -1))

        # i recieved unknown message, print it
        else:
            distributedchat.functions.debug_print("UNKNOWN MESSAGE: ")
            distributedchat.functions.debug_print(str(message))

        distributedchat.settings.node.debug(message)
        return False
