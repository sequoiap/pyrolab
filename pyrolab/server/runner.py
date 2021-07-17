
# import atexit
# import importlib
from pyrolab.server.server import Daemon, DaemonGroup

from Pyro5.core import locate_ns
from pyrolab.server.registry import create_unique_resource
# from pyrolab.server.resourcemanager import manager
# from pyrolab.utils.network import get_ip

# TODO: Make this some sort of PyroLab configuration parameter.
# REGISTRY_AUTOSAVE = True

def setup_daemon_group(dg: DaemonGroup):
    from pyrolab.server.configure import srv_profile
    srv_profile.use(dg.server_config)

    import pyrolab.server.server as daemons
    d_cls: Daemon = getattr(daemons, dg.daemon_class)
    daemon = d_cls()

    from pyrolab.server.registry import InstrumentRegistry
    reg = InstrumentRegistry().load()

    ns = locate_ns(host=srv_profile.NS_HOST, port=srv_profile.NS_PORT)

    for instr_name in dg.resources:
        instr_info = reg.get(instr_name)
        obj = instr_info.get_class()
        unique = create_unique_resource(obj, _autoconnect_params=instr_info.connect_params)

        uri = daemon.register(unique)
        print("registering", dg.registered_names[instr_name], "at", uri)
        ns.register(dg.registered_names[instr_name], uri)
    
    return daemon

# def start_default_public_server(ns_host: str, ns_port: int) -> None:
#     """
#     Given the nameserver host and port, gets the public ip address of the
#     local machine and hosts all known resources, registering them with the
#     nameserver.

#     Parameters
#     ----------
#     ns_host : str
#         The hostname of the nameserver.
#     ns_port : int
#         The port of the nameserver.
#     """
#     manager.update_host(get_ip())
#     manager.update_ns(ns_host=ns_host, ns_port=ns_port)
#     manager.launch_all()

# def start_default_local_server(ns_host: str="localhost", ns_port: int=9090) -> None:
#     """
#     Given the nameserver host and port, hosts all known resources on localhost, 
#     registering them with the nameserver.

#     Parameters
#     ----------
#     ns_host : str, optional
#         The hostname of the nameserver (default "localhost").
#     ns_port : int, optional
#         The port of the nameserver (default 9090).
#     """
#     manager.update_host("localhost")
#     manager.update_ns(ns_host=ns_host, ns_port=ns_port)
#     manager.launch_all()

# @atexit.register
# def shutdown_on_exit():
#     log.info("Shutting down all processes in ResourceManager.")
#     manager.shutdown_all()
