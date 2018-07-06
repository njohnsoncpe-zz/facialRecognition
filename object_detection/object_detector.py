import os
import cv2
import time
import argparse
import multiprocessing
import numpy as np
import tensorflow as tf
import pickle
from io import BytesIO
import base64
from utils.app_utils import FPS, WebcamVideoStream
from multiprocessing import Queue, Pool
from utils import label_map_util
from utils.network_utils import TCPServer
from utils import visualization_utils as vis_util #Matplotlib breaks current version, so we do not use Vis_utils

CWD_PATH = os.getcwd()

boxes_enc = b''

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

    # Visualization of the results of a detection.
    vis_util.visualize_boxes_and_labels_on_image_array(
    		image_np,
    		np.squeeze(boxes),
    		np.squeeze(classes).astype(np.int32),
    		np.squeeze(scores),
    		category_index,
    		use_normalized_coordinates=True,
    		line_thickness=8)
    # print([category_index.get(i) for i in classes[0]])
    # print(np.size(boxes))
    # print(np.shape(boxes))
    # print(np.size(classes))
    # print(np.shape(classes))
    # print(np.size(scores))
    # print(np.shape(scores))

    # print('BOXES:\n', boxes, 'SCORES:\n', scores, 'CLASSES:\n', classes, 'NUM_DETECT:\n', num_detections)

    boxes_str = np.array2string(boxes)
    out = base64.b64encode(boxes_str.encode())

    # scores_str = np.array2string(scores)
    # classes_str = np.array2string(classes)
    # num_detections_str = np.array2string(num_detections)

    return image_np, out

def queryParser(ip, queue, data):
    print(data, "recieved from", ip)
    #TODO Parse into string, look for isReady and start sending data.


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

        sess = tf.Session(graph=detection_graph)  # , config=config)

    fps = FPS().start()
    while True:
        fps.update()
        frame = input_q.get()
        print("Frame taken from input queue")
        # frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        output_q.put(detect_objects(frame, sess, detection_graph))

    fps.stop()
    sess.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', dest='video_source',
                        type=str, default='0', help='rstp://....')
    parser.add_argument('-nw', '--num-workers', dest='num_workers',
                        type=int, default=5, help='Number of workers.')
    parser.add_argument('-qs', '--queue-size', dest='queue_size',
                        type=int, default=10, help='Size of the queue.')
    args = parser.parse_args()

    logger = multiprocessing.log_to_stderr()
    logger.setLevel(multiprocessing.SUBDEBUG)

    if(args.video_source == '0'):
        print('please provide a valid addr')
        exit
    
    server = TCPServer("public", 20004, queryParser)
    print("test1")
    server.run()
    print("test2")
    
    input_q = Queue(maxsize=args.queue_size)
    output_q = Queue(maxsize=args.queue_size)
    pool = Pool(args.num_workers, worker, (input_q, output_q))

    # setup rtsp client connection
    video_capture = WebcamVideoStream(
        src=args.video_source).start()

    fps = FPS().start()

    try:
        while True:  # fps._numFrames < 120
            frame = video_capture.read()
            
            #print("frame read from stream")
            input_q.put(frame)
            #print("frame put into queue")
            t = time.time()
            # output_rgb = cv2.cvtColor(output_q.get(), cv2.COLOR_RGB2BGR)
            frame_2, arr = output_q.get()
            cv2.imshow('Video', frame_2)
            #if()
            #s.send(arr)
            fps.update()

            print('[INFO] elapsed time: {:.2f}'.format(time.time() - t))

            # s.send()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        fps.stop()

    fps.stop()
    video_capture.stop()
    print('[INFO] elapsed time (total): {:.2f}'.format(fps.elapsed()))
    print('[INFO] approx. FPS: {:.2f}'.format(fps.fps()))
    pool.terminate()
    video_capture.stop()
    cv2.destroyAllWindows()
