# -*- coding: utf-8 -*-
# Copyright © 2020 PyroLab Project Contributors and others (see AUTHORS.txt).
# The resources, libraries, and some source files under other terms (see NOTICE.txt).
#
# This file is part of PyroLab.
#
# PyroLab is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyroLab is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyroLab. If not, see <https://www.gnu.org/licenses/>.

"""
PyroLab
=======

A framework for using remote lab instruments as local resources built on Pyro5 
"""

import pathlib
import platform
import sys

if sys.version_info < (3, 7, 0):
    raise Exception(
        "PyroLab requires Python 3.7+ (version "
        + platform.python_version()
        + " detected)."
    )

__name__ = "PyroLab"
__author__ = "CamachoLab"
__copyright__ = "Copyright 2020, The PyroLab Project"
__version__ = "0.2.0"
__license__ = "GPLv3+"
__maintainer__ = "Sequoia Ploeg"
__maintainer_email__ = "sequoia.ploeg@byu.edu"
__status__ = "Development" # "Production"
__project_url__ = "https://github.com/sequoiap/pyrolab"
__forum_url__ = "https://github.com/sequoiap/pyrolab/issues"
__website_url__ = "https://camacholab.byu.edu/"


import warnings
warnings.filterwarnings("default", category=DeprecationWarning)

# from pyrolab.configure import global_config as config

from appdirs import AppDirs
_dirs = AppDirs(__name__, __author__, version=__version__)
SITE_DATA_DIR = pathlib.Path(_dirs.site_data_dir)
SITE_CONFIG_DIR = pathlib.Path(_dirs.site_config_dir)
SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
SITE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
