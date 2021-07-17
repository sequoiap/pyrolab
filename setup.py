# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
PyroLab

A framework for using remote lab instruments as local resources, built on Pyro5.
"""

import io
import sys

import setuptools

# ==============================================================================
# Constants
# ==============================================================================
NAME = "PyroLab"
LIBNAME = "pyrolab"

# ==============================================================================
# Auxiliary functions
# ==============================================================================
extra_files = []
extra_files += ["*.ini"]

# ==============================================================================
# Use README for long description
# ==============================================================================
with io.open("README.md", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

# ==============================================================================
# Setup arguments
# ==============================================================================
setup_args = dict(
    name=NAME,
    version="0.2.0",
    author="Sequoia Ploeg",
    maintainer="Sequoia Ploeg",
    maintainer_email="sequoia.ploeg@byu.edu",
    url="https://github.com/BYUCamachoLab/pyrolab",
    description="A framework for using remote lab instruments as local resources built on Pyro5",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    # download_url=__website_url__ + "",
    license="GPLv3+",
    keywords="laboratory instrumentation hardware science remote network integration",
    platforms=["Windows", "Linux", "Mac OS-X"],
    packages=setuptools.find_packages(),
    package_data={"": extra_files},
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.7",
)

install_requires = [
    "Pyro5",
    "deprecation",
    "numpy",
    "scipy",
    "appdirs",
]

extras_require = {
    "tsl550": ["pyserial",],
    "oscope": ["pyvisa", "pyvisa-py",],
    # "kinesis": ["thorlabs-kinesis",],
    "test": ["pytest",],
}

if "setuptools" in sys.modules:
    setup_args["install_requires"] = install_requires
    setup_args["extras_require"] = extras_require


# ==============================================================================
# Main setup
# ==============================================================================
setuptools.setup(**setup_args)
