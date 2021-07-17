<p align="center">
<img src="https://raw.githubusercontent.com/sequoiap/pyrolab/master/docs/source/_static/images/pyrolab_logo.svg" width="40%" alt="PyroLab">
</p>

---

<p align="center">
<img alt="Development version" src="https://img.shields.io/badge/master-v0.2.0-informational">
<a href="https://pypi.python.org/pypi/pyrolab"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/pyrolab.svg"></a>
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/pyrolab">
<!-- <a href="https://github.com/BYUCamachoLab/simphony/actions?query=workflow%3A%22build+%28pip%29%22"><img alt="Build Status" src="https://github.com/BYUCamachoLab/simphony/workflows/build%20(pip)/badge.svg"></a> -->
<!-- <a href="https://github.com/pre-commit/pre-commit"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit" style="max-width:100%;"></a> -->
<a href="https://pyrolab.readthedocs.io/"><img alt="Documentation Status" src="https://readthedocs.org/projects/pyrolab/badge/?version=latest"></a>
<a href="https://pypi.python.org/pypi/pyrolab/"><img alt="License" src="https://img.shields.io/pypi/l/pyrolab.svg"></a>
<a href="https://github.com/sequoiap/pyrolab/commits/master"><img alt="Latest Commit" src="https://img.shields.io/github/last-commit/sequoiap/pyrolab.svg"></a>
</p>

A framework for using remote lab instruments as local resources, built on Pyro5.

Developed by Sequoia Ploeg (for [CamachoLab](https://camacholab.byu.edu/), 
Brigham Young University).

## About
This project aims to allow all laboratory instruments to be accessed as
local objects from a remote machine. Instruments that don't natively
support such access, such as those required to be connected by a USB cable
(or similar), are wrapped with a Pyro5 interface. However, this library may
contain other instruments that are already internet-capable and don't rely
on Pyro5. That's alright; we're just trying to create a minimal-dependency,
one-stop-shop for laboratory instruments!

**Note:** while the software says "OS Independent", some of the servers *are*
OS-specific. For example, ThorLabs DLL's only work on Windows. However, you could
use PyroLab to connect to those devices from any operating system.

## Installation

PyroLab is pip installable:

```
pip install pyrolab
```

PyroLab declares several "extras", depending on which instruments you need
to support:

```
pip install pyrolab[tsl550, oscope]
```

The full list of supported extras is:
- tsl550
- oscope

You can also clone the repository, navigate to the toplevel, and install in 
editable mode:

```
pip install -e .
```

## Uninstallation

PyroLab creates data and configuration directories that aren't deleted when
pip uninstalled. You can find their locations by running (before 
uninstallation):

```
import pyrolab
print(pyrolab.SITE_DATA_DIR)
print(pyrolab.SITE_CONFIG_DIR)
```

These folders can be safely deleted after uninstallation.

## Example

### Local Instruments

Locally available instruments just import drivers without using any of the 
other features of PyroLab.

```
from pyrolab.drivers.lasers.tsl550 import TSL550

laser = TSL550("COM4")
laser.on()
laser.power_dBm(12)
laser.open_shutter()
laser.sweep_set_mode(continuous=True, twoway=True, trigger=False, const_freq_step=False)
```

### Remote Instruments

First, make sure all configurations on the nameserver computer, instrument 
server computer, and client are correct (with the proper keys, if configured, 
etc.).

Run a nameserver:

```python
from pyrolab.api import start_ns_loop
start_ns_loop()
```

Provide a service:

```python
from pyrolab.api import Daemon, locate_ns
from pyrolab.drivers.sample import SampleService

daemon = Daemon()
ns = locate_ns(host="localhost")
uri = daemon.register(SampleService)
ns.register("test.SampleService", uri)

try:
    daemon.requestLoop()
finally:
    ns.remove("test.SampleService")
```

Connect using a remote client:

```python
from pyrolab.api import locate_ns, Proxy

ns = locate_ns(host="localhost")
uri = ns.lookup("test.SampleService")

with Proxy(uri) as service:
    resp = service.echo("Hello, server!")
    print(type(resp), resp)
```

## Instrument Server Configuration

PyroLab stores information about instruments and servers when it closes. This
means that once PyroLab has been configured once, each time it is restarted,
it will remember and reload the previous configuration. Hence, once a server
is set up, unless the available instruments, nameserver, or other 
configurations change, PyroLab will automatically work when started, every 
time!

For an example of how a new PyroLab instrument server should be configured the
first time it's run, see ``examples/302.resource-manager/prep.py``.

## FAQ's
1. **Another instrument library? What about all the others?**  
    In our experience, many of the other libraries are buggy or have difficulty
    with network connections. So, our approach was to rely on a well developed
    and time-tested framework (Pyro) instead of worrying about developing and
    supporting our own custom set of servers.

2. **Is this a standalone software that automatically supports all the advertised 
instruments?**  
    No; many of these instruments depend on other software already being
    installed. In particular, ThorLabs equipment depends on ThorLabs software
    already being installed on the computer connected to the physical hardware
    (but not on the remote computer!). As much as possible, though, we try to
    make the drivers standalone capable.

## For Developers
Since the passing of data is, by definition, between hosts and over IP, PyroLab
avoids the use of complex Python objects for return values that will be 
transmitted to remote machines. Since serialization is complicated, and
security is even harder, we resort to using only basic Python types when
interfacing with hardware (i.e., Python lists, ints, tuples, and not NumPy 
arrays, matplotlib plot objects, custom objects, etc.).

To bump version prior to a release, run one of the following commands:

```bash
bumpversion major
bumpversion minor
bumpversion patch
```

Releases are automatically created when git tags matching the "v*" pattern
are created.
