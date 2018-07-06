import threading
import queue
import cv2


class VideoCaptureDaemon(threading.Thread):

    def __init__(self, video, result_queue):
        super().__init__()
        self.daemon = True
        self.video = video
        self.result_queue = result_queue

    def run(self):
        self.result_queue.put(cv2.VideoCapture(self.video))


def get_video_capture(video, timeout=5):
    res_queue = queue.Queue()
    VideoCaptureDaemon(video, res_queue).start()
    try:
        return res_queue.get(block=True, timeout=timeout)
    except queue.Empty:
        print('cv2.VideoCapture: could not grab input ({}). Timeout occurred after {:.2f}s'.format(
            video, timeout))
