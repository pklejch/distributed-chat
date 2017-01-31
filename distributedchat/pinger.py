import threading
import time
import pickle

import distributedchat.functions


class Pinger(threading.Thread):
    """
    This class is used for checking, whether node behind me is alive.
    It is also used for sending PING messages to the next node.
    So the next node knows I'm alive.
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.interval = 2
        self.errors = 0
        self.attempts = 2
        self.daemon = True

    def run(self):
        """
        This is the main function of Pinger thread.
        It receives PING messages from the queue and also sends other PING messages to the next node.
        """
        time.sleep(1)

        while True:
            # create PING message
            p = distributedchat.settings.node.client.create_message('PING', '')

            # try to send PING message
            try:
                distributedchat.settings.node.client.send_data(pickle.dumps(p, -1))
            except (OSError, ConnectionRefusedError):
                pass

            # sleep
            time.sleep(self.interval)

            # number of tries exceeded limit
            # start sending who is dead message
            if self.errors > self.attempts:
                distributedchat.functions.error_print("NODE BEHIND ME IS DEAD")
                dead_message = distributedchat.settings.node.client.create_message('WHO_IS_DEAD', distributedchat.settings.node.ip + ":" + distributedchat.settings.node.port)
                try:
                    distributedchat.settings.node.client.send_data(pickle.dumps(dead_message, -1))
                # next node is dead, im alone
                except (OSError, ConnectionRefusedError):
                    distributedchat.settings.node.queue.put(dead_message)
                self.errors = 0
            # there is something in the ping queue, node behind us is alive
            elif distributedchat.settings.node.ping_queue.qsize() > 0:
                self.errors = 0
                distributedchat.settings.node.ping_queue.get()
                distributedchat.settings.node.ping_queue.task_done()
            # there is nothing in the ping queue, increment error counter
            else:
                self.errors += 1
