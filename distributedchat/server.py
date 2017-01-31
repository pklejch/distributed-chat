import threading
import socketserver

import distributedchat.functions
import distributedchat.settings
import distributedchat.message


class Server(threading.Thread):
    """
    This class is used as server of the node.
    It listens on specified IP and port and handling incoming messages.
    """
    allow_reuse_address = True

    def __init__(self, node_id, ip, port):
        threading.Thread.__init__(self)
        self.name = 'Server'
        self.id = node_id
        self.ip = ip
        self.port = int(port)
        self.daemon = True
        self._create_socket()

    def _create_socket(self):
        """
        This function will create server and starts listening for incoming packets.
        """
        if distributedchat.settings.verbose_level > 0:
            distributedchat.functions.debug_print("Starting server on: "+self.ip+":"+str(self.port))
        socketserver.ThreadingTCPServer.allow_reuse_address = True

        # start server
        try:
            self.socket = socketserver.ThreadingTCPServer((self.ip, self.port), distributedchat.message.MessageHandler)
        except (OSError, ConnectionRefusedError):
            distributedchat.functions.error_print("Cannot start server, perhaps port is in use.")
            distributedchat.settings.error = 1
        try:
            self.socket.daemon_threads = True
        except AttributeError:
            pass

    def run(self):
        """
        Main function of server thread.
        """
        try:
            self.socket.serve_forever()
        except AttributeError:
            distributedchat.functions.info_print("Server exiting...")
