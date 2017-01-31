Installation guide
==================

Download
--------
From GitHub
...........

You can download this tool either from GitHub repository (https://github.com/pklejch/distributed-chat) as zip.

Or clone it to you computer using

.. code::

   git clone https://github.com/pklejch/distributed-chat

From PYPi
.........
You can download this tool from PYPi (https://pypi.python.org/pypi/distributedchat) in tar.gz format.

Alternatively you can use pip tool:

.. code::

  python -m pip install distributedchat

Installation
------------
Installation doesn't download and install PyQt5 dependency due to compatibility issue with some distributions. See :ref:`pyqt-label` chapter
for more information.

Run following command in the downloaded directory and install it system-wide:

.. code::

   python3.5 setup.py install

Or you can create virtual environment using:

.. code::

   python3.5 -m venv env

Start virtual environment:

.. code::

   . env/bin/activate

And then install it into virtual environment:

.. code::

   python setup.py install


.. _pyqt-label:

PyQt5
-----
This program needs PyQt5 module, but on some distributions you can't install it through pip,
so command

.. code::

   python setup.py install

will fail.

On Ubuntu you can install this module system-wide using Ubuntu's packaging system.

.. code::

   sudo apt-get install python3-pyqt5

And then create virtual environment with system-wide packages and activated it using:

.. code::

   python3.5 -m venv --system-site-packages env
   . env/bin/activate


But on some distribution you can just download and install PyQt5 in virtual enviroment using pip:

.. code::

   python -m pip install PyQt5