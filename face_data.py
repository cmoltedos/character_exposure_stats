import os, sys
import cv2
import numpy as np
import time
import uuid
import face_recognition
import threading
import math
from PIL import Image
from pdb import set_trace

import stream_capture

ANALYSE_EVERY_N_SECONDS=0.5

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
    for (top, right, bottom, left), (fid, name) in zip(locations, names):
        # Draw a box around the face
        cv2.rectangle(picture_frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(picture_frame, (left, bottom - 35), (right, bottom), (0, 0, 255),
                      cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(picture_frame, name, (left + 6, bottom - 6), font, 1.0,
                    (255, 255, 255), 1)
    return picture_frame


def get_best_match(known_face_encodings, face_encoding):
    matches = face_recognition.compare_faces(known_face_encodings,
                                             face_encoding)
    face_distances = face_recognition.face_distance(known_face_encodings,
                                                    face_encoding)
    best_match_index = np.argmin(face_distances)

    if matches[best_match_index]:
        return (best_match_index, face_distances[best_match_index])
    return (None, 1)



def detect_faces_name(picture_data, known_faces):
    picture_route, picture_frame = picture_data
    picture = face_recognition.load_image_file(picture_route)
    face_locations = face_recognition.face_locations(picture)
    face_encodings = face_recognition.face_encodings(picture, face_locations)
    face_id_and_names = list()
    new_unknow_faces = dict()
    if known_faces:
        known_face_id, values = zip(*known_faces.items())
        known_face_names, know_face_location, known_face_encodings = zip(*values)
    else:
        known_face_id, known_face_names, known_face_encodings = list(), list(), list()
    for face_encoding, face_location in zip(face_encodings, face_locations):
        name = f"Unknown"
        if len(known_face_encodings):
            # See if the face is a match for the known face(s)
            best_match_index, match_value = get_best_match(known_face_encodings, face_encoding)
        else:
            match_value = 1
            best_match_index = None

        if best_match_index is not None and match_value < 0.4:
            name = known_face_names[best_match_index]
            face_id = known_face_id[best_match_index]
        else:
            top, right, bottom, left = face_location
            # You can access the actual face itself like this:
            face_image = picture[top:bottom, left:right]
            pil_image = Image.fromarray(face_image)
            os.makedirs('faces', exist_ok=True)
            face_id = str(uuid.uuid4())
            unknow_route = f'faces/{face_id}.jpg'
            pil_image.save(unknow_route, "JPEG")
            unknow_data = [name, unknow_route, face_encoding]
            new_unknow_faces[face_id] = unknow_data
        face_id_and_names.append((face_id, name))
    capture_with_mark = mark_faces_in_picture(picture_frame, face_locations,
                                              face_id_and_names)
    return face_id_and_names, new_unknow_faces, capture_with_mark


def get_know_faces():
    know_faces = dict()
    if not os.path.exists('kwnow_faces_data.txt'):
        return know_faces
    with open('kwnow_faces_data.txt') as know_faces_file:
        for line in know_faces_file:
            data = line.strip().split(';;')
            data_array = np.array(list(map(float, data[-1].split(','))))
            know_faces[data[0]] = data[1:-1] + [data_array]
    return know_faces


def set_know_faces(know_faces):
    with open('kwnow_faces_data.txt', 'w') as know_faces_file:
        for know_face in know_faces:
            know_face_value = know_faces[know_face][:4]
            array_image_str = ','.join(map(str, know_face_value[-1]))
            new_line = ';;'.join([know_face]
                                 + list(map(str, know_face_value[:-1]))
                                 + [array_image_str])
            know_faces_file.write(new_line + '\n')
    return None


def update_stats(stat_dict, new_data):
    for data in new_data[1]:
        fid = data[0]
        if fid not in stat_dict:
            stat_dict[fid] = list()
        stat_dict[fid].append(new_data[0])
    return None


def save_stats(stat_dict):
    stat_filename = 'stat_data.txt'
    with open(stat_filename, 'w') as stat_file:
        for stat_key, stat_value in stat_dict.items():
            line = f"{str(stat_key)}::{','.join(map(str, stat_value))}\n"
            stat_file.write(line)
    return stat_filename


def get_stats_data_from_file(stat_filename):
    stat_dict = dict()
    with open(stat_filename) as stat_file:
        for line in stat_file:
            content = line.strip().split('::')
            stat_dict[content[0]] = list(map(float, content[1].split(',')))
    return stat_dict


def create_csv_race_bar_graphic_data(stat_dict, know_faces, sec_window=10):
    result_filename = 'race_bar_data.csv'
    max_seconds_per_id = list(map(max, stat_dict.values()))
    if not max_seconds_per_id:
        return None
    max_second = max(max_seconds_per_id)
    stat_faces_id = list(stat_dict.keys())
    stat_faces_names = list(map(lambda x: know_faces[x][0], stat_faces_id))
    name_stats = dict()
    for face_name, face_id in zip(stat_faces_names, stat_faces_id):
        if face_name not in name_stats:
            name_stats[face_name] = list()
        name_stats[face_name] += stat_dict[face_id]
    list(map(lambda x: x.sort(), name_stats.values()))
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
            new_unknown_faces = capture_data[2]
            update_stats(stat_dict, capture_data)
            known_faces.update(new_unknown_faces)
            cv2.imshow('TV', capture_data[-1])
            cv2.waitKey(1)
    process_stream_thread.join()
    set_know_faces(known_faces)
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
            # actual time, face id and names, new unknow faces (id, name, picture route, face encoding), frame with mark
            time_data = (actual_second,) + capture_data
            actual_second += ANALYSE_EVERY_N_SECONDS
            yield time_data


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
    do_analysis()