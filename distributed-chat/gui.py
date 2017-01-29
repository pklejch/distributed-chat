from PyQt5 import QtWidgets, uic


def load_keys_file(window):
    result = QtWidgets.QFileDialog.getOpenFileName(window)
    filepath = result[0]


    # save file path
    if filepath != '':
        window.keys_file = filepath



def gui_main():
    app = QtWidgets.QApplication([])

    window = QtWidgets.QMainWindow()

    with open('main.ui') as f:
        uic.loadUi(f, window)

    # Vytvoříme nový dialog.
    # V dokumentaci mají dialogy jako argument `this`;
    # jde o "nadřazené" okno
    dialog = QtWidgets.QDialog(window)

    # Načteme layout z Qt Designeru
    with open('startnode.ui') as f:
        uic.loadUi(f, dialog)



    btn = window.findChild(QtWidgets.QPushButton,'btn_keys')
    btn.clicked.connect(lambda: load_keys_file(window))

    # Zobrazíme dialog.
    # Funkce exec zajistí modalitu (tj.  tzn. nejde ovládat zbytek aplikace,
    # dokud je dialog zobrazen), a vrátí se až potom, co uživatel dialog zavře.
    result = dialog.exec()



    # Výsledná hodnota odpovídá tlačítku/způsobu, kterým uživatel dialog zavřel.
    if result == QtWidgets.QDialog.Rejected:
        # Dialog uživatel zavřel nebo klikl na Cancel
        QtWidgets.QMessageBox.critical(window, "Error", "You have to specify IP and port.", QtWidgets.QMessageBox.Close)
        exit(1)
    else:
        # get ip and port from dialog
        ip = dialog.findChild(QtWidgets.QLineEdit,'ip').text()
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

        name = dialog.findChild(QtWidgets.QLineEdit, 'name').text()


    if hasattr(window, 'keys_file'):
        return [app, window, str(ip), str(port), str(ip_next), str(port_next), leader, name, window.keys_file]
    else:
        return [app, window, str(ip), str(port), str(ip_next), str(port_next), leader, name, None]
