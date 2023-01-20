# -*- coding: utf-8 -*-
"""functions and classes related to wheels."""
import os
import shutil
import tempfile
import json
import re
import zipfile
import platform
from io import open

import six
from six.moves import configparser

try:
    from stashutils.extensions import create_command
    from libversion import VersionSpecifier
except ImportError:
    create_command = None
    VersionSpecifier = None


class WheelError(Exception):
    """Error related to a wheel."""
    pass


def parse_wheel_name(filename):
    """
    Parse the filename of a wheel and return the information as dict.
    """
    if not filename.endswith(".whl"):
        raise WheelError("PEP427 violation: wheels need to end with '.whl'")
    else:
        filename = filename[:-4]
    splitted = filename.split("-")
    distribution = splitted[0]
    version = splitted[1]
    if len(splitted) == 6:
        build_tag = splitted[2]
        python_tag = splitted[3]
        abi_tag = splitted[4]
        platform_tag = splitted[5]
    elif len(splitted) == 5:
        build_tag = None
        python_tag = splitted[2]
        abi_tag = splitted[3]
        platform_tag = splitted[4]
    else:
        raise WheelError("PEP427 violation: invalid naming schema")
    return {
        "distribution": distribution,
        "version": version,
        "build_tag": build_tag,
        "python_tag": python_tag,
        "abi_tag": abi_tag,
        "platform_tag": platform_tag,
    }


def escape_filename_component(fragment):
    """
    Escape a component of the filename as specified in PEP 427.
    """
    return re.sub(r"[^\w\d.]+", "_", fragment, re.UNICODE)


def generate_filename(
        distribution,
        version,
        build_tag=None,
        python_tag=None,
        abi_tag=None,
        platform_tag=None,
):
    """
    Generate a filename for the wheel and return it.
    """
    if python_tag is None:
        if six.PY3:
            python_tag = "py3"
        else:
            python_tag = "py2"
    if abi_tag is None:
        abi_tag = "none"
    if platform_tag is None:
        platform_tag = "any"
    return "{d}-{v}{b}-{py}-{a}-{p}.whl".format(
        d=escape_filename_component(distribution),
        v=escape_filename_component(version),
        b=("-" + escape_filename_component(build_tag) if build_tag is not None else ""),
        py=escape_filename_component(python_tag),
        a=escape_filename_component(abi_tag),
        p=escape_filename_component(platform_tag),
    )


def wheel_is_compatible(filename):
    """
    Return True if the wheel is compatible, False otherwise.
    """
    data = parse_wheel_name(filename)
    if ("py2.py3" in data["python_tag"]) or ("py3.py2" in data["python_tag"]):
        # only here to skip elif/else
        pass
    elif six.PY3:
        if not data["python_tag"].startswith("py3"):
            return False
    else:
        if not data["python_tag"].startswith("py2"):
            return False
    if data["abi_tag"].lower() != "none":
        return False
    if data["platform_tag"].lower() != "any":
        return False
    return True


class BaseHandler(object):
    """
    Baseclass for installation handlers.
    """
    name = "<name not set>"

    def __init__(self, wheel, verbose=False):
        self.wheel = wheel
        self.verbose = verbose

    def copytree(self, packagepath, src, dest, remove=False):
        """
        Copies a package directory tree.
        :param packagepath: relative path of the (sub-)package, e.g. 'package/subpackage/'
        :type packagepath: str
        :param src: path to the actual source of the root package
        :type src: str
        :param dest: path to copy to
        :type dest: str
        :return: the path to which the directories have been copied.
        :trype: str
        """
        if self.verbose:
            print("Copying {s} -> {d}".format(s=src, d=dest))
        if os.path.isfile(src):
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(src))
            if os.path.exists(dest) and remove:
                os.remove(dest)
            shutil.copy(src, dest)
            return dest
        else:
            target = os.path.join(
                dest,
                # os.path.basename(os.path.normpath(src)),
                packagepath,
            )
            if os.path.exists(target) and remove:
                shutil.rmtree(target)
            shutil.copytree(src, target)
            return target

    @property
    def distinfo_name(self):
        """the name of the *.dist-info directory."""
        data = parse_wheel_name(self.wheel.filename)
        return "{pkg}-{v}.dist-info".format(
            pkg=data["distribution"],
            v=data["version"],
        )


