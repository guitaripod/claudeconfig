# Face detector

`face_detection_yunet_2026may.onnx` — YuNet, from
[opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet),
Apache-2.0. 225 KB.

The 2026may export has dynamic input dimensions, which OpenCV 5's ONNX Runtime
engine needs; the older 2023mar export has a fixed shape. `faces.py` resolves this
file relative to `scripts/`, or `VIDEO_EDIT_FACE_MODEL` overrides it.
