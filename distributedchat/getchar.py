import termios
import tty
import sys


class GetchUnix:
    """
    This class is used for fetching pressed key from terminal.
    """
    def get_key(self):
        """
        This function returns pressed key in terminal.

        :return: Pressed key.
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
