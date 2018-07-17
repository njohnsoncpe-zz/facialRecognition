import os
import cv2
import time
import argparse
import multiprocessing
import numpy as np
import tensorflow as tf
from io import BytesIO
import base64
from utils.app_utils import WebcamVideoStream
from multiprocessing import Queue, Pool
from utils import label_map_util
from utils.network_utils import ThreadedServer
from utils import visualization_utils as vis_util
import json
CWD_PATH = os.getcwd()

# Use JIT Compilation to get speed up. Experimental feature.
# config = tf.ConfigProto()
# config.graph_options.optimizer_options.global_jit_level = tf.OptimizerOptions.ON_1


# Path to frozen detection graph. This is the actual model that is used for the object detection.
MODEL_NAME = 'ssd_mobilenet_v1_coco_11_06_2017'
PATH_TO_CKPT = os.path.join(CWD_PATH, MODEL_NAME, 'frozen_inference_graph.pb')

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join(CWD_PATH, 'data', 'mscoco_label_map.pbtxt')

NUM_CLASSES = 90

# Loading label map
print(">Loading Label Map")
label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(
    label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)


def convert_keys_to_string(dictionary):
    """Recursively converts dictionary keys to strings."""
    if not isinstance(dictionary, dict):
        return dictionary
    return dict((str(k), convert_keys_to_string(v)) for k, v in dictionary.items())


def detect_objects(image_np, sess, detection_graph):
    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)
    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')

    # Each box represents a part of the image where a particular object was detected.
    boxes = detection_graph.get_tensor_by_name('detection_boxes:0')

    # Each score represent how level of confidence for each of the objects.
    # Score is shown on the result image, together with the class label.
    scores = detection_graph.get_tensor_by_name('detection_scores:0')
    classes = detection_graph.get_tensor_by_name('detection_classes:0')
    num_detections = detection_graph.get_tensor_by_name('num_detections:0')

    # Actual detection.
    (boxes, scores, classes, num_detections) = sess.run(
        [boxes, scores, classes, num_detections], feed_dict={image_tensor: image_np_expanded})

    # # Visualization of the results of a detection.
    # vis_util.visualize_boxes_and_labels_on_image_array(
    #     image_np,
    #     np.squeeze(boxes),
    #     np.squeeze(classes).astype(np.int32),
    #     np.squeeze(scores),
    #     category_index,
    #     use_normalized_coordinates=True,
    #     line_thickness=8, min_score_thresh=0.4)

    detection_dict = vis_util.create_detection_dict(
        np.squeeze(boxes),
        np.squeeze(classes).astype(np.int32),
        np.squeeze(scores),
        category_index,
        use_normalized_coordinates=True,
        line_thickness=8, min_score_thresh=0.4)

    # print("RAW: ", detection_dict)
    detection_dict_annotated = {}
    detection_dict_annotated = [
        {"object_location": i, "object_data": j} for i, j in detection_dict.items()]
    # print("ANNOTATED: ", detection_dict_annotated,
    #       type(detection_dict_annotated))
    detection_dict_json = json.dumps(
        detection_dict_annotated)
    # print("JSOND: ", detection_dict_json, type(detection_dict_json))
    # print(json.loads(detection_dict_json))
    return detection_dict_json


def queryParser(ip, queue, data):
    print(data, "recieved from", ip)
    # TODO: Parse into string, look for isReady and start sending data.


def worker(input_q, output_q):
    # Load a (frozen) Tensorflow model into memory.
    print(">Loading Frozen Graph")
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.FastGFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

        sess = tf.Session(graph=detection_graph) #config enable for JIT

    while True:
        frame, start = input_q.get()
        # print(">Frame taken from input queue")
        # frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        output_q.put((detect_objects(frame, sess, detection_graph), start))
    sess.close()


def getRTSPStream():
    while True:
        if (server.isClientConnected):
            print('INPUTS:')
            for s in server.inputs:
                print(s.getsockname())
            print('OUTPUTS:')
            for s in server.outputs:
                print(s.getpeername())
            # TODO: This is only valid for single user case.
            src = 'rtsp://'+ str(server.outputs[0].getpeername()[0]) + ':1234/h264'
            ret = (WebcamVideoStream(src=src).start())
            return ret
        time.sleep(0.5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-nw', '--num-workers', dest='num_workers',
                        type=int, default=5, help='Number of workers.')
    parser.add_argument('-qs', '--queue-size', dest='queue_size',
                        type=int, default=10, help='Size of the queue.')
    args = parser.parse_args()

    logger = multiprocessing.log_to_stderr()
    logger.setLevel(multiprocessing.SUBWARNING)

    server = ThreadedServer('', 20004)
    input_q = Queue(maxsize=args.queue_size)
    output_q = Queue(maxsize=args.queue_size)
    pool = Pool(args.num_workers, worker, (input_q, output_q))

    while True:
        try:
            video_capture = getRTSPStream()
            
            while (server.isClientConnected and server.isClientReady):
                frame = video_capture.read()
                # Rotate incoming video stream, For debug only should be removed o/w
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                start = time.time()
                input_q.put((frame, start))  # Add Frame to Queue
                # output_rgb = cv2.cvtColor(output_q.get(), cv2.COLOR_RGB2BGR)
                out, start = output_q.get()
                end = time.time()
                print("Frame processing time: " + str((end - start)) + " seconds.")
                if (len(server.outputs) > 0):
                    # out = out + "#END#"
                    server.appendToMessageBuff(bytes((str((time.time()*1000)) + "#" + out), 'utf-8'))
                    # TODO: add buffer control
                else:
                    print("no clients!")
            
            
        except KeyboardInterrupt:
            video_capture.stop()
            pool.terminate()
            break
    

