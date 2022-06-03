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

    def closeEvent(self, event):
        self.kill_pinging_thread()
        event.accept()


    def termination_message(self, given_text):
        exit_message = QtWidgets.QMessageBox(
            icon=3, text=given_text)
        exit_message.setWindowTitle("Сообщение об ошибке")
        exit_message.setStandardButtons(QtWidgets.QMessageBox.Ok)
        exit_message.exec_()
        self.close()

    def start_socket(self):
        try:
            host_addr = (HOST, PORT)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(host_addr)
            sock.setblocking(True)
            self.message = clientmessage.Message(sock, 4096)
            obtained_dict = self.message.get_field_values()
        

            Clientapp_Ui.fill_values_combo_box(
                self.select_room, obtained_dict.get('room_values'))
            Clientapp_Ui.fill_values_combo_box(
                self.select_doctor, obtained_dict.get('doctor_values'))
            Clientapp_Ui.fill_values_combo_box(
                self.select_study, obtained_dict.get('study_values'))

            self.switch_to_connected_state()
        except ConnectionResetError:
            self.termination_message(
                "Сервер перестал отвечать на запросы. По закрытии этого окна программа закроется")
        except ConnectionRefusedError:
            self.termination_message(
                "Сервер в данный момент не работает. По закрытии этого окна программа закроется")

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

    def ping_thread_function(self, imprint):
        while True:
            
            for _ in range(120):
                if self.kill_flag:
                    break
                sleep(1)
            if self.kill_flag:
                break
            self.change_room_status(imprint[-1], True)

    def start_pinging_thread(self):
        if self.ping_thread is not None:
            self.kill_pinging_thread()
        self.ping_thread = threading.Thread(
            target=lambda: self.ping_thread_function(self.data_imprint))
        self.ping_thread.start()

    def kill_pinging_thread(self):
        if self.ping_thread is not None:
            self.kill_flag = True
            self.ping_thread.join()
            self.ping_thread = None
            self.kill_flag = False

    def display_animated_label(self, text, color):
        self.status_label.setText(text)

        effect = QtWidgets.QGraphicsColorizeEffect(self.status_label)
        self.status_label.setGraphicsEffect(effect)

        self.label_animation = QtCore.QPropertyAnimation(effect, b"color")

        self.label_animation.setStartValue(QtGui.QColor(color))
        self.label_animation.setEndValue(QtGui.QColor(0, 0, 0))

        self.label_animation.setDuration(1000)

        self.status_label.show()
        self.label_animation.start()

    

    def change_room_status(self, to_which, is_ping=False):
        try:
            if not is_ping:
                room = self.select_room.currentIndex()
                doctor = self.select_doctor.currentIndex()
                study = self.select_study.currentIndex()
            else:
                room, doctor, study = self.data_imprint[:-1]
            try:   
                old_imprint = self.data_imprint.copy()
            except NameError:
                old_imprint = []
            self.data_imprint = [room, doctor, study, to_which]

            result, code_value = self.message.change_room_status(self.data_imprint)

            if code_value == 0:
                color = QtCore.Qt.green
                
                self.start_pinging_thread()
                self.setWindowTitle(self.select_room.itemText(self.data_imprint[0]))
            else:
                color = QtCore.Qt.red
                if old_imprint != []:
                    self.data_imprint = old_imprint
                    self.start_pinging_thread()
                else:
                    self.data_imprint = []
            if not is_ping:
                self.display_animated_label(result, color)
        except ConnectionResetError:
            self.termination_message(
                "Сервер перестал отвечать на запросы. По закрытии этого окна программа закроется")
        except ConnectionRefusedError:
            self.termination_message(
                "Сервер в данный момент не работает. По закрытии этого окна программа закроется")

    def switch_shrink_window(self):
        #diff = 300
        if self.is_shrunk:
            self.bottom_frame.show()
            self.setMaximumHeight(500)
            self.setMinimumHeight(500)
            self.centralwidget.resize(self.centralwidget.width(), 500)
            self.resize(self.width(), 500)
            self.is_shrunk = False
            self.button_shrink.setText("Уменьшить")
        else:
            self.bottom_frame.hide()
            self.setMinimumHeight(200)
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
            self.setWindowFlags(self.windowFlags() & ~
                                QtCore.Qt.WindowStaysOnTopHint)
            self.button_pin.setText("Закрепить")
            self.show()
            self.is_pinned = False

    def __init__(self):
        super().__init__()

        self.is_shrunk = False
        self.is_pinned = False

        self.ping_thread = None
        self.kill_flag = False

        self.data_imprint = []

        self.setupUi(self)
        self.button_connect.clicked.connect(self.start_socket)
        self.button_noentry.clicked.connect(lambda: self.change_room_status(0))
        self.button_occupied.clicked.connect(
            lambda: self.change_room_status(1))
        self.button_empty.clicked.connect(lambda: self.change_room_status(2))
        self.button_pin.clicked.connect(self.switch_pinned_state)
        self.button_shrink.clicked.connect(self.switch_shrink_window)


def main():
    app = QtWidgets.QApplication([])

    window = Clientapp_Ui()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
