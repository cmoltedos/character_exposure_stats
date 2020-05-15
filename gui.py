import sys
import time
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore

import face_data

class Thread(QtCore.QThread):
    changePixmap = QtCore.pyqtSignal(str)#QtGui.QPixmap)
    new_data = QtCore.pyqtSignal(tuple)

    def __init__(self, stream, known_faces, start_button):
        super(Thread, self).__init__()
        self.stream = stream
        self.known_faces = known_faces
        self._isRunning = False
        self._isPause = False
        self.start_button = start_button

    def run(self):
        self._isRunning = True
        result_yield = face_data.yield_process_streaming(
            known_faces=self.known_faces, streaming=self.stream
        )
        while self._isRunning:
            if self._isPause:
                time.sleep(1)
                continue
            try:
                capture_data = next(result_yield)
            except StopIteration:
                break
            # rgbImage = face_data.get_rgb_image_from_frame(capture_data[-1])
            # convertToQtFormat = QtGui.QImage(rgbImage.data, rgbImage.shape[1],
            #                                  rgbImage.shape[0],
            #                                  QtGui.QImage.Format_RGB888)
            # convertToQtFormat = QtGui.QPixmap.fromImage(convertToQtFormat)
            convertToQtFormat = face_data.create_image_from_frame('test.jpg', capture_data[-1])
            self.changePixmap.emit(convertToQtFormat)
            self.new_data.emit(capture_data)
            #time.sleep(face_data.ANALYSE_EVERY_N_SECONDS)
        self._isRunning = False
        self.start_button.setText('Start')

    def stop(self):
        self.start_button.setText('Start')
        self._isRunning = False

    def pause_process(self):
        if self.start_button.text() == 'Pause':
            self.start_button.setText('Continue')
        else:
            self.start_button.setText('Pause')
        self._isPause = not self._isPause


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
        self.lineedit.returnPressed.connect(self.save_new_name)
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
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop_capturing_stream)
        action_layout.addWidget(self.stop_button)
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

    def set_recomendation(self, face_encoding):
        values_list = [value for value in self.know_faces.values() if value[0] != 'Unknown']
        if not values_list:
            return None

        known_face_names, know_face_location, known_face_encodings = zip(*values_list)
        best_match_index, match_value = face_data.get_best_match(known_face_encodings, face_encoding)
        if best_match_index:
            recomended_name = known_face_names[best_match_index]
            self.lineedit.setText(recomended_name)

    def set_unknown_face(self):
        if len(self.unknown_faces):
            self.new_face = self.unknown_faces.popitem()
            self.update_face_image(self.new_face[1][1])
            self.set_recomendation(self.new_face[1][-1])
            self.create_button.setEnabled(True)
        else:
            self.create_button.setEnabled(False)
            self.face.clear()

    def capture_new_data(self, new_data):
        face_data.update_stats(self.stats, new_data)
        if len(new_data[2]):
            self.know_faces.update(new_data[2])
            self.unknown_faces.update(new_data[2])
            if not self.create_button.isEnabled():
                self.set_unknown_face()
        return None

    def start_capturing_stream(self):
        channel = self.channel.currentText()
        if self.start_button.text() != 'Start':
            self.streaming.pause_process()
        else:
            self.start_button.setText('Pause')
            stream = ['result_13_b859e668b266815bf6771bf001ee2ddd.ts']
            self.streaming = Thread(stream=stream, known_faces=self.know_faces,
                                    start_button=self.start_button)
            self.streaming.changePixmap.connect(self.add_tv_capture_image)
            self.streaming.new_data.connect(self.capture_new_data)
            self.streaming.start()

    def stop_capturing_stream(self):
        if self.streaming is None:
            return None
        self.streaming.stop()


    def add_tv_capture_image(self, image):
        pixmap = QtGui.QPixmap(image)
        self.tv_screen.setPixmap(pixmap)

    def updated_auto_complete(self, element_list):
        completer = QtWidgets.QCompleter(element_list)
        self.lineedit.setCompleter(completer)

    def update_face_image(self, picture_route):
        pixmap = QtGui.QPixmap(picture_route)
        self.face.setPixmap(pixmap.scaled(100, 100, QtCore.Qt.KeepAspectRatio))

    def closeEvent(self, event):
        face_data.set_know_faces(self.know_faces)
        face_data.save_stats(self.stats)
        face_data.create_csv_race_bar_graphic_data(self.stats, self.know_faces)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    screen = Window()
    screen.show()
    sys.exit(app.exec_())