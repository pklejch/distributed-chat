How to use
==========
You can run this program in two modes:

- CLI mode
- GUI mode

If you install package using:

.. code::

   python3.5 -m venv env
   . env/bin/activate
   python setup.py install

You can run it by typing it's name in activated virtual enviroment:

.. code::

   distributedchat <mode>

If you just downloaded code from github, you can run this program as python module
(in virtual environment, with downloaded dependencies).

So, first create virtual environment and activate it:

.. code::

   python3.5 -m venv env
   . env/bin/activate

Then install dependencies using pip:

.. code::

   python -m pip install -r requirements.txt

And at last run program as python module:

.. code::

   python -m distributedchat <mode>

CLI mode
--------
You can run this program in CLI mode by command:

.. code::

   distributedchat cli IP:port [OPTIONS]

IP:port is used to specify where (on which interface) will this node listen.

List of available options:

\-v, \-\-verbose
   Enables verbose output. (You can enable verbose output multiple times for more detailed output.)
\-i, \-\-ip_port_next
   IP and port of node, which is already running. This is used, if you want to connect into existing network.
   IP and port is in the following format: IP:port.



GUI mode
--------
You can run this program in GUI mode by command:

.. code::

   distributedchat gui

Then in dialog window you must specify:

- Local IP and port, where node will listen.
- Name of the node. **This must be unique, otherwise you get unexpected behavior.**
- Remote IP and port of node, where you want to connect. (If you want to connect and not to bootstrap the network.)
- File with keys, which has following format:

[keys]

node_name=<32 byte long key encoded in base64>

node_name2=<32 byte long key encoded in base64>

...

Using encryption
~~~~~~~~~~~~~~~~

First you must generate keys and then secretly exchange keys with your partner.
You can generate key using this command:

.. code::

   head -c 32 /dev/urandom | base64

Then store it in yours key configuration file:

[keys]

<my_name>=<my key>

<my_friends_name>=<his_key>


If you at start don't specify key configuration file, you can't use encryption.
This file needs to contain line with your name, otherwise you cannot receive encrypted messages.
If you want to use encryption, check "Encrypt message" checkbox while sending a message.