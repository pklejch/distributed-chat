import threading
from queue import Queue

from PyQt5.QtCore import pyqtSignal, QObject

import distributedchat.functions
import distributedchat.settings
from distributedchat.server import Server
from distributedchat.pinger import Pinger
from distributedchat.client import Client


class Node(QObject):
    """
    This class represents main node object. Node object wraps server, client, pinger and other classes for communication.
    """
    signal_message = pyqtSignal(str,  name='msg')
    signal_log_message = pyqtSignal(str,  name='log')
    signal_error = pyqtSignal(int, name='error')
    signal_scan = pyqtSignal(str, name='users')

    def __init__(self, node_id, ip, ip_next, port, port_next, name, window=None):
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
        self.keys = None

    def debug(self, message):
        """
        This function will print debug information about message.

        :param message: Incoming message to be printed.
        """
        if distributedchat.settings.verbose_level > 0:
            distributedchat.functions.debug_print("***************")
            distributedchat.functions.debug_print("Timestamp: " + str(self.clock))
            distributedchat.functions.debug_print("ID: " + str(self.id))
            distributedchat.functions.debug_print("Name: " + self.name)
            distributedchat.functions.debug_print("Status: " + self.state)
            distributedchat.functions.debug_print("Leader: " + str(self.leader))
            distributedchat.functions.debug_print("Leader ID: " + str(self.leader_id))
            distributedchat.functions.debug_print("IP:port: " + self.ip + ":" + self.port)
            distributedchat.functions.debug_print("IP_next:port_next: " + self.ip_next + ":" + self.port_next)
            distributedchat.functions.debug_print("Message: ")
            distributedchat.functions.debug_print(str(message))
            distributedchat.functions.debug_print("***************")

    def increment_clock(self):
        """
        This function implements Lamport clock. It is algorithm for logical clock in distributed system.
        When node is sending message, it will increment his local clock.

        When node receive message it will set his local clock as max(my_clock, received_clock) + 1, see :func:`set_clock`.

        :return: Incremented clock counter.
        """
        mutex = threading.Lock()
        with mutex:
            self.clock += 1
        return self.clock

    def set_clock(self, other_clock):
        """
        This function is a second part of Lamport algorithm to implement logical clock in distributed system.
        For more information see :func:`increment_clock`.

        :param other_clock: Received clock for comparison.
        """
        mutex = threading.Lock()
        with mutex:
            self.clock = max(self.clock, other_clock) + 1

    def start(self):
        """
        This is main function of node wrapper. It start all other threads (server, client, pinger).
        :return:
        """
        self.server.start()
        self.client.start()
        self.pinger.start()
