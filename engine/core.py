import shlex
import subprocess
import threading
import time
from typing import Tuple

import cv2
import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # isort:skip

DEFAULT_SOCKET_PATH = "/tmp/engineering"
DEFAULT_EXEC = "/usr/bin/rusty-engine"
DEFAULT_VIDEO_SIZE = (640, 480, 30)


class Engine:
    """
    Class which starts and manages a rusty-engine process.
    """

    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        engine_exec: str = DEFAULT_EXEC,
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
    ):
        """
        Constructor. Starts a new rusty-engine process.
        
        :param socket_path: Location to create the shared memory socket at.
        :param engine_exec: Absolute path to the compiled rusty-engine binary. 
        :param video_size: Tuple of video dimensions (width, height, framerate)
        """
        launchline = "{exec_} -w {w} -h {h} -f {f} -d {sock} --input shmem".format(
            exec_=engine_exec,
            w=video_size[0],
            h=video_size[1],
            f=video_size[2],
            sock=socket_path,
        )
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
    """
    Constructor. Starts a GStreamer pipeline.
    
    :param socket_path: Location to create the shared memory socket at.
    :param video_size: Tuple of video dimensions (width, height, framerate)
    :param repeat_frames: False if a new frame must be acquired before streaming continues.
    """

    def __init__(
        self,
        socket_path: str,
        video_size: Tuple[int, int, int],
        repeat_frames: bool = False,
    ):
        self.thread = threading.Thread(target=self.__run_pipeline__)
        self.frame = None
        self.repeat_frames = repeat_frames
        self.end = False

        Gst.init(None)
        self.pipeline = Gst.Pipeline.new(None)
        self.loop = GLib.MainLoop()

        appsrc_caps = Gst.Caps.from_string(
            "video/x-raw,format=BGR,width={w},height={h},framerate={f}/1".format(
                w=video_size[0], h=video_size[1], f=video_size[2]
            )
        )
        capsfilter_caps = Gst.Caps.from_string("video/x-raw,format=I420")
        self.appsrc = Gst.ElementFactory.make("appsrc")
        self.videoconvert = Gst.ElementFactory.make("videoconvert")
        self.capsfilter = Gst.ElementFactory.make("capsfilter")
        self.shmsink = Gst.ElementFactory.make("shmsink")

        self.appsrc.connect("need-data", self.__need_data__)
        self.appsrc.set_property("caps", appsrc_caps)
        self.appsrc.set_property("is-live", True)
        self.capsfilter.set_property("caps", capsfilter_caps)
        self.shmsink.set_property("socket-path", socket_path)
        self.shmsink.set_property("wait-for-connection", False)

        self.pipeline.add(self.appsrc)
        self.pipeline.add(self.videoconvert)
        self.pipeline.add(self.capsfilter)
        self.pipeline.add(self.shmsink)

        self.appsrc.link(self.videoconvert)
        self.videoconvert.link(self.capsfilter)
        self.capsfilter.link(self.shmsink)

    def write(self, frame):
        self.frame = frame

    def start(self):
        self.thread.start()

    def __need_data__(self, bus, msg):
        try:
            while self.frame is None:
                if self.end:
                    return
                time.sleep(0.001)

            buf = Gst.Buffer.new_wrapped(self.frame.tostring())
            self.appsrc.emit("push-buffer", buf)

            if not self.repeat_frames:
                self.frame = None

        except StopIteration:
            self.appsrc.emit("end-of-stream")

    def __run_pipeline__(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        bus = self.pipeline.get_bus()
        self.loop.run()
        self.end = True
        self.pipeline.set_state(Gst.State.NULL)


class GStreamerEngineWriter(Engine):
    """
    Constructor for pure-GStreamer implementation.
    
    :param socket_path: Location to create the shared memory socket at.
    :param engine_exec: Absolute path to the compiled rusty-engine binary. 
    :param video_size: Tuple of video dimensions (width, height, framerate)
    :param repeat_frames: False if a new frame must be acquired before streaming continues.
    """

    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        engine_exec: str = DEFAULT_EXEC,
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
        repeat_frames: bool = False,
    ):
        self.writer = GStreamerWriter(socket_path, video_size, repeat_frames)
        super().__init__(socket_path, engine_exec, video_size)
        self.writer.start()

    def write_frame(self, frame):
        """
        Write a frame into the engine. Call in a tight loop, you need to hit your given framerate!

        :param frame: Frame to write to shared memory.
        """
        self.writer.write(frame)

    def end(self):
        """
        Close the rusty-engine process and stop the GStreamer pipeline.
        """
        self.process.terminate()
        self.writer.loop.quit()
