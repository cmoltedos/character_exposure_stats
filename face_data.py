import os, sys
import cv2
import numpy as np
import time
import uuid
import face_recognition
import threading
import math
import shutil
from PIL import Image
from pdb import set_trace

ANALYSE_EVERY_N_SECONDS=0.5
UNKONWN_FACES_DIR = 'unknown_faces'
KNOWN_FACES_DIR = 'known_faces'

class FaceData(object):

    def __init__(self, encoding, face_picture_route=None, face_id=None,
                 person=None):
        self.encoding = encoding
        self.face_picture_route = face_picture_route
        self.face_id = face_id
        self.person = person
        self.recommendation = None
        self.timings = list()

    def __str__(self):
        encoding_str = ','.join(map(str, self.encoding))
        return f'{self.face_id};;{self.face_picture_route};;{encoding_str}'

    def set_face_data(self, base_picture, location):
        top, right, bottom, left = location
        face_image = base_picture[top:bottom, left:right]
        pil_image = Image.fromarray(face_image)
        os.makedirs(UNKONWN_FACES_DIR, exist_ok=True)
        face_id = str(uuid.uuid4())
        unknow_route = os.path.join(UNKONWN_FACES_DIR, f'{face_id}.jpg')
        pil_image.save(unknow_route, "JPEG")
        self.face_picture_route = unknow_route
        self.face_id = face_id

    def change_picture_route(self, new_dir):
        new_route = os.path.join(new_dir, os.path.basename(self.face_picture_route))
        if new_route != self.face_picture_route:
            shutil.move(self.face_picture_route, new_route)
            self.face_picture_route = new_route

    def set_recomendation(self, recommendation):
        # input: face distance, face
        self.recommendation = recommendation

    @staticmethod
    def face_from_string(face_string):
        data = face_string.strip().split(';;')
        encoding = np.array(list(map(float, data[-1].split(','))))
        return FaceData(
            encoding=encoding, face_picture_route=data[1], face_id=data[0]
        )

    def __del__(self):
        if (self.person is None and self.face_picture_route is not None
                and os.path.exists(self.face_picture_route)):
            os.remove(self.face_picture_route)


class Person(object):

    def __init__(self, name):
        self.name = name
        self.faces = list()
        self.timings = list()

    def add_face(self, face):
        face_dir = os.path.join(KNOWN_FACES_DIR, self.name)
        os.makedirs(face_dir, exist_ok=True)
        face.change_picture_route(face_dir)
        face.person = self
        self.timings += face.timings
        face.timing = list()
        self.faces.append(face)

    def save(self, open_file):
        open_file.write(f'NAME:{self.name}\n')
        for face in self.faces:
            open_file.write(str(face) + '\n')

    def save_stats(self, open_file):
        line = f"{self.name}::{','.join(map(str, self.timings))}"
        open_file.write(line + '\n')


def get_faces_in_picture(picture_route):
    image = face_recognition.load_image_file(picture_route)
    face_locations = face_recognition.face_locations(image)
    return face_locations


def get_frames_per_second(video_route, actual_image_counter=0):
    cam = cv2.VideoCapture(video_route)
    try:
        os.makedirs('data', exist_ok=True)
    except OSError:
        print('Error: Creating directory of data')
    fps = cam.get(cv2.CAP_PROP_FPS)
    currentframe = 0
    while (True):
        # reading from frame
        ret, frame = cam.read()
        if not ret:
            break
        elif currentframe % (fps * ANALYSE_EVERY_N_SECONDS) == 0:
            # if video is still left continue creating images
            actual_image_counter += 1
            name = './data/frame%.8d.jpg' % actual_image_counter
            print('Creating: ' + name)
            # writing the extracted images
            cv2.imwrite(name, frame)
            yield (name, frame)
        # increasing counter so that it will show how many frames are created
        currentframe += 1
    # Release all space and windows once done
    cam.release()
    # cv2.destroyAllWindows()


def create_image_from_frame(result_route, frame):
    cv2.imwrite(result_route, frame)
    return result_route


