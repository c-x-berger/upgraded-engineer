import abc
import shlex
import subprocess
import threading
import time
from typing import Tuple, List

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # isort:skip

DEFAULT_EXEC_PATH = "/usr/bin/rusty-engine"
DEFAULT_SOCKET_PATH = "/tmp/engineering"
DEFAULT_VIDEO_SIZE = (320, 240, 30)
DEFAULT_EXEC = shlex.split(
    "{e} -w {w} -h {h} -f {f} -d {sock} --input shmem".format(
        e=DEFAULT_EXEC_PATH,
        w=DEFAULT_VIDEO_SIZE[0],
        h=DEFAULT_VIDEO_SIZE[1],
        f=DEFAULT_VIDEO_SIZE[2],
        sock=DEFAULT_SOCKET_PATH,
    )
)


def launchline(exec_: str, size: Tuple[int, int, int], socket: str):
    return shlex.split(
        "{exec_} -w {w} -h {h} -f {f} -d {sock} --input shmem".format(
            exec_=exec_, w=size[0], h=size[1], f=size[2], sock=socket,
        )
    )


class Engine:
    """
    Class which starts and manages a rusty-engine process.
    """

    def __init__(
        self, launch: List[str] = DEFAULT_EXEC,
    ):
        """
        Constructor.
        
        :param launch: Absolute path to the compiled rusty-engine binary.
        """
        self.launch = launch
        self.process: subprocess.Popen = None

    def start(self):
        """
        Start the rusty-engine process.
        """
        self.process = subprocess.Popen(self.launch)

    def stop(self):
        """
        Stop the rusty-engine process, potentially destroying the socket.
        """
        if self.process is not None:
            self.process.terminate()


class EngineWriter(Engine, metaclass=abc.ABCMeta):
    """
    Provides easy access to a shared memory socket and starts an Engine.
    """

    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
        autostart: bool = True,
    ):
        """
        Constructor.

        :param socket_path: The filesystem path to the shared memory socket.
        :param video_size: Tuple of video dimensions.
        :param autostart: If True, the start method will be immediately called.
        """
        super().__init__(launchline(DEFAULT_EXEC_PATH, video_size, socket_path))
        self.socket, self.size, self.autostart = socket_path, video_size, autostart
        if self.autostart:
            self.start()

    @abc.abstractmethod
    def write_frame(self, frame):
        """
        Write a frame into the engine. Call in a tight loop, you need to hit your given framerate!

        :param frame: Frame to write to shared memory.
        """
        pass


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


class GStreamerEngineWriter(EngineWriter):
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
        video_size: Tuple[int, int, int] = DEFAULT_VIDEO_SIZE,
        repeat_frames: bool = False,
        autostart: bool = True,
    ):
        super().__init__(socket_path, video_size, autostart)
        self.writer = GStreamerWriter(socket_path, video_size, repeat_frames)
        self.writer.start()

    def write_frame(self, frame):
        """
        Write a frame into the engine. Call in a tight loop, you need to hit your given framerate!

        :param frame: Frame to write to shared memory.
        """
        self.writer.write(frame)

    def stop(self):
        """
        Close the rusty-engine process and stop the GStreamer pipeline.
        """
        super().stop()
        self.writer.loop.quit()
