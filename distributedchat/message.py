import socketserver
import pickle
import distributedchat.settings
import distributedchat.functions


class MessageHandler(socketserver.BaseRequestHandler):
    """
    This class is used for handling incoming messages.
    """
    def handle(self):
        """
        This function will process incoming messages.
        It unpickles them and stores them in to the right queue.
        """
        data = self.request.recv(4096)
        if len(data) == 0:
            return

        # unpickle data
        message = pickle.loads(data)

        # its a DIE message, return
        if message['state'] == 'DIE':
            if distributedchat.settings.verbose_level > 0:
                distributedchat.functions.info_print("RECEIVED DIE")
            return
        # its a PING message, put it in the ping_queue
        elif message['state'] == 'PING':
            if distributedchat.settings.verbose_level > 1:
                distributedchat.functions.debug_print("RECEIVED PING MESSAGE from: " + message['from'])
                distributedchat.settings.node.ping_queue.put(message)
        # some other message (MSG, CLOSE, ELECTION, ...) put in the message queue
        else:
            distributedchat.settings.node.queue.put(message)