def mark_faces_in_picture(picture_frame, locations, names):
    for (top, right, bottom, left), name in zip(locations, names):
        # Draw a box around the face
        cv2.rectangle(picture_frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(picture_frame, (left, bottom - 35), (right, bottom), (0, 0, 255),
                      cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(picture_frame, name, (left + 6, bottom - 6), font, 1.0,
                    (255, 255, 255), 1)
    return picture_frame


def detect_faces_name(picture_data, known_faces):
    picture_route, picture_frame = picture_data
    picture = face_recognition.load_image_file(picture_route)
    face_locations = face_recognition.face_locations(picture)
    face_encodings = face_recognition.face_encodings(picture, face_locations)
    face_names = list()
    know_element = list()
    unknow_faces = list()
    for face_encoding, face_location in zip(face_encodings, face_locations):
        new_face = FaceData(encoding=face_encoding)
        if known_faces:
            actual_faces = [face.encoding for face in known_faces]
            face_distances = face_recognition.face_distance(actual_faces,
                                                            new_face.encoding)
            recognition_list = sorted(zip(face_distances, known_faces))
            if recognition_list[0][0] < 0.5:
                person = recognition_list[0][1].person
                if person is None:
                    name = 'Unknown '
                    know_element.append(recognition_list[0][1]) # Face
                else:
                    name = person.name
                    know_element.append(person)
            elif len(recognition_list) > 10:
                exact_person = get_best_name(recognition_list[:10])
                if exact_person is not None:
                    name = exact_person.name
                    know_element.append(exact_person)
                else:
                    name = 'Unknown'
                    recommendation = min(recognition_list[:10])
                    new_face.set_recomendation(recommendation)
            else:
                name = 'Unknown'
        else:
            name = 'Unknown'

        if name == 'Unknown':
            new_face.set_face_data(base_picture=picture,
                                   location=face_location)
            unknow_faces.append(new_face)
        face_names.append(name)
    capture_with_mark = mark_faces_in_picture(picture_frame, face_locations,
                                              face_names)
    return know_element, unknow_faces, capture_with_mark


def get_best_name(best_list):
    stat_dict = dict()
    for match_value, face in best_list:
        person = face.person
        if person is None:
            continue
        if person.name not in stat_dict:
            stat_dict[person.name] = [0, person]
        stat_dict[person.name][0] += 1
    data = stat_dict.values()
    if data:
        best = max(data, key=lambda x: x[0])
        exact_person = best[1] if best[0] >= 8 else None
    else:
        exact_person = None
    return exact_person


def get_know_faces():
    know_faces = dict()
    if not os.path.exists('kwnow_faces_data.txt'):
        return know_faces
    with open('kwnow_faces_data.txt') as know_faces_file:
        for line in know_faces_file:
            if line.startswith('NAME:'):
                tag, name = line.strip().split(':')
                person = Person(name=name)
                know_faces[name] = person
            else:
                data = FaceData.face_from_string(line.strip())
                person.add_face(data)
    return know_faces


def set_know_faces(know_faces):
    with open('kwnow_faces_data.txt', 'w') as know_faces_file:
        for person in know_faces.values():
            person.save(know_faces_file)
    return None


def save_stats(know_persons):
    stat_filename = 'stat_data.txt'
    with open(stat_filename, 'w') as stat_file:
        for person in know_persons.values():
            person.save_stats(stat_file)
    return stat_filename


def get_stats_data_from_file(stat_filename):
    stat_dict = dict()
    with open(stat_filename) as stat_file:
        for line in stat_file:
            content = line.strip().split('::')
            stat_dict[content[0]] = list(map(float, content[1].split(',')))
    return stat_dict


def create_csv_race_bar_graphic_data(know_persons, sec_window=10):
    result_filename = 'race_bar_data.csv'
    max_second = 0
    name_stats = dict()
    for person in know_persons.values():
        max_second_p = max(person.timings) if person.timings else 0
        if max_second_p > max_second:
            max_second = max_second_p
        name_stats[person.name] = sorted(person.timings)

    header = ['Person'] + list(map(str, range(math.ceil(max_second/sec_window))))
    with open(result_filename, 'w') as result_file:
        result_file.write(','.join(header) + '\n')
        for face_name, times in name_stats.items():
            line_list = [0] * math.ceil(max_second/sec_window)
            for second in times:
                block_i = int(second/sec_window)
                line_list[block_i] += ANALYSE_EVERY_N_SECONDS
            # cumulative sum
            for i in range(1, len(line_list)):
                line_list[i] += line_list[i-1]
            line_list = [face_name] + list(map(str, line_list))

            result_file.write(','.join(line_list) + '\n')
    return result_filename


def do_work_uni_thread():
    streaming = ['result_13_b859e668b266815bf6771bf001ee2ddd.ts']
    known_faces = get_know_faces()
    for capture_data in yield_process_streaming(known_faces, streaming):
        cv2.imshow('TV', capture_data[-1])
        cv2.waitKey(1)
    cv2.destroyAllWindows()
    return None


def do_work():
    #stream = stream_capture.LiveStream(channel='tvn')
    resolution = '360' # str(input(f'Insert a resolution: '))
    #streaming = stream.get_n_second_batches(resolution=resolution)
    streaming = ['result_13_b859e668b266815bf6771bf001ee2ddd.ts']
    known_faces = get_know_faces()
    result_queue = list()
    process_stream_thread = threading.Thread(
        target=process_streaming, args=(known_faces, streaming, result_queue)
    )
    stat_dict = dict()
    process_stream_thread.start()
    while process_stream_thread.is_alive():
        if not len(result_queue):
            time.sleep(1)
            continue
        while len(result_queue):
            capture_data = result_queue[0]
            del result_queue[0]
            cv2.imshow('TV', capture_data[-1])
            cv2.waitKey(1)
    process_stream_thread.join()
    cv2.destroyAllWindows()
    return None


def get_rgb_image_from_frame(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def yield_process_streaming(known_faces, streaming):
    actual_second = 0
    frame_n = 0
    for video in streaming:
        for capture in get_frames_per_second(video, frame_n):
            frame_n += 1
            capture_data = detect_faces_name(capture, known_faces)
            # elements (person or face), unknow_faces, capture_with_mark
            for element in capture_data[0] + capture_data[1]:
                element.timings.append(actual_second)
            known_faces += capture_data[1]
            actual_second += ANALYSE_EVERY_N_SECONDS
            yield capture_data[1], capture_data[2]


def process_streaming(known_faces, streaming, result_queue):
    for result in yield_process_streaming(known_faces, streaming):
        result_queue.append(result)
    return None


def do_analysis():
    stat_dict = get_stats_data_from_file('stat_data.txt')
    known_faces_dict = get_know_faces()
    create_csv_race_bar_graphic_data(stat_dict, known_faces_dict)


if __name__ == "__main__":
    # do_work()
    do_work_uni_thread()
    # do_analysis()