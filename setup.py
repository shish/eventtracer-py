import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="eventtracer-py",
    version="0.0.2",
    author="Shish",
    author_email="webmaster@shishnet.org",
    description="A library for tracing code into the chrome Event Trace format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shish/eventtracer-py",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
