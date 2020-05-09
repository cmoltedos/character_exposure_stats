import sys
import time
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore

import face_data

class Thread(QtCore.QThread):
    changePixmap = QtCore.pyqtSignal(QtGui.QPixmap)
    new_data = QtCore.pyqtSignal(tuple)

    def __init__(self, stream, known_faces):
        super(Thread, self).__init__()
        self.stream = stream
        self.known_faces = known_faces
        self.stream_data = list()
        self._isRunning = False

    def run(self):
        self._isRunning = True
        result_yield = face_data.yield_process_streaming(
            known_faces=self.known_faces, streaming=self.stream
        )
        for capture_data in result_yield:
            if not self._isRunning:
                break
            rgbImage = face_data.get_rgb_image_from_frame(capture_data[-1])
            convertToQtFormat = QtGui.QImage(rgbImage.data, rgbImage.shape[1],
                                             rgbImage.shape[0],
                                             QtGui.QImage.Format_RGB888)
            convertToQtFormat = QtGui.QPixmap.fromImage(convertToQtFormat)
            self.changePixmap.emit(convertToQtFormat)
            self.new_data.emit(capture_data)
            time.sleep(face_data.ANALYSE_EVERY_N_SECONDS)

    def stop(self):
        self._isRunning = False

    def continue_process(self):
        self._isRunning = True


class Window(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.streaming = None
        self.know_faces = face_data.get_know_faces()
        self.unknown_faces = dict()
        self.stats = dict()
        self.create_layout()

    def create_layout(self):
        layout = QtWidgets.QHBoxLayout()

        self.tv_screen = QtWidgets.QLabel(self)
        layout.addWidget(self.tv_screen)

        second_layout = QtWidgets.QVBoxLayout()

        self.channel = QtWidgets.QComboBox()
        self.channel.addItems(['13', 'TVN', 'Mega', 'CHV'])
        second_layout.addWidget(self.channel)

        group = QtWidgets.QGroupBox("New face:")
        group_layout = QtWidgets.QVBoxLayout()
        self.lineedit = QtWidgets.QLineEdit()
        self.completer = QtWidgets.QCompleter(list(set(map(lambda x: x[1], self.know_faces))))
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.lineedit.setCompleter(self.completer)
        group_layout.addWidget(self.lineedit)
        self.face = QtWidgets.QLabel(self)
        group_layout.addWidget(self.face)
        self.create_button = QtWidgets.QPushButton('Save')
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.save_new_name)
        group_layout.addWidget(self.create_button)
        group.setLayout(group_layout)
        second_layout.addWidget(group)

        action_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton('Start')
        self.start_button.clicked.connect(self.start_capturing_stream)
        action_layout.addWidget(self.start_button)
        self.pause_button = QtWidgets.QPushButton('Pause')
        self.pause_button.clicked.connect(self.pause_capturing_stream)
        action_layout.addWidget(self.pause_button)
        second_layout.addLayout(action_layout)

        layout.addLayout(second_layout)
        self.setLayout(layout)

    def save_new_name(self):
        new_face = self.new_face
        new_face_id = new_face[0]
        new_face_values = new_face[1]
        new_name = self.lineedit.text()
        self.know_faces[new_face_id] = [new_name, new_face_values[1], new_face_values[2]]
        self.lineedit.setText('')
        model = self.completer.model()
        model.setStringList(list(set(map(lambda x: x[0], self.know_faces.values()))))
        del self.new_face
        self.set_unknown_face()

    def set_recomendation(self, recomendation_id):
        recomended_name = self.know_faces[recomendation_id][0]
        self.lineedit.setText(recomended_name)

    def set_unknown_face(self):
        if len(self.unknown_faces):
            self.new_face = self.unknown_faces.popitem()
            self.update_face_image(self.new_face[1][1])
            if len(self.new_face[1]) > 3:
                self.set_recomendation(self.new_face[1][-1])
            self.create_button.setEnabled(True)
        else:
            self.create_button.setEnabled(False)
            self.face.clear()

    def capture_new_data(self, new_data):
        for data in new_data[1]:
            fid = data[0]
            if fid not in self.stats:
                self.stats[fid] = list()
            self.stats[fid].append(new_data[0])
        if len(new_data[2]):
            new_faces = dict(map(lambda x: (x[0], x[1][:4]), new_data[2].items()))
            self.know_faces.update(new_faces)
            self.unknown_faces.update(new_data[2])
            if not self.create_button.isEnabled():
                self.set_unknown_face()
        return None

    def start_capturing_stream(self):
        channel = self.channel.currentText()
        stream = ['result_tvn_57a498c4d7b86d600e5461cb.ts']
        self.streaming = Thread(stream=stream, known_faces=self.know_faces)
        self.streaming.changePixmap.connect(self.add_tv_capture_image)
        self.streaming.new_data.connect(self.capture_new_data)
        self.streaming.start()

    def pause_capturing_stream(self):
        if self.streaming is None:
            return None
        if self.pause_button.text() == 'Pause':
            self.streaming.stop()
        else:
            self.streaming.continue_process()


    def add_tv_capture_image(self, image):
        pixmap = QtGui.QPixmap(image)
        self.tv_screen.setPixmap(pixmap)

    def updated_auto_complete(self, element_list):
        completer = QtWidgets.QCompleter(element_list)
        self.lineedit.setCompleter(completer)

    def update_face_image(self, picture_route):
        pixmap = QtGui.QPixmap(picture_route)
        self.face.setPixmap(pixmap)

    def closeEvent(self, event):
        face_data.set_know_faces(self.know_faces)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    screen = Window()
    screen.show()
    sys.exit(app.exec_())