import click
import hashlib
import logging
from distributedchat.cnode import Node
from distributedchat.gui import gui_main
from PyQt5 import QtWidgets
import distributedchat.settings
import distributedchat.functions

# for history in input() in CLI mode
try:
    import readline
except ImportError:
    # readline not available
    pass


@click.group()
def interface():
    pass


@interface.command()
def gui():
    # set settings for GUI mode
    distributedchat.settings.verbose_level = 2
    distributedchat.settings.gui = True

    # run initial GUI window and get values
    [app, window, ip, port, ip_next, port_next, leader, name, keys_file] = gui_main()

    # compute node ID
    node_id = hashlib.sha224((ip + ":" + port).encode('ascii')).hexdigest()

    # create node
    distributedchat.settings.node = Node(node_id, ip, ip_next, port, port_next, node_id, window)

    # set node name
    distributedchat.settings.node.name = name

    # initialize leader
    if leader:
        distributedchat.settings.node.state = 'ALONE'
        distributedchat.settings.node.leader = True
        distributedchat.settings.node.leader_id = node_id

    # read configuration file with keys
        distributedchat.settings.node.keys = distributedchat.functions.read_config(keys_file)

    # if no keys file was specified, disable encryption option
    if distributedchat.settings.node.keys is None:
        window.findChild(QtWidgets.QCheckBox, 'chck_encrypt').setEnabled(False)

    # try to start node, otherwise exit
    try:
        distributedchat.settings.node.start()
    except:
        distributedchat.functions.error_print("Error while starting node.")
        exit(1)

    # connect function with onclick event
    btn = window.findChild(QtWidgets.QPushButton, 'button_send')
    btn.clicked.connect(lambda: distributedchat.functions.send_message_from_qui(window))

    # connect signals with functions
    distributedchat.settings.node.signal_message.connect(distributedchat.functions.message_received)
    distributedchat.settings.node.signal_log_message.connect(distributedchat.functions.log_received)
    distributedchat.settings.node.signal_error.connect(distributedchat.functions.missing_key)

    window.show()
    return app.exec()


@interface.command()
@click.argument("ip_port",  callback=distributedchat.functions.validate_ip)
@click.option("--ip_port_next", "-i", help="Ip and port.", callback=distributedchat.functions.validate_ip)
@click.option('--verbose', '-v', count=True, help='Enables verbose output.')
def cli(ip_port, ip_port_next, verbose):
    # set verbose level from command option
    distributedchat.settings.verbose_level = verbose

    # parse command options
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
    distributedchat.settings.rootLogger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.ERROR)
    distributedchat.settings.rootLogger.addHandler(console_handler)

    distributedchat.settings.rootLogger.setLevel(logging.DEBUG)

    # call function to start node in CLI mode
    distributedchat.functions.start_node(node_id, ip, port, ip_next, port_next, leader)


def main():
    interface()

if __name__ == '__main__':
    main()
