import pytest
import os
import distributedchat.functions

def get_dir():
    return str(os.path.abspath(os.path.dirname(__file__)))

directory = get_dir()

# test existent file and user
def test_read_config():
    assert isinstance(distributedchat.functions.read_config(directory + "/../distributedchat/keys.cfg")['petr'],str)


# test existent file, but nonexistent user
def test_read_config2():
    with pytest.raises(KeyError):
        distributedchat.functions.read_config(directory + "/../distributedchat/keys.cfg")['nonexistent']


# test nonexistent file
def test_read_config3():
    assert distributedchat.functions.read_config("nonexistentfile") is None