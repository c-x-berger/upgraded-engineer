from typing import Tuple

import cv2

from .core import EngineWriter, DEFAULT_SOCKET_PATH, DEFAULT_VIDEO_SIZE


class OpenCVEngineWriter(EngineWriter):
    """
    Starts an engine and provides easy access to the shared memory socket.
    """

    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
        autostart: bool = True,
    ):
        super().__init__(socket_path, video_size, autostart)
        # pipeline, 0 (magic gst number), framerate, video dimensions tuple
        self.writer = cv2.VideoWriter(
            "appsrc ! videoconvert ! video/x-raw,format=I420 ! shmsink socket-path = {}".format(
                socket_path
            ),
            0,
            video_size[2],
            video_size[:2],
        )

    def write_frame(self, frame):
        """
        Write a frame into the engine. Call in a tight loop, you need to hit your given framerate!

        :param frame: Frame to write to shared memory.
        """
        self.writer.write(frame)

    def stop(self):
        super().stop()
        if self.writer.isOpened():
            self.writer.release()
