import time
import pickle
import configparser
import click
import hashlib

from cryptography.fernet import Fernet
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import Qt

from distributedchat.getchar import GetchUnix
import distributedchat.settings
import distributedchat.cnode


def start_node(node_id, ip, port, ip_next, port_next, leader):
    """
    This function is used in CLI mode to prepare and boostrap node.

    :param node_id: ID of the node.

    :param ip: Local IP where node will be started.

    :param port: Local port where node will be started.

    :param ip_next: Remote IP of the next node in ring.

    :param port_next: Remote port of the next node.

    :param leader: Bool value, if this node is leader.
    """

    # create node
    distributedchat.settings.node = distributedchat.cnode.Node(node_id, ip, ip_next, port, port_next, node_id)

    # initialize leader
    if leader:
        distributedchat.settings.node.state = 'ALONE'
        distributedchat.settings.node.leader = True
        distributedchat.settings.node.leader_id = node_id

    # try to start node, otherwise exit
    try:
        distributedchat.settings.node.start()
    except (OSError, ConnectionRefusedError):
        error_print("Error while starting node.")
        exit(1)

    # prompt for name of the node
    print("Enter name of your node: ")
    node_name = input("> ")
    distributedchat.settings.node.name = node_name

    # get char
    getch = GetchUnix()

    first = True

    # get char in while loop and check for ESC and Enter
    try:
        while True:

            if distributedchat.settings.error:
                error_print("Something went wrong.")
                exit(1)

            if first:
                print("To send message press Enter, to quit press ESC")
                first = False

            pressed_key = ord(getch.get_key())

            # ESC = 27, Ctrl-C = 3
            # Enter = 13

            # ESC or Ctrl-C
            if pressed_key == 27 or pressed_key == 3:
                raise KeyboardInterrupt
            # Enter
            elif pressed_key == 13:
                send_message(node_name)

    # main CLI loop was interrupted
    except KeyboardInterrupt:
        print("Pressed ESC or Ctrl+C, exiting....")
        disconnect_from_network()
        exit(0)


def disconnect_from_network():
    """
    This function will notify next nodes, that this node is leaving the network. This message is then propagated,
    until it reaches node behind me, node behind me will then update his information about his next node.

    Then this function will gracefully terminate threads.
    """
    # send closing message
    end_msg = distributedchat.settings.node.client.create_message(
        'CLOSE',
        distributedchat.settings.node.ip_next + ":" + distributedchat.settings.node.port_next
    )
    end_msg['to'] = distributedchat.settings.node.id
    distributedchat.settings.node.client.send_data(pickle.dumps(end_msg, -1))

    time.sleep(0.3)

    # close client thread
    distributedchat.settings.node.queue.put(None)

    # close main server thread
    distributedchat.settings.node.server.socket.shutdown()
    distributedchat.settings.node.server.socket.server_close()


def info_print(msg=''):
    """
    This function prints info messages into log.

    :param msg: Message to be printed.
    """
    if not distributedchat.settings.gui:
        distributedchat.settings.rootLogger.info(msg)
    else:
        if distributedchat.settings.node is not None:
            distributedchat.settings.node.signal_log_message.emit(msg)


def debug_print(msg=''):
    """
    This function prints debug messages into log.

    :param msg: Message to be printed.
    """
    if not distributedchat.settings.gui:
        distributedchat.settings.rootLogger.debug(msg)
    else:
        if distributedchat.settings.node is not None:
            distributedchat.settings.node.signal_log_message.emit(msg)


def error_print(msg=''):
    """
    This function prints error messages into log.

    :param msg: Message to be printed.
    """
    if not distributedchat.settings.gui:
        distributedchat.settings.rootLogger.error(msg)
    else:
        if distributedchat.settings.node is not None:
            distributedchat.settings.node.signal_log_message.emit(msg)


def send_message(node_name):
    """
    This function sends message to other node from CLI mode.

    :param node_name: Name of recipient node.
    """
    print("Enter name or ID of target node: ")
    node_id = input("> ")
    print("Message: ")
    msg = input("> ")

    if len(msg) > 4050:
        print("Max length of message is 4050 characters.")
        return

    # create message
    new_msg = distributedchat.settings.node.client.create_message('MSG', node_name + " says: " + msg)

    # replace target
    new_msg['to'] = node_id
    distributedchat.settings.node.client.send_data(pickle.dumps(new_msg, -1))


def create_id(ip, port):
    """
    This function will calculates ID of the node from local IP and port.

    :param ip: Local IP of the node.

    :param port: Local port of the node.

    :return: SHA hash of string IP:node
    """
    return hashlib.sha224((ip + ":" + port).encode('ascii')).hexdigest()


