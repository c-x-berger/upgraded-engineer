upgraded-engineer
===
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![PyPI](https://img.shields.io/pypi/v/upgraded-engineer.svg)](https://pypi.org/project/upgraded-engineer/)

`upgraded-engineer` is a Python library for interacting with FRC 3494's [`potential-engine`.](https://github.com/BHSSFRC/potential-engine)

## Installation
`pip install upgraded-engineer`
### Dependencies
* GStreamer (base and bad plugins required for `upgraded-engineer`, more required by `potential-engine`)
* Open CV (known working with >= 4.0.0, must be compiled with GStreamer support)

## Usage
Importing is simple:
```python
import engine
```
To simply start a new `potential-engine` process, create an instance of the `engine.Engine` class. You will have to figure out how to write frames into the shared memory yourself. (Note that `potential-engine` is expecting I420 color, and cannot determine what is being written for itself.)

Alternatively, using `engine.EngineWriter` provides the `write_frame` method to write "normal" Open CV BGR color frames into shared memory for streaming.
```python
ew = engine.EngineWriter()
# alternately, if we wanted smaller video
ew = engine.EngineWriter(video_size=(426, 240, 30)) # width, height, framerate
```
Now, writing frames into shared memory is simple.
```python
def on_new_frame_whenever_that_is_for_you(frame):
    ew.write_frame(frame) # ew.write_frame handles the BGR to I420 conversion automagically
```
