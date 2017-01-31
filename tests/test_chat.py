import os
import hashlib

import click
import pytest

import distributedchat.functions
import distributedchat.settings


def get_dir():
    return str(os.path.abspath(os.path.dirname(__file__)))


directory = get_dir()


# test existent file and user
def test_read_config():
    assert isinstance(distributedchat.functions.read_config(directory + "/../distributedchat/keys.cfg")['petr'], str)


# test existent file, but nonexistent user
def test_read_config2():
    with pytest.raises(KeyError):
        distributedchat.functions.read_config(directory + "/../distributedchat/keys.cfg")['nonexistent']


# test nonexistent file
def test_read_config3():
    assert distributedchat.functions.read_config("nonexistentfile") is None


# test if returned message is OK
@pytest.mark.parametrize(['state', 'body'],
                         [('PING', ''),
                         ('MSG', 'hello'),
                         ('DIE', '')]
                         )
def test_create_message(state, body):
    c = distributedchat.client.Client('id', '', '')
    distributedchat.settings.node = distributedchat.cnode.Node('node_id', 'ip', 'ip_next', '9999', '9998', 'name')
    msg = c.create_message(state, body)
    assert msg['state'] == state and msg['body'] == body


# test if do_task is successfully closed, when no work is to be done
def test_do_task():
    c = distributedchat.client.Client('id', '', '')
    assert c.do_task(None) is True


# test compare clock
@pytest.mark.parametrize(['num', 'clock'], [(5, 10), (15, 10), (20, 15)])
def test_set_clock(num, clock):
    node = distributedchat.cnode.Node('node_id', 'ip', 'ip_next', '9999', '9998', 'name')
    for _ in range(0, num):
        node.increment_clock()
    node.set_clock(clock)

    assert node.clock == max(num, clock) + 1


# test increment clock
@pytest.mark.parametrize('num', (5, 10, 15))
def test_increment_clock(num):
    node = distributedchat.cnode.Node('node_id', 'ip', 'ip_next', '9999', '9998', 'name')
    for _ in range(0, num):
        node.increment_clock()
    assert node.clock == num


# test creating id
@pytest.mark.parametrize(['ip', 'port'], [('localhost', '9999'), ('127.0.0.1', '9922'), ('192.168.0.1', '1234')])
def test_create_id(ip, port):
    node_id = distributedchat.functions.create_id(ip, port)
    assert node_id == hashlib.sha224((ip + ":" + port).encode('ascii')).hexdigest()


# test ok and port
@pytest.mark.parametrize(['ip', 'port'], [('localhost', '9999'), ('127.0.0.1', '9922'), ('192.168.0.1', '1234')])
def test_validate_ip(ip, port):
    ip_port = distributedchat.functions.validate_ip('', '', ip + ":" + port)
    assert ip_port == ip + ":" + port


# test wrong ip or port
@pytest.mark.parametrize('ip_port', ('300.600.213.5555:9999', '127.0.0.1:dog', '192.168.0.1-1234'))
def test_validate_ip(ip_port):
    with pytest.raises(click.ClickException):
        distributedchat.functions.validate_ip('', '', ip_port)
