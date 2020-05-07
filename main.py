import os
import cv2
import numpy as np
import time
import face_recognition
import stream_capture
from PIL import Image
from pdb import set_trace

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
    result_images = list()
    while (True):
        # reading from frame
        ret, frame = cam.read()
        if not ret:
            break
        elif currentframe % fps == 0:
            # if video is still left continue creating images
            actual_image_counter += 1
            name = './data/frame%.8d.jpg' % actual_image_counter
            print('Creating: ' + name)
            # writing the extracted images
            cv2.imwrite(name, frame)
            result_images.append((name, frame))
        # increasing counter so that it will show how many frames are created
        currentframe += 1
    # Release all space and windows once done
    cam.release()
    cv2.destroyAllWindows()
    return result_images


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
    cv2.imshow('Video', picture_frame)
    cv2.waitKey(1)


def detect_faces_name(picture_data, known_faces):
    picture_route, picture_frame = picture_data
    picture = face_recognition.load_image_file(picture_route)
    face_locations = face_recognition.face_locations(picture)
    face_encodings = face_recognition.face_encodings(picture, face_locations)
    face_names = []
    unknown_faces_amount = len(list(filter(lambda x: 'Unknown' in x[0], known_faces)))
    new_unknow_faces = list()
    if known_faces:
        known_face_names, know_face_location, known_face_encodings = zip(*known_faces)
    else:
        known_face_encodings, known_face_names = list(), list()
    for face_encoding, face_location in zip(face_encodings, face_locations):
        name = f"Unknown_{unknown_faces_amount+1}"
        if len(known_face_encodings):
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(known_face_encodings,
                                                     face_encoding)
            face_distances = face_recognition.face_distance(known_face_encodings,
                                                            face_encoding)
            best_match_index = np.argmin(face_distances)
        else:
            best_match_index = None

        if best_match_index is not None and matches[best_match_index] \
                and face_distances[best_match_index] < 0.4:
            name = known_face_names[best_match_index]
        else:
            unknown_faces_amount += 1
            top, right, bottom, left = face_location

            # You can access the actual face itself like this:
            face_image = picture[top:bottom, left:right]
            pil_image = Image.fromarray(face_image)
            os.makedirs('faces', exist_ok=True)
            unknow_route = f'faces/{name}.jpg'
            pil_image.save(unknow_route, "JPEG")
            new_unknow_faces.append((name, unknow_route, face_encoding))
        face_names.append(name)
    mark_faces_in_picture(picture_frame, face_locations, face_names)
    return face_names, new_unknow_faces


def get_know_faces():
    know_faces = list()
    if not os.path.exists('kwnow_faces_data.txt'):
        return know_faces
    with open('kwnow_faces_data.txt') as know_faces_file:
        for line in know_faces_file:
            data = line.strip().split(';;')
            data_array = np.array(list(map(float, data[2].split(','))))
            know_faces.append((data[0], data[1], data_array))
    return know_faces


def set_know_faces(know_faces):
    with open('kwnow_faces_data.txt', 'w') as know_faces_file:
        line_format = '{name};;{location};;{array}\n'
        for know_face in know_faces:
            new_line = line_format.format(
                name=know_face[0], location=know_face[1],
                array=','.join(map(str, know_face[2]))
            )
            know_faces_file.write(new_line)
    return None


def identify_unknown_faces(unknown_faces):
    i = 0
    while i < len(unknown_faces):
        actual_name, picture_route, _ = unknown_faces[i]
        image = cv2.imread(picture_route)
        cv2.imshow(actual_name, image)
        cv2.waitKey(1)
        new_name = input(f'Insert name for {actual_name}: ')
        if new_name:
            unknown_faces[i] = (new_name, picture_route, _)
        i += 1
    return None


def do_work():
    stream = stream_capture.LiveStream(channel='tvn')
    resolution = '360' # str(input(f'Insert a resolution: '))
    actual_second = 0
    frame_n = 0
    known_faces = get_know_faces()
    faces_stat = dict()
    streaming = stream.get_n_second_batches(resolution=resolution, seconds=60)
    # streaming = ['result_tvn_57a498c4d7b86d600e5461cb.ts']
    for video in streaming:
        captures = get_frames_per_second(video, frame_n)
        frame_n += len(captures)
        for capture in captures:
            faces, new_unknown_faces = detect_faces_name(capture, known_faces)
            identify_unknown_faces(new_unknown_faces)
            known_faces += new_unknown_faces
            for face in faces:
                if face not in faces_stat:
                    faces_stat[face] = list()
                faces_stat[face].append(actual_second)
            actual_second += ANALYSE_EVERY_N_SECONDS
    set_know_faces(known_faces)
    return faces_stat


if __name__ == "__main__":
    do_work()