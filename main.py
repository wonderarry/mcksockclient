from PyQt5 import QtWidgets, QtCore, QtGui
import design
import socket
import clientmessage
from time import sleep
import threading
import configparser


conf = configparser.ConfigParser()
conf.read('config.ini')

HOST = conf.get('connection', 'host')
PORT = int(conf.get('connection', 'port'))






class Clientapp_Ui(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def start_socket(self):
        host_addr = (HOST, PORT)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(host_addr)
        sock.setblocking(True)
        self.message = clientmessage.Message(sock, 4096)
        obtained_dict = self.message.get_field_values()

        Clientapp_Ui.fill_values_combo_box(self.select_room, obtained_dict.get('room_values'))
        Clientapp_Ui.fill_values_combo_box(self.select_doctor, obtained_dict.get('doctor_values'))
        Clientapp_Ui.fill_values_combo_box(self.select_study, obtained_dict.get('study_values'))

        self.switch_to_connected_state()

    @staticmethod
    def fill_values_combo_box(object, data):
        for item in data:
            object.addItem(item)

    def switch_to_connected_state(self):
        self.button_empty.setEnabled(True)
        self.button_occupied.setEnabled(True)
        self.button_noentry.setEnabled(True)

        self.label_room.setEnabled(True)
        self.select_room.setEnabled(True)

        self.label_doctor.setEnabled(True)
        self.select_doctor.setEnabled(True)

        self.label_study.setEnabled(True)
        self.select_study.setEnabled(True)

        self.button_connect.setEnabled(False)
        self.button_connect.hide()


    def change_room_status(self, to_which):

        
        room = self.select_room.currentIndex()
        doctor = self.select_doctor.currentIndex()
        study = self.select_study.currentIndex()

        result = self.message.change_room_status([room, doctor, study, to_which])
        self.status_label.setText(result)
        self.status_label.show() 

    def switch_shrink_window(self):
        #diff = 300
        if self.is_shrunk:
            self.bottom_frame.show()
            self.setMaximumHeight(500)
            self.centralwidget.resize(self.centralwidget.width(), 500)
            self.resize(self.width(), 500)
            self.is_shrunk = False
            self.button_shrink.setText("Уменьшить")
        else:
            self.bottom_frame.hide()
            self.setMaximumHeight(200)
            self.centralwidget.resize(self.centralwidget.width(), 200)
            self.resize(self.width(), 200)
            self.is_shrunk = True
            self.button_shrink.setText("Увеличить")

    def switch_pinned_state(self):
        if not self.is_pinned:
            self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            self.button_pin.setText("Открепить")
            self.show()
            self.is_pinned = True
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.button_pin.setText("Закрепить")
            self.show()
            self.is_pinned = False

    def __init__(self):
        super().__init__()

        self.is_shrunk = False
        self.is_pinned = False
        self.setupUi(self)
        self.button_connect.clicked.connect(self.start_socket)
        self.button_noentry.clicked.connect(lambda : self.change_room_status(0))
        self.button_occupied.clicked.connect(lambda : self.change_room_status(1))
        self.button_empty.clicked.connect(lambda : self.change_room_status(2))
        self.button_pin.clicked.connect(self.switch_pinned_state)
        self.button_shrink.clicked.connect(self.switch_shrink_window)     








def main():
    app = QtWidgets.QApplication([])

    window = Clientapp_Ui()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()