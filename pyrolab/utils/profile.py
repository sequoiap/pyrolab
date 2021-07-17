# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

import pathlib
from pyrolab.utils.configure import Configuration
import shutil
from typing import Any, Type, Union

from yaml import safe_load, dump


class Profile:
    """
    A profile, to be used as a singleton for easily managing  different 
    configurations.
    """
    __slots__ = [
        'name', 'configuration', '_base_dir', '_suffix'
    ]

    def __init__(self, base_dir: Union[str, pathlib.Path], suffix: str, config: Type[Configuration]):
        self._base_dir = pathlib.Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._suffix = suffix

        self.name = 'default'
        self.configuration = config()
        self.save(overwrite=True)

    def __str__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__name__} '{self.name}'>"

    def __getattr__(self, name: str):
        if name in self.__slots__:
            return getattr(self, name)
        else:
            return getattr(self.configuration, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.__slots__:
            super().__setattr__(name, value)
        else:
            self.configuration.__setattr__(name, value)

    def _get_profile_path(self, name):
        """
        Returns the default profile path for a given profile name.
        """
        return (self._base_dir / name).with_suffix(self._suffix)

    def use(self, cfg: Union[str, Configuration]):
        """
        Switches current configuration to use a given profile.

        Parameters
        ----------
        cfg : str or Configuration
            The configuration to use. If a string, looks for the named 
            configuration in the saved configuration directory. If a 
            Configuration object, creates a "temp" configuration using the 
            given Configuration.
        """
        if isinstance(cfg, Configuration):
            self.name = 'temp'
            self.configuration = cfg
        elif type(cfg) is str:
            profile = self._get_profile_path(cfg)
            if profile.exists():
                with profile.open('r') as fin:
                    dictionary = safe_load(fin)
                    self.name = cfg
                    self.configuration = self.configuration.from_dict(dictionary)

    def add(self, name, configuration):
        """
        Adds a profile given a name and configuration.
        """
        profile = self._get_profile_path(name)
        if profile.exists():
            raise Exception(f"profile '{name}' already exists!")
        else:
            with profile.open('w') as fout:
                fout.write(dump(configuration.to_dict()))

    def delete(self, name):
        """
        Deletes a profile by name.
        """
        profile = self._get_profile_path(name)
        if profile.exists():
            profile.unlink()
        else:
            raise Exception(f"profile '{name}' does not exist!")

    def list(self):
        """
        Lists all installed profiles.

        Returns
        -------
        list of str
            The names of all installed nameserver profiles.
        """
        return [path.stem for path in self._base_dir.glob(f'*{self._suffix}')]

    def save(self, overwrite: bool=False) -> bool:
        """
        Updates the current (modified) profile.

        Parameters
        ----------
        overwrite : bool, optional
            If the profile exists, it is overwritten (default False).
        """
        profile = self._get_profile_path(self.name)
        if profile.exists():
            if not overwrite:
                return False
        with profile.open('w') as fout:
            fout.write(dump(self.configuration.to_dict()))
        return True

    def export(self, name: str, path: Union[pathlib.Path, str]):
        """
        Exports a .profile configuration file to the given path.

        Parameters
        ----------
        name : str
            The name of the profile to be exported.
        path : str, pathlib.Path
            The directory to export the .profile file to.
        """
        path = pathlib.Path(path)
        if not path.is_dir():
            raise Exception(f"destination is not a directory ('{path}')")
        profile = self._get_profile_path(name)
        shutil.copy(profile, path)

    def install(self, name: str, path: Union[pathlib.Path, str]):
        """
        Imports and installs a .profile configuration file. This does not apply
        the imported profile to the current instance; use `use()` to switch
        profiles.

        Parameters
        ----------
        name : str
            The name of the profile being imported.
        path : str, pathlib.Path
            The location of the .profile file to be imported.
        """
        if name in self.list():
            raise Exception(f"profile '{name}' already exists!")
        path = pathlib.Path(path)
        profile = self._get_profile_path(name)
        shutil.copy(path, profile)
