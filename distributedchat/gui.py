from PyQt5 import QtWidgets, uic
import os


def get_dir():
    """
    This function returns directory (as a string) from which is run this tool.
    It is used as prefix for file path of configuration files.

    :return: String with absolute path of directory from which is this tool run.
    """
    return str(os.path.abspath(os.path.dirname(__file__)))


def load_keys_file(window):
    """
    This function will start open file dialog and then stores path of the file with keys.
    """
    # get filename from dialog
    result = QtWidgets.QFileDialog.getOpenFileName(window)
    filepath = result[0]

    # save file path if it isnt empty
    if filepath != '':
        window.keys_file = filepath


def gui_main():
    """
    Main GUI function which first starts dialog with settings (local IP and port, remote IP and port, ...)
    and then start main window with chat.
    """
    directory = get_dir()

    app = QtWidgets.QApplication([])

    window = QtWidgets.QMainWindow()

    # create init dialog with settings
    with open(directory + '/main.ui') as f:
        uic.loadUi(f, window)
    dialog = QtWidgets.QDialog(window)

    with open(directory + '/startnode.ui') as f:
        uic.loadUi(f, dialog)

    # connect function with onlick event
    btn = window.findChild(QtWidgets.QPushButton, 'btn_keys')
    btn.clicked.connect(lambda: load_keys_file(window))

    # display dialog window
    result = dialog.exec()

    # get the result of a window
    if result == QtWidgets.QDialog.Rejected:
        # dialog was exited
        exit(0)
    else:
        # get ip and port from dialog
        ip = dialog.findChild(QtWidgets.QLineEdit, 'ip').text()
        port = dialog.findChild(QtWidgets.QSpinBox, 'port').value()

        # set default next ip and port
        ip_next = ip
        port_next = port
        leader = True

        # override next ip and port, if user set it
        if dialog.findChild(QtWidgets.QCheckBox, 'chck_init').isChecked():
            leader = False
            ip_next = dialog.findChild(QtWidgets.QLineEdit, 'ip_next').text()
            port_next = dialog.findChild(QtWidgets.QSpinBox, 'port_next').value()

        # set name of the node
        name = dialog.findChild(QtWidgets.QLineEdit, 'name').text()

        # check if name is viable
        if name == "" or name is None:
            QtWidgets.QMessageBox.critical(window, "Error", "You have to specify name of the node.",
                                           QtWidgets.QMessageBox.Close)
            exit(1)
        if ';' in name:
            QtWidgets.QMessageBox.critical(window, "Error", "Sorry your name can't contain character ';'.",
                                           QtWidgets.QMessageBox.Close)
            exit(1)

    # set the title of the window
    window.setWindowTitle("Distributed chat | Node name: " + name)

    if hasattr(window, 'keys_file'):
        return [app, window, str(ip), str(port), str(ip_next), str(port_next), leader, name, window.keys_file]
    else:
        return [app, window, str(ip), str(port), str(ip_next), str(port_next), leader, name, None]
