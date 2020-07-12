import sys
import time
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore

import face_data

class Thread(QtCore.QThread):
    changePixmap = QtCore.pyqtSignal(str)#QtGui.QPixmap)
    new_data = QtCore.pyqtSignal(list)

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
            self.new_data.emit(capture_data[0])
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

    def is_pause(self):
        return self._isPause


class Window(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.streaming = None
        self.know_persons = face_data.get_know_faces()
        self.unknown_faces = list()
        self.stats = dict()
        self.create_layout()

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout()

        file_layout = QtWidgets.QHBoxLayout()
        self.video = QtWidgets.QLineEdit()
        self.video.setEnabled(False)
        self.video.setGeometry(QtCore.QRect(10, 10, 191, 20))
        self.video.setObjectName("FileName")
        self.video.setFixedWidth(400)
        file_layout.addWidget(self.video)
        toolButtonOpenDialog = QtWidgets.QToolButton(self)
        toolButtonOpenDialog.setGeometry(QtCore.QRect(210, 10, 25, 19))
        toolButtonOpenDialog.setObjectName("FileSelector")
        toolButtonOpenDialog.setText("...")
        toolButtonOpenDialog.clicked.connect(self.set_video)
        file_layout.addWidget(toolButtonOpenDialog)
        main_layout.addLayout(file_layout)

        layout = QtWidgets.QHBoxLayout()

        self.tv_screen = QtWidgets.QLabel(self)
        layout.addWidget(self.tv_screen)

        second_layout = QtWidgets.QVBoxLayout()

        group = QtWidgets.QGroupBox("New face:")
        group_layout = QtWidgets.QVBoxLayout()
        self.lineedit = QtWidgets.QLineEdit()
        self.completer = QtWidgets.QCompleter(list(set(self.know_persons)))
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.lineedit.setCompleter(self.completer)
        #self.lineedit.returnPressed.connect(self.save_new_name)
        group_layout.addWidget(self.lineedit)
        self.face = QtWidgets.QLabel(self)
        group_layout.addWidget(self.face)
        self.recommendation_percent = QtWidgets.QLabel(self)
        group_layout.addWidget(self.recommendation_percent)
        self.create_button = QtWidgets.QPushButton('Save')
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.save_new_name)
        self.lineedit.returnPressed.connect(self.create_button.click)
        group_layout.addWidget(self.create_button)
        group.setLayout(group_layout)
        second_layout.addWidget(group)

        action_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton('Start')
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_capturing_stream)
        action_layout.addWidget(self.start_button)
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_capturing_stream)
        action_layout.addWidget(self.stop_button)
        second_layout.addLayout(action_layout)

        layout.addLayout(second_layout)

        main_layout.addLayout(layout)

        self.setLayout(main_layout)

    def set_video(self):
        self.video.setText(str(QtWidgets.QFileDialog.getOpenFileName(self, 'Open File')[0]))
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(True)

    def save_new_name(self):
        new_name = self.lineedit.text()
        if new_name not in self.know_persons:
            new_person = face_data.Person(name=new_name)
            self.know_persons[new_name] = new_person
        self.know_persons[new_name].add_face(self.new_face)
        self.lineedit.setText('')
        model = self.completer.model()
        model.setStringList(list(set(self.know_persons)))
        self.set_unknown_face()

    def set_recomendation(self):
        if self.new_face.recommendation:
            percent = round(100 - self.new_face.recommendation[0]*100, 2)
            self.recommendation_percent.setText(str(percent) + ' %')
            self.lineedit.setText(self.new_face.recommendation[1].person.name)

    def set_unknown_face(self):
        if len(self.unknown_faces):
            self.new_face = self.unknown_faces[0]
            del self.unknown_faces[0]
            self.update_face_image(self.new_face.face_picture_route)
            self.set_recomendation()
            self.create_button.setEnabled(True)
        else:
            self.create_button.setEnabled(False)
            self.face.clear()
            self.recommendation_percent.clear()
            if self.streaming.is_pause():
                self.streaming.pause_process()

    def capture_new_data(self, new_data):
        if len(new_data):
            self.unknown_faces += new_data
            if not self.create_button.isEnabled():
                self.set_unknown_face()
        return None

    def start_capturing_stream(self):
        video = self.video.text()
        if self.start_button.text() != 'Start':
            self.streaming.pause_process()
        else:
            self.start_button.setText('Pause')
            stream = [video]
            know_faces = [face for person in self.know_persons.values() for face in person.faces]
            self.streaming = Thread(stream=stream, known_faces=know_faces,
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
        face_data.set_know_faces(self.know_persons)
        face_data.save_stats(self.know_persons)
        face_data.create_csv_race_bar_graphic_data(self.know_persons)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    screen = Window()
    screen.show()
    sys.exit(app.exec_())