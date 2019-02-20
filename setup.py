import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="python-logging-loki",
    version="0.1.0",
    description="Python logging handler for Grafana Loki.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    author="Andrey Maslov",
    author_email="greyzmeem@gmail.com",
    url="https://github.com/greyzmeem/python-logging-loki",
    packages=setuptools.find_packages(),
    python_requires=">=3.5",
    install_requires=["rfc3339", "requests"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Logging",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
