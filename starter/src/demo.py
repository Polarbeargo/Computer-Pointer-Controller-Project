from argparse import ArgumentParser
from input_feeder import InputFeeder
import os
from face_detection import Model_Face
from facial_landmarks_detection import Model_Landmark
from gaze_estimation import Model_Gaze
from head_pose_estimation import Model_Pose
from mouse_controller import MouseController
import cv2
import imutils
import math

WEBCAM = 'cam'
IMAGE = 'image'
VIDEO = 'video'
IP_CAMERA = 'ip-cam'

ALLOWED_EXTENSIONS = ['mp4', 'avi', 'jpg', 'png', 'jpeg']

def imshow(windowname, frame, width=None):
    if width == None:
        width = 400

    frame = imutils.resize(frame, width=width)
    cv2.imshow(windowname, frame)


def build_argparser():
    parser = ArgumentParser()
    parser.add_argument("-f", "--face", required=True, type=str,
                        help="Path to .xml file of Face Detection model.")
    parser.add_argument("-l", "--landmarks", required=True, type=str,
                        help="Path to .xml file of Facial Landmark Detection model.")
    parser.add_argument("-hp", "--headpose", required=True, type=str,
                        help="Path to .xml file of Head Pose Estimation model.")
    parser.add_argument("-ge", "--gazeestimation", required=True, type=str,
                        help="Path to .xml file of Gaze Estimation model.")
    parser.add_argument("-i", "--input", required=True, type=str,
                        help="Path to video file or enter cam for webcam")
    parser.add_argument("-it", "--input_type", required=True, type=str,
                        help="Provide the source of video frames." + VIDEO + " " + WEBCAM + " | " + IP_CAMERA + " | " + IMAGE)
    parser.add_argument("-debug", "--debug", required=False, type=str, nargs='+',
                        default=[],
                        help="To debug each model's output visually, type the model name with comma seperated after --debug")
    parser.add_argument("-ld", "--cpu_extension", required=False, type=str,
                        default=None,
                        help="linker libraries if have any")
    parser.add_argument("-d", "--device", type=str, default="CPU",
                        help="Provide the target device: "
                             "CPU, GPU, FPGA or MYRIAD is acceptable.")

    return parser

    def main(args):

        feeder = None
        if args.input_type == VIDEO or args.input_type == IMAGE:
            extension = str(args.input).split('.')[1]
        if not extension.lower() in ALLOWED_EXTENSIONS:
            print('Please provide supported extension.' +
                         str(ALLOWED_EXTENSIONS))
            exit(1)

        if not os.path.isfile(args.input):
            print("Unable to find specified video/image file")
            exit(1)

            feeder = InputFeeder(args.input_type, args.input)
        elif args.input_type == IP_CAMERA:
            if not str(args.input).startswith('http://'):
                print('Please provide ip of server with http://')
                exit(1)

            feeder = InputFeeder(args.input_type, args.input)
        elif args.input_type == WEBCAM:
            feeder = InputFeeder(args.input_type)

        mc = MouseController("medium", "fast")

        feeder.load_data()

        face_model = Face_Model(args.face, args.device, args.cpu_extension)
        face_model.check_model()

        landmark_model = Model_Landmark(args.landmarks, args.device, args.cpu_extension)
        landmark_model.check_model()

        gaze_model = Model_Gaze(args.gazeestimation, args.device, args.cpu_extension)
        gaze_model.check_model()

        head_model = Model_Pose(
        args.headpose, args.device, args.cpu_extension)
        head_model.check_model()

        face_model.load_model()
        print("Face Detection Model Loaded...")
        landmark_model.load_model()
        print("Landmark Detection Model Loaded...")
        gaze_model.load_model()
        print("Gaze Estimation Model Loaded...")
        head_model.load_model()
        print("Head Pose Detection Model Loaded...")
        print('Loaded')

        try:
            frame_count = 0
            for ret, frame in feeder.next_batch():
                if not ret:
                    break

                if frame is None:
                    continue

                frame_count += 1
                crop_face = None
                if frame_count % 3 ==0:

                    crop_face, box = face_model.predict(frame.copy())

                    if crop_face is None:
                        print("Unable to detect the face.")
                        continue

                    (lefteye_x, lefteye_y), (righteye_x, righteye_y), eye_coords, left_eye, right_eye = landmark_model.predict(
                    crop_face.copy(), eye_surrounding_area=15)
                
    

                    head_position = head_model.predict(crop_face.copy())

                    gaze, (mousex, mousey) = gaze_model.predict(left_eye.copy(), right_eye.copy(), head_position)
               
                    if (len(args.debug) > 0):
                        debuFrame = frame.copy()
                        if crop_face is None:
                            continue

                        thickness = 2
                        radius = 2
                        color = (0, 0, 255)
                        [[le_xmin, le_ymin, le_xmax, le_ymax], [re_xmin, re_ymin, re_xmax, re_ymax]] = eye_coords

                        '''
                        LandMark
                        '''
                        cv2.circle(crop_face, (lefteye_x, lefteye_y), radius, color, thickness)
                        cv2.circle(crop_face, (righteye_x, righteye_y), radius, color, thickness)

                        if 'headpose' in args.debug:
                            yaw = head_position[0]
                            pitch = head_position[1]
                            roll = head_position[2]

                            sinY = math.sin(yaw * math.pi / 180.0)
                            sinP = math.sin(pitch * math.pi / 180.0)
                            sinR = math.sin(roll * math.pi / 180.0)

                            cosY = math.cos(yaw * math.pi / 180.0)
                            cosP = math.cos(pitch * math.pi / 180.0)
                            cosR = math.cos(roll * math.pi / 180.0)

                            cH, cW = crop_face.shape[:2]
                            arrowLength = 0.4 * cH * cW

                            xCenter = int(cW / 2)
                            yCenter = int(cH / 2)

                            # center to right
                            cv2.line(crop_face, (xCenter, yCenter),
                                 (int((xCenter + arrowLength * (cosR * cosY + sinY * sinP * sinR))),
                                  int((yCenter + arrowLength * cosP * sinR))), (186, 204, 2), 1)

                            # center to top
                            cv2.line(crop_face, (xCenter, yCenter),
                                 (int(((xCenter + arrowLength * (cosR * sinY * sinP + cosY * sinR)))),
                                  int((yCenter - arrowLength * cosP * cosR))), (186, 204, 2), 1)

                            # center to forward
                            cv2.line(crop_face, (xCenter, yCenter),
                                 (int(((xCenter + arrowLength * sinY * cosP))),
                                  int((yCenter + arrowLength * sinP))), (186, 204, 2), 1)

                            cv2.putText(crop_face, 'head pose: (y={:.2f}, p={:.2f}, r={:.2f})'.format(yaw, pitch, roll),
                                    (0, 20), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.35, (255, 255, 255), 1)

                        if 'gaze' in args.debug:
                            cH, cW = crop_face.shape[:2]
                            arrowLength = 0.4 * cH * cW

                            gazeArrowX = gaze[0] * arrowLength
                            gazeArrowY = -gaze[1] * arrowLength

                            cv2.rectangle(crop_face, (re_xmin, re_ymin), (re_xmax, re_ymax), (255, 255, 255))
                            cv2.rectangle(crop_face, (le_xmin, le_ymin), (le_xmax, le_ymax), (255, 255, 255))

                            cv2.arrowedLine(crop_face, (lefteye_x, lefteye_y),
                                        (int(lefteye_x + gazeArrowX), int(lefteye_y + gazeArrowY)), (184, 113, 57), 2)
                            cv2.arrowedLine(crop_face, (righteye_x, righteye_y),
                                        (int(righteye_x + gazeArrowX), int(righteye_y + gazeArrowY)), (184, 113, 57), 2)

                            cv2.putText(crop_face, 'gaze angles: h={}, v={}'.format("!", "2"), (0, 10),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.35, (255, 255, 255), 1)

                            imshow("face", crop_face, width=400)
                            cv2.moveWindow("face", 0, 0)
                            imshow("debug", debuFrame, width=400)
                            cv2.moveWindow("debug", cW * 2, cH)

                    try:
                        mc.move(gaze[0], gaze[1])
                    except Exception as err:
                        print("Moving cursor outside the PC not supported yet !!")

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except Exception as err:
            print(err)

        cv2.destroyAllWindows()
        feeder.close()

    if __name__ == '__main__':

        args = build_argparser().parse_args()

        main(args)
