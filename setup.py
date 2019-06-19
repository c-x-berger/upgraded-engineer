import setuptools

with open("README.md", "r") as fh:
    long_desc = fh.read()

setuptools.setup(
    name="upgraded-engineer",
    version="0.0.1.5",
    author="Caleb Xavier Berger",
    author_email="caleb.x.berger@gmail.com",
    description='Python "API" for interacting with team 3494\'s potential-engine',
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/homebrew-limelight/upgraded-engineer",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