class TopLevelHandler(BaseHandler):
    """Handler for 'top_level.txt'"""
    name = "top_level.txt installer"

    def handle_install(self, src, dest):
        tltxtp = os.path.join(src, self.distinfo_name, "top_level.txt")
        files_installed = []
        if not os.path.exists(tltxtp):
            files = os.listdir(src)
            fin = [file_name for file_name in files if file_name != self.distinfo_name]
            print('No top_level.txt, try to fix this.', fin)
        else:
            with open(tltxtp, "r") as f:
                fin = f.readlines()
        for pkg_name in fin:
            pure = pkg_name.replace("\r", "").replace("\n", "")
            sp = os.path.join(src, pure)
            if os.path.exists(sp):
                p = self.copytree(pure, sp, dest, remove=True)
            elif os.path.exists(sp + ".py"):
                dp = os.path.join(dest, pure + ".py")
                p = self.copytree(pure, sp + ".py", dp, remove=True)
            else:
                raise WheelError("top_level.txt entry '{e}' not found in toplevel directory!".format(e=pure))
            files_installed.append(p)
        return files_installed


class ConsoleScriptsHandler(BaseHandler):
    """Handler for 'console_scripts'."""
    name = "console_scripts installer"

    def handle_install(self, src, dest):
        eptxtp = os.path.join(src, self.distinfo_name, "entry_points.txt")
        if not os.path.exists(eptxtp):
            if self.verbose:
                print("No entry_points.txt found, skipping.")
            return
        parser = configparser.ConfigParser()
        try:
            parser.read(eptxtp)
        except configparser.MissingSectionHeaderError:
            # print message and return
            if self.verbose:
                print("No section headers found in entry_points.txt, passing.")
                return
        if not parser.has_section("console_scripts"):
            if self.verbose:
                print("No console_scripts definition found, skipping.")
            return

        if create_command is None:
            if self.verbose:
                print("Warning: could not import create_command(); skipping.")
            return

        files_installed = []

        mdp = os.path.join(src, self.distinfo_name, "metadata.json")
        if os.path.exists(mdp):
            with open(mdp, "r") as fin:
                desc = json.load(fin).get("summary", "???")
        else:
            desc = "???"

        for command, definition in parser.items(section="console_scripts"):
            # name, loc = definition.replace(" ", "").split("=")
            modname, funcname = definition.split(":")
            if not command.endswith(".py"):
                command += ".py"
            path = create_command(
                command,
                (
                    u"""'''%s'''
from %s import %s

if __name__ == "__main__":
    %s()
""" % (desc,
            modname,
            funcname,
            funcname)
                ).encode("utf-8")
            )
            files_installed.append(path)
        return files_installed


class WheelInfoHandler(BaseHandler):
    """Handler for wheel informations."""
    name = "WHEEL information checker"
    supported_major_versions = [1]
    supported_versions = ["1.0"]

    def handle_install(self, src, dest):
        wtxtp = os.path.join(src, self.distinfo_name, "WHEEL")
        with open(wtxtp, "r") as fin:
            for line in fin:
                line = line.replace("\r", "").replace("\n", "")
                ki = line.find(":")
                key = line[:ki]
                value = line[ki + 2:]

                if key.lower() == "wheel-version":
                    major, minor = value.split(".")
                    major, minor = int(major), int(minor)
                    if major not in self.supported_major_versions:
                        raise WheelError("Wheel major version is incompatible!")
                    if value not in self.supported_versions:
                        print("WARNING: unsupported minor version: " + str(value))
                    self.wheel.version = (major, minor)

                elif key.lower() == "generator":
                    if self.verbose:
                        print("Wheel generated by: " + value)
        return []