def validate_ip(ctx, param, value):
    """
    This function is used for validating supplied parameters from CLI.

    :param value: String to be validated.

    :return: Return string if OK, otherwise raise exception.
    """
    if value is None:
        return
    try:
        _, _ = value.split(":")
        return value
    except ValueError:
        raise click.BadParameter("IP and port must be in the following format: <ip/hostname>:<port>")


def send_message_from_gui(window):
    """
    This function will send message from GUI mode. It is GUI counterpart of function :func:`send_message`.

    It takes message from QPlainTextEdit widget and sends it to the node specified in the QLineEdit widget.

    It will also encrypt message if checkbox "Encrypt message" is checked.

    :param window: Parent window widget.
    """
    node_id = window.findChild(QtWidgets.QLineEdit, 'node_id').text()
    msg = window.findChild(QtWidgets.QPlainTextEdit, 'message').toPlainText()
    window.findChild(QtWidgets.QPlainTextEdit, 'message').clear()
    encrypt = window.findChild(QtWidgets.QCheckBox, 'chck_encrypt').isChecked()

    # if message will be encrypted load key of target node and encrypt the message
    if encrypt:
        try:
            cipher_key = distributedchat.settings.node.keys[node_id]
        except KeyError:
            QtWidgets.QMessageBox.critical(window, "Missing key.",
                                           "You don't have key for target recipient. "
                                           "Add key in keys.cfg configuration file.",
                                           QtWidgets.QMessageBox.Close)
            return

        # encrypt message
        cipher = Fernet(cipher_key)
        message = distributedchat.settings.node.name + " says: " + msg
        encrypted_message = cipher.encrypt(message.encode('utf-8'))
        new_msg = distributedchat.settings.node.client.create_message('MSG', encrypted_message)
        new_msg['encrypted'] = True
    else:
        new_msg = distributedchat.settings.node.client.create_message(
            'MSG',
            distributedchat.settings.node.name + " says: " + msg
        )

    # replace target
    new_msg['to'] = node_id

    # send message
    distributedchat.settings.node.client.send_data(pickle.dumps(new_msg, -1))


def scan_network_for_users():
    """
    This function starts to scan network for connected users.
    """
    scan_message = distributedchat.settings.node.client.create_message('SCAN', '')
    scan_message['to'] = distributedchat.settings.node.id

    # send message
    distributedchat.settings.node.client.send_data(pickle.dumps(scan_message, -1))


def select_user():
    """
    This function will set recipient of message after clicking on the user in QListWidget.
    """
    users = distributedchat.settings.node.window.findChild(QtWidgets.QListWidget, 'users').selectedItems()
    selected_user = None

    for user in users:
        selected_user = user.data(Qt.DisplayRole)

    distributedchat.settings.node.window.findChild(QtWidgets.QLineEdit, 'node_id').setText(selected_user)


def read_config(config):
    """
    This function will read configuration file.

    :param config: Path with configuration file containing keys.

    :return: Config section with keys (dictionary), where key is name of the node and value is his key. None will be returned if config file cannot be read.
    """
    keys_config = configparser.ConfigParser()
    if config is not None:
        try:
            keys_config.read(config)
            return keys_config['keys']
        except KeyError:
            return None
    else:
        return None


@pyqtSlot(str, name='users')
def print_users(users):
    """
    This function listens for signal, which contains all connected users.
    Then this function will fill QListWidget with received users.

    :param users: Recieved string with users, separated with ';'.
    """
    list = distributedchat.settings.node.window.findChild(QtWidgets.QListWidget, 'users')
    list.clear()
    users = sorted(users.split(';'))

    for user in users:
        if user != '':
            list.addItem(QtWidgets.QListWidgetItem(user))


@pyqtSlot(str, name='msg')
def message_received(msg):
    """
    This function listens for signal, which contains received message.
    Then this function will print received message into received messages section.

    :param msg: Message to be printed.
    """
    recv_messages = distributedchat.settings.node.window.findChild(QtWidgets.QPlainTextEdit, 'recv_messages')
    recv_messages.appendPlainText(msg)


@pyqtSlot(str, name='log')
def log_received(msg):
    """
    This function listens for signal, which contains debug message.

    :param msg: Log message to be printed.
    """
    recv_messages = distributedchat.settings.node.window.findChild(QtWidgets.QPlainTextEdit, 'logs')
    recv_messages.appendPlainText(msg)


@pyqtSlot(int, name='error')
def missing_key(err_code):
    """
    This function listens for signal, which contains error message, that message was received but this node doesn't
    have needed key for decryption.
    """
    QtWidgets.QMessageBox.critical(distributedchat.settings.node.window, "Missing key.",
                                   "Someone send you a message encrypted with key you don't have. "
                                   "Add your key in keys.cfg configuration file.",
                                   QtWidgets.QMessageBox.Close)
