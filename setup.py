import setuptools
import re

# hacky way of reading version from __init__
# stolen from discord.py
version = ""
with open("engine/__init__.py") as f:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE
    ).group(1)

if not version:
    raise RuntimeError("version is not set")

with open("README.md", "r") as fh:
    long_desc = fh.read()

setuptools.setup(
    name="upgraded-engineer",
    version=version,
    author="Caleb Xavier Berger",
    author_email="caleb.x.berger@gmail.com",
    description='Python "API" for interacting with rusty-engine',
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/opensight-cv/upgraded-engineer",
    packages=["engine"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
