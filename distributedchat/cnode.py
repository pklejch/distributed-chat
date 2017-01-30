from PyQt5.QtCore import pyqtSignal, QObject
import threading
from queue import Queue
from distributedchat.functions import debug_print
import distributedchat.settings
from distributedchat.server import Server
from distributedchat.pinger import Pinger
from distributedchat.client import Client


class Node(QObject):
    signal_message = pyqtSignal(str,  name='msg')
    signal_log_message = pyqtSignal(str,  name='log')
    signal_error = pyqtSignal(int, name='error')

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
        if distributedchat.settings.verbose_level > 0:
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
