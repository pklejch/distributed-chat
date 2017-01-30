from distributedchat.getchar import GetchUnix
import distributedchat.settings
import time
import pickle
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot
import configparser
import distributedchat.cnode
import click
import hashlib
from cryptography.fernet import Fernet


def start_node(node_id, ip, port, ip_next, port_next, leader):
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
    except:
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

            # ESC or Ctrl-C
            if pressed_key == 27 or pressed_key == 3:
                raise KeyboardInterrupt
            # Enter
            elif pressed_key == 13:
                send_message(node_name)

    # main CLI loop was interrupted
    except KeyboardInterrupt:
        print("Pressed ESC or Ctrl+C, exiting....")

        # send closing message
        end_msg = distributedchat.settings.node.client.create_message(
            'CLOSE',
            distributedchat.settings.node.ip_next + ":" + distributedchat.settings.node.port_next
        )
        end_msg['to'] = distributedchat.settings.node.id
        distributedchat.settings.node.client.send_data(pickle.dumps(end_msg, -1))

        time.sleep(2)
        # close client thread
        distributedchat.settings.node.queue.put(None)

        # close main server thread
        distributedchat.settings.node.server.socket.shutdown()
        distributedchat.settings.node.server.socket.server_close()

        exit(0)


def info_print(msg=''):
    if not distributedchat.settings.gui:
        distributedchat.settings.rootLogger.info(msg)
    else:
        if distributedchat.settings.node is not None:
            distributedchat.settings.node.signal_log_message.emit(msg)


def debug_print(msg=''):
    if not distributedchat.settings.gui:
        distributedchat.settings.rootLogger.debug(msg)
    else:
        if distributedchat.settings.node is not None:
            distributedchat.settings.node.signal_log_message.emit(msg)


def error_print(msg=''):
    if not distributedchat.settings.gui:
        distributedchat.settings.rootLogger.error(msg)
    else:
        if distributedchat.settings.node is not None:
            distributedchat.settings.node.signal_log_message.emit(msg)


def send_message(node_name):
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


def read_config(config):
    keys_config = configparser.ConfigParser()
    if config is not None:
        try:
            keys_config.read(config)
            return keys_config['keys']
        except KeyError:
            return None
    else:
        return None


@pyqtSlot(str, name='msg')
def message_received(msg):
    recv_messages = distributedchat.settings.node.window.findChild(QtWidgets.QPlainTextEdit, 'recv_messages')
    recv_messages.appendPlainText(msg)


@pyqtSlot(str, name='log')
def log_received(msg):
    recv_messages = distributedchat.settings.node.window.findChild(QtWidgets.QPlainTextEdit, 'logs')

    recv_messages.appendPlainText(msg)


@pyqtSlot(int, name='error')
def missing_key(err_code):
        QtWidgets.QMessageBox.critical(distributedchat.settings.node.window, "Missing key.",
                                       "Someone send you a message encrypted with key you don't have. "
                                       "Add your key in keys.cfg configuration file.",
                                       QtWidgets.QMessageBox.Close)