import shlex
import subprocess
import threading
import time
from typing import Tuple

import cv2
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # isort:skip

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
        launchline = "{exec_} -w {w} -h {h} -f {f} -d {sock} --shared_memory".format(
            exec_=engine_exec,
            w=video_size[0],
            h=video_size[1],
            f=video_size[2],
            sock=socket_path,
        )
        print(launchline)
        self.process = subprocess.Popen(shlex.split(launchline))


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


class GStreamerWriter:
    def __init__(self, socket_path: str, repeat_frames: bool = False):
        self.thread = threading.Thread(target=self.__run_pipeline__)
        self.frame = None
        self.repeat_frames = repeat_frames

        Gst.init(None)
        self.pipeline = Gst.Pipeline.new(None)

        caps = Gst.Caps.from_string(
            f"video/x-raw,format=I420,height=240,width=320,framerate=30/1"
        )
        self.appsrc = Gst.ElementFactory.make("appsrc")
        videoconvert = Gst.ElementFactory.make("videoconvert")
        shmsink = Gst.ElementFactory.make("shmsink")

        self.appsrc.connect("need-data", self.__need_data__)
        self.appsrc.set_property("caps", caps)
        self.appsrc.set_property("is-live", True)
        shmsink.set_property("socket-path", socket_path)
        shmsink.set_property("sync", False)
        shmsink.set_property("wait-for-connection", False)
        shmsink.set_property("processing-deadline", 100)

        self.pipeline.add(self.appsrc)
        self.pipeline.add(videoconvert)
        self.pipeline.add(shmsink)

        self.appsrc.link(videoconvert)
        videoconvert.link(shmsink)

    def write(self, frame):
        self.frame = frame

    def start(self):
        self.thread.start()

    def __need_data__(self, bus, msg):
        try:
            while self.frame is None:
                time.sleep(0.001)

            data = cv2.cvtColor(self.frame, cv2.COLOR_BGR2YUV_I420).tostring()
            buf = Gst.Buffer.new_wrapped(data)
            self.appsrc.emit("push-buffer", buf)
        except StopIteration:
            self.appsrc.emit("end-of-stream")

    def __run_pipeline__(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        bus = self.pipeline.get_bus()
        bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS
        )
        self.pipeline.set_state(Gst.State.NULL)


class GStreamerEngineWriter(Engine):
    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        engine_exec: str = DEFAULT_EXEC,
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
        repeat_frames: bool = False,
    ):
        self.writer = GStreamerWriter(socket_path, repeat_frames)
        super().__init__(socket_path, engine_exec, video_size)
        self.writer.start()

    def write_frame(self, frame):
        """
        Write a frame into the engine. Call in a tight loop, you need to hit your given framerate!

        :param frame: Frame to write to shared memory.
        """
        self.writer.write(frame)
