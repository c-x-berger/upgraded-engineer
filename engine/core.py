import cv2
import shlex
import subprocess
from typing import Tuple

DEFAULT_SOCKET_PATH = "/tmp/engineering"
DEFAULT_EXEC = "/usr/local/bin/potential-engine"
DEFAULT_VIDEO_SIZE = (640, 480, 30)


class Engine:
    """
    Class which starts and manages a potential-engine process.
    """

    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        engine_exec: str = DEFAULT_EXEC,
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
    ):
        """
        Constructor. Starts a new potential-engine process.
        
        :param socket_path: Location to create the shared memory socket at.
        :param engine_exec: Absolute path to the compiled potential-engine binary. 
        :param video_size: Tuple of video dimensions (width, height, framerate)
        """
        self.launchline = "{exec_} -w {w} -h {h} -f {f} -d {sock} --port {p} --shared_memory".format(
            exec_=engine_exec,
            w=video_size[0],
            h=video_size[1],
            f=video_size[2],
            sock=socket_path,
        )
        self.process = None
        # self.process = subprocess.Popen(shlex.split(launchline))

    def start(self):
        self.process = subprocess.Popen(shlex.split(self.launchline))

    def stop(self):
        if self.process is not None:
            self.process.terminate()


class EngineWriter(Engine):
    """
    Starts an engine and provides easy access to the shared memory socket.
    """

    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        engine_exec: str = DEFAULT_EXEC,
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
    ):
        super().__init__(socket_path, engine_exec, video_size)
        # pipeline, (magic gst number), 0, framerate, video dimensions tuple
        self.writer = cv2.VideoWriter(
            "appsrc ! video/x-raw,format=BGR ! videoconvert ! video/x-raw,format=I420 ! shmsink socket-path = {}".format(
                socket_path
            ),
            cv2.CAP_GSTREAMER,
            0,
            video_size[2],
            video_size[:2],
        )
        super().start()

    def write_frame(self, frame):
        """
        Write a frame into the engine. Call in a tight loop, you need to hit your given framerate!

        :param frame: Frame to write to shared memory.
        """
        self.writer.write(frame)

    def stop(self):
        super().stop()
        self.writer.release()