class DependencyHandler(BaseHandler):
    """
    Handler for the dependencies.
    """
    name = "dependency handler"

    def handle_install(self, src, dest):
        metajsonp = os.path.join(src, self.distinfo_name, "metadata.json")
        metadatap = os.path.join(src, self.distinfo_name, "METADATA")
        if not os.path.exists(metajsonp):
            if os.path.exists(metadatap):
                if self.verbose:
                    print("Reading 'METADATA' file...")
                dependencies = self.read_dependencies_from_METADATA(metadatap)
            else:
                if self.verbose:
                    print("Warning: could find neither 'metadata.json' nor `METADATA`, can not detect dependencies!")
                return
        else:
            if self.verbose:
                print("Reading 'metadata.json' file...")
            with open(metajsonp, "r") as fin:
                content = json.load(fin)
            dependencies = []
            for ds in content.get("run_requires", []):
                ex = ds.get("extra", None)
                dep = ds.get("requires", [])
                if ex is not None:
                    if ex not in self.wheel.extras:
                        # extra not wanted
                        continue
                    else:
                        if self.verbose:
                            print("Adding dependencies for extra '{e}'...".format(e=ex))
                        dependencies += dep
                else:
                    dependencies += dep
        self.wheel.dependencies += dependencies

    def read_dependencies_from_METADATA(self, p):
        """read dependencies from distinfo/METADATA"""
        dependencies = []
        with open(p, "r", encoding='utf-8') as fin:
            for line in fin:
                line = line.replace("\n", "")
                if line.startswith("Requires-Dist: "):
                    t = line[len("Requires-Dist: "):]
                    if ";" in t:
                        es = t[t.find(";") + 1:].replace('"', "").replace("'", "")
                        t = t[:t.find(";")].strip()
                        for sub_es in es.split(' and '):
                            if VersionSpecifier is None:
                                # libversion not found
                                print(
                                    "Warning: could not import libversion.VersionSpecifier! Ignoring version and extra dependencies."
                                )
                                rq, v, extras = "<libversion not found>", "???", []
                            else:
                                rq, v, extras = VersionSpecifier.parse_requirement(sub_es)

                            if rq == "python_version":
                                # handle python version dependencies
                                if not v.match(platform.python_version()):
                                    # dependency NOT required
                                    break
                            elif rq == "extra":
                                # handle extra dependencies
                                matched = any([v.match(e) for e in self.wheel.extras])
                                if not matched:
                                    # dependency NOT required
                                    break
                                else:
                                    if self.verbose:
                                        print("Adding dependencies for extras...")
                            elif rq == "platform_python_implementation":
                                if not v.match(platform.python_implementation()):
                                    break
                            elif rq == "platform_system":
                                if v.match(platform.system()):
                                    break
                            elif rq == "sys_platform":
                                if not v.match(sys.platform):
                                    break
                            else:
                                # unknown requirement for dependency
                                # warn user and register the dependency
                                print("Warning: unknown dependency requirement: '{}'".format(rq))
                                print("Warning: Adding dependency '{}', ignoring requirements for dependency.".format(t))
                                # do not do anything here- As long as we dont use 'continue', 'break', ... the dependency will be added.
                        else:
                            # no 'break' happens
                            continue
                        # a 'break' happens, don't add dependencies and go to next 'line'
                        break

                    dependencies.append(t)
        return dependencies


# list of default handlers
DEFAULT_HANDLERS = [
    WheelInfoHandler,
    DependencyHandler,
    TopLevelHandler,
    ConsoleScriptsHandler,
]


class Wheel(object):
    """class for installing python wheels."""

    def __init__(self, path, handlers=DEFAULT_HANDLERS, extras=[], verbose=False):
        self.path = path
        self.extras = extras
        self.verbose = verbose
        self.filename = os.path.basename(self.path)
        self.handlers = [handler(self, self.verbose) for handler in handlers]
        self.version = None  # to be set by handler
        self.dependencies = []  # to be set by handler

        if not wheel_is_compatible(self.filename):
            raise WheelError("Incompatible wheel: {p}!".format(p=self.filename))

    def install(self, targetdir):
        """
        Install the wheel into the target directory.
        Return (files_installed, dependencies)
        """
        if self.verbose:
            print("Extracting wheel..")
        tp = self.extract_into_temppath()
        if self.verbose:
            print("Extraction finished, running handlers...")
        try:
            files_installed = []
            for handler in self.handlers:
                if hasattr(handler, "handle_install"):
                    if self.verbose:
                        print("Running handler '{h}'...".format(h=getattr(handler, "name", "<unknown>")))
                    tfi = handler.handle_install(tp, targetdir)
                    if tfi is not None:
                        files_installed += tfi
        finally:
            if self.verbose:
                print("Cleaning up...")
            if os.path.exists(tp):
                shutil.rmtree(tp)
        return (files_installed, self.dependencies)

    def extract_into_temppath(self):
        """
        Extract the wheel into a temporary directory.
        Return the path of the temporary directory.
        """
        p = os.path.join(tempfile.gettempdir(), "wheel_tmp", self.filename)
        if not os.path.exists(p):
            os.makedirs(p)

        with zipfile.ZipFile(self.path, mode="r") as zf:
            zf.extractall(p)

        return p


if __name__ == "__main__":
    # test script
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Wheel debug installer")
    parser.add_argument("path", help="path to .whl", action="store")
    parser.add_argument("-q", help="be less verbose", action="store_false", dest="verbose")
    parser.add_argument("extras", action="store", nargs="*", help="extras to install")
    ns = parser.parse_args()
    print("Installing {} with extras {}...".format(ns.path, ns.extras))
    fi, dep = Wheel(ns.path, verbose=ns.verbose, extras=ns.extras).install(os.path.expanduser("~/Documents/site-packages/"))
    print("files installed: ")
    print(fi)
    print("dependencies:")
    print(dep)
    if len(dep) > 0:
        print("WARNING: Dependencies were not installed.")