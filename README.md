## Facial Detection Over IP
The goal of this project is to detect Faces in live IP Camera footage. We use Tensorflow as our back end and build off of the
SSD MobileNet Architecture. Versions using Inception V1/V2 are being explored for higher accuracy.

[Video Exposition](https://youtu.be/-ED7T9X5zcY)

## Motivation
We take in a live video stream from a network connected camera and perform image classification on the frames of this video. This video is then sent over LAN to an embedded device for display purposes (i.e. ARM Processor).

By taking this approach, we can allow users to explore image classification output on devices not powerful enough to perform these computations themselves. Additionally, any smartphone can act as the video source.

## Tech/framework used

<b>Built with</b>
- [TensorFlow](https://www.tensorflow.org/)
- [OpenCV](https://opencv.org/)
- [NVIDIA cuDNN](https://developer.nvidia.com/cudnn)

## Installation
Coming soon.
## Credits
Inspired by [TensorFlow Model Zoo](https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/detection_model_zoo.md)
## License
MIT License. Provided AS IS.

MIT © [Noah Johnson](njohnsoncpe.github.io)
