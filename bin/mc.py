# coding: utf-8
"""easily work with multiple filesystems (e.g. local and FTP) synchronously"""

# the name refers to midnight-commander, but this will probably
# never be a true counterpart
import os
import shutil
import cmd
import sys
import tempfile
import shlex

from stashutils.fsi.errors import OperationFailure, IsDir, IsFile
from stashutils.fsi.errors import AlreadyExists
from stashutils.fsi.interfaces import INTERFACES
from stashutils.fsi.local import LocalFSI

_stash = globals()["_stash"]
Text = _stash.text_color  # alias for cleaner code
"""
TODO:
		-fix mv command still deletes source directoy when file-mv failed (mid prio)
		-fix spelling mistakes in help (low prio)
		-improve documentation (low prio)
		-fix infinite loop when copying a directory into itself
			=> I initialy solved this by  doing a walk before a copy,
				but this was removed as it lead to ugly code
			=>low prio as this script is designed for use with different fs;
				this bug only occurs when using the same fs.
		-make run command transferring file deletions in "w"-mode (low prio)
		-make run command more efficient (only cp file changes) (low prio)
"""

# =====================
# Constants

INTERN_FS_ID = "_<intern>"  # the id used for internal commands
assert " " not in INTERN_FS_ID, "Invalid configuration!"

# ===================
# FSIs


class InternalFSI(LocalFSI):
    """a LocalFSI used by some commands. It only differs in repr."""

    def repr(self):
        return "<Internal FSI>"


# =============================
# utility classes and functions


def modified(path, prev=None):
    """if prev is None, calculates a state to be later passed to modified().
    if prev is such a state,
    modified() will return wether the path has been modified or not."""
    dirs = []
    files = []
    for n in os.listdir(path):
        ap = os.path.join(path, n)
        if os.path.isfile(ap):
            stat = os.stat(ap)
            size = stat.st_size
            mod = stat.st_mtime
            files.append((ap, size, mod))
        else:
            res = modified(ap, prev=None)
            dirs += res[0]
            files += res[1]
    if prev is None:
        return (dirs, files)
    else:
        return prev != (dirs, files)


# =============================
# User-Interface


class McCmd(cmd.Cmd):
    prompt = Text("(mc)", "blue")
    intro = Text(
        "Entering mc's command-loop.\nType 'help' for help and 'exit' to exit.",
        "yellow",
    )
    ruler = Text("=", "yellow")
    use_rawinput = True
    misc_header = "Miscellaneous help topics (unmaintained; see 'man mounting'):"

    def __init__(self):
        cmd.Cmd.__init__(self)
        internal_fsi = InternalFSI(self)
        self.FSIs = {INTERN_FS_ID: internal_fsi}

    def do_connected(self, cmd):
        """prints a list of connected interfaces and their id."""
        if len(self.FSIs.keys()) <= 1:
            self.stdout.write("No Interfaces connected.\n")
        for k in sorted(self.FSIs.keys()):
            if k == INTERN_FS_ID:
                continue
            i = self.FSIs[k]
            name = i.repr()
            self.stdout.write("{k}: {n}\n".format(k=k, n=name))

    def do_exit(self, cmd=""):
        """exit: quits the script."""
        self.stdout.write("closing interfaces... ")
        for k in self.FSIs.keys():
            try:
                self.FSIs[k].close()
            except:
                pass
            del self.FSIs[k]
        self.stdout.write(Text("Done", "green"))
        self.stdout.write(".\ngoodbye!\n")
        sys.exit(0)

    do_EOF = do_quit = do_exit

    def do_connect(self, cmd):
        """connect <id> <type> [args]: opens a new interface."""
        args = shlex.split(cmd)
        if len(args) < 2:
            self.stdout.write(Text("Error: expected at least 2 arguments!\n", "red"))
            return
        ID, name = args[0], args[1]
        if len(args) > 2:
            args_to_pass = tuple(args[2:])
        else:
            args_to_pass = ()
        if ID in self.FSIs:
            self.stdout.write(Text("Error: ID already registered!\n", "red"))
            return
        if name not in INTERFACES:
            self.stdout.write(Text("Error: FSI not found!\n", "red"))
            return
        self.stdout.write("Creating Interface... ")
        fsic = INTERFACES[name]
        fsi = fsic(self.stdout.write)
        self.stdout.write(Text("Done", "green"))
        self.stdout.write(".\nConnecting... ")
        try:
            state = fsi.connect(*args_to_pass)
        except OperationFailure as e:
            self.stdout.write(Text("Error: {e}!\n".format(e=e.message), "red"))
            return
        if state is True:
            self.FSIs[ID] = fsi
            self.stdout.write(Text("Done", "green"))
            self.stdout.write(".\n")
        elif isinstance(state, str):
            self.stdout.write(Text("Error: {e}!\n".format(e=state), "red"))
        else:
            self.stdout.write(
                Text("Error: cannot interpret return-Value of connect()!\n", "red")
            )
            return

    def do_disconnect(self, command):
        """disconnect <interface>: close 'interface'."""
        args = shlex.split(command)
        if len(args) != 1:
            self.stdout.write(Text("Error: expected exactly on argument!\n", "red"))
            return
        ID = args[0]
        if ID not in self.FSIs:
            self.stdout.write(
                Text("Error: ID does not refer to any Interface!\n", "red")
            )
            return
        if ID == INTERN_FS_ID:
            self.stdout.write(Text("Error: cannot close internal FSI!\n", "red"))
            return
        try:
            self.FSIs[ID].close()
        except OperationFailure as e:
            m = e.message
            self.stdout.write(
                Text("Error closing Interface: {m}!\n".format(m=m), "red")
            )
        del self.FSIs[ID]
        self.stdout.write(Text("Interface closed.\n", "green"))

    def do_shell(self, command):
        """shell <command>: run 'command' in shell"""
        if _stash is not None:
            _stash(command)
        else:
            p = os.popen(command)
            content = p.read()
            code = p.close()
            self.stdout.write(content + "\n")
            self.stdout.write(Text("Exit status: {s}\n".format(s=code), "yellow"))

    def do_cd(self, command):
        """cd <interface> <dirname>: change path of 'interface' to 'dirname'."""
        fsi, name = self.parse_fs_command(command, nargs=1)
        if (fsi is None) or (name is None):
            return
        if name == "..":
            isdir = True
        else:
            try:
                isdir = fsi.isdir(name)
            except:
                isdir = True
                # lets just try. It worked before isdir() was added so it should still work
        if not isdir:
            self.stdout.write(Text("Error: dirname does not refer to a dir!\n", "red"))
            return
        try:
            fsi.cd(name)
        except IsFile:
            self.stdout.write(Text("Error: dirname does not refer to a dir!\n", "red"))
        except OperationFailure as e:
            self.stdout.write(Text("Error: {m}\n".format(m=e.message), "red"))

    def do_path(self, command):
        """path <interface>: shows current path of 'interface'."""
        fsi, name = self.parse_fs_command(command, nargs=0)
        if (fsi is None) or (name is None):
            return
        try:
            self.stdout.write(fsi.get_path() + "\n")
        except OperationFailure as e:
            self.stdout.write(Text("Error: {m}\n".format(m=e.message), "red"))

    do_cwd = do_pwd = do_path

    def do_ls(self, command):
        """ls <interface>: shows the content of the current dir of 'interface'."""
        fsi, name = self.parse_fs_command(command, nargs=0)
        if (fsi is None) or (name is None):
            return
        try:
            content = fsi.listdir()
        except OperationFailure as e:
            self.stdout.write(Text("Error: {m}\n".format(m=e.message), "red"))
        else:
            self.stdout.write("  " + "\n  ".join(content) + "\n")

    do_dir = do_ls

    def do_rm(self, command):
        """rm <interface> <name>: removes file/dir 'name'."""
        fsi, name = self.parse_fs_command(command, nargs=1)
        if (fsi is None) or (name is None):
            return
        self.stdout.write("Removing... ")
        try:
            fsi.remove(name)
        except OperationFailure as e:
            self.stdout.write(Text("Error: {m}\n".format(m=e.message), "red"))
        else:
            self.stdout.write(Text("Done", "green"))
            self.stdout.write(".\n")

    do_del = do_remove = do_rm

    def do_mkdir(self, command):
        """mkdir <interface> <name>: creates the dir 'name'."""
        fsi, name = self.parse_fs_command(command, nargs=1)
        if (fsi is None) or (name is None):
            return
        self.stdout.write("Creating dir... ")
        try:
            fsi.mkdir(name)
        except OperationFailure as e:
            self.stdout.write(Text("Error: {m}\n".format(m=e.message), "red"))
        else:
            self.stdout.write(Text("Done", "green"))
            self.stdout.write(".\n")

    def do_cp(self, command):
        """cp <ri> <rf> <wi> <wn>: copy file 'rf' from 'ri' to file 'wf' on 'wi'."""
        args = shlex.split(command)
        if len(args) != 4:
            self.stdout.write(Text("Error: invalid argument count!\n", "red"))
            return
        rfi, rfp, wfi, wfp = args
        if wfi == rfi:
            self.stdout.write(
                Text("Error: can only copy between different interfaces!", "red")
            )
        if (rfi not in self.FSIs) or (wfi not in self.FSIs):
            self.stdout.write(Text("Error: Interface not found!\n", "red"))
            return
        rfsi = self.FSIs[rfi]
        wfsi = self.FSIs[wfi]
        isfile = rfsi.isfile(rfp)
        isdir = rfsi.isdir(rfp)
        if isfile:
            self.stdout.write("Copying file '{n}'...\n".format(n=rfp))
            try:
                self.stdout.write("   Opening infile... ")
                rf = rfsi.open(rfp, "rb")
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n   Opening outfile... ")
                wf = wfsi.open(wfp, "wb")
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n   Copying... ")
                while True:
                    data = rf.read(4096)
                    if len(data) == 0:
                        break
                    wf.write(data)
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n")
            except IsDir:
                self.stdout.write(Text("Error: expected a filepath!\n", "red"))
                return
            except OperationFailure as e:
                self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
                return
            finally:
                self.stdout.write("   Closing infile... ")
                try:
                    rf.close()
                    self.stdout.write(Text("Done", "green"))
                    self.stdout.write(".\n")
                except Exception as e:
                    self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
                self.stdout.write("   Closing outfile... ")
                try:
                    wf.close()
                    self.stdout.write(Text("Done", "green"))
                    self.stdout.write(".\n")
                except Exception as e:
                    self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n")
        elif isdir:
            crp = rfsi.get_path()
            cwp = wfsi.get_path()
            rfsi.cd(rfp)
            if not (wfp in wfsi.listdir() or wfp == "/"):
                self.stdout.write("Creating dir '{n}'... ".format(n=wfp))
                try:
                    wfsi.mkdir(wfp)
                except AlreadyExists:
                    pass
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n")
            wfsi.cd(wfp)
            try:
                content = rfsi.listdir()
                for fn in content:
                    subcommand = '{rfi} "{name}" {wfi} "{name}"'.format(
                        rfi=rfi, name=fn, wfi=wfi
                    )
                    self.do_cp(subcommand)
            except OperationFailure as e:
                self.stdout.write(Text("Error: {e}!\n".format(e=e.message), "red"))
                return
            finally:
                rfsi.cd(crp)
                wfsi.cd(cwp)
        else:
            self.stdout.write(Text("Error: Not found!\n", "red"))
            return

    do_copy = do_cp

    def do_mv(self, command):
        """mv <ri> <rf> <wi> <wn>: move file 'rf' from 'ri' to file 'wf' on 'wi'."""
        args = shlex.split(command)
        if len(args) != 4:
            self.stdout.write(Text("Error: invalid argument count!\n", "red"))
            return
        rfi, rfp, wfi, wfp = args
        if (rfi not in self.FSIs) or (wfi not in self.FSIs):
            self.stdout.write(Text("Error: Interface not found!\n", "red"))
            return
        if wfi == rfi:
            self.stdout.write(
                Text("Error: can only move between different interfaces!", "red")
            )
        rfsi = self.FSIs[rfi]
        wfsi = self.FSIs[wfi]
        isdir = rfsi.isdir(rfp)
        isfile = rfsi.isfile(rfp)
        if isfile:
            self.stdout.write("Moving file '{n}'...\n".format(n=rfp))
            try:
                self.stdout.write("   Opening file to read... ")
                rf = rfsi.open(rfp, "rb")
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n   Opening file to write... ")
                wf = wfsi.open(wfp, "wb")
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n   Copying... ")
                while True:
                    data = rf.read(4096)
                    if len(data) == 0:
                        break
                    wf.write(data)
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n")
            except IsDir:
                self.stdout.write(Text("Error: expected a filepath!\n", "red"))
                return
            except OperationFailure as e:
                self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
                return
            finally:
                self.stdout.write("   Closing infile... ")
                try:
                    rf.close()
                    self.stdout.write(Text("Done", "green"))
                    self.stdout.write(".\n")
                except Exception as e:
                    self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
                self.stdout.write("   Closing outfile... ")
                try:
                    wf.close()
                    self.stdout.write(Text("Done", "green"))
                    self.stdout.write(".\n")
                except Exception as e:
                    self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
                    return
                self.stdout.write("   Deleting Original... ")
                try:
                    rfsi.remove(rfp)
                except OperationFailure as e:
                    self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
                else:
                    self.stdout.write(Text("Done", "green"))
                    self.stdout.write(".\n")
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n")
        elif isdir:
            crp = rfsi.get_path()
            cwp = wfsi.get_path()
            rfsi.cd(rfp)
            if not (wfp in wfsi.listdir() or wfp == "/"):
                self.stdout.write("Creating dir '{n}'... ".format(n=wfp))
                wfsi.mkdir(wfp)
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n")
            wfsi.cd(wfp)
            try:
                content = rfsi.listdir()
                for fn in content:
                    subcommand = '{rfi} "{name}" {wfi} "{name}"'.format(
                        rfi=rfi, name=fn, wfi=wfi
                    )
                    self.do_mv(subcommand)
                rfsi.cd(crp)
                rfsi.remove(rfp)
            except OperationFailure as e:
                self.stdout.write(Text("Error: {e}!\n".format(e=e.message), "red"))
                return
            finally:
                rfsi.cd(crp)
                wfsi.cd(cwp)
        else:
            self.stdout.write(Text("Error: Not found!\n", "red"))
            return

    do_move = do_mv

    def do_cat(self, command):
        """cat <interface> <file> [-b]: shows the content of target file on 'interface'
        if --binary is specified, print all bytes directly.
        otherwise, print repr(content)[1:-1]
        """
        fsi, args = self.parse_fs_command(command, nargs=-1, ret=tuple)
        if (fsi is None) or (args is None):
            return
        if len(args) == 2:
            if args[1] in ("-b", "--binary"):
                # never print nullbytes until explictly told.
                binary = True
            else:
                self.stdout.write(Text("Error: Unknown read-mode!\n", "red"))
                return
            name, binary = args[0], binary
        elif len(args) not in (1, 2):
            self.stdout.write(Text("Error: invalid argument count!\n", "red"))
            return
        else:
            name, binary = args[0], False
        self.stdout.write("Reading file... ")
        try:
            f = fsi.open(name, "r" + ("b" if binary else ""))
            content = f.read()
        except IsDir:
            self.stdout.write(Text("Error: expected a filepath!\n", "red"))
        except OperationFailure as e:
            self.stdout.write(Text("Error: {m}\n".format(m=e.message), "red"))
        else:
            self.stdout.write(Text("Done", "green"))
            self.stdout.write(".\n")
            if not binary:
                content = repr(content)[1:-1]
            self.stdout.write(Text("=" * 25, "yellow"))
            self.stdout.write("\n{c}\n".format(c=content))
            self.stdout.write(Text("=" * 25, "yellow"))
            self.stdout.write("\n")
        finally:
            try:
                f.close()
            except:
                pass

    def do_run(self, command):
        """run <ID> <F> <MODE> <CMD> [ARGS [ARGS...]]: download F and execute CMD on it
        run understands the '*' filename.
        MODE should be either 'r' or 'w'. 'r' only downloads the files,
        'w' additionally uploads the files if they have been modified."""
        rfsi, args = self.parse_fs_command(command, nargs=-1, ret=tuple)
        if (rfsi is None) or (args is None):
            return
        rid = shlex.split(command)[0]
        if len(args) < 3:
            self.stdout.write(Text("Error: invalid argument count!\n", "red"))
            return
        mode = args[1]
        remotepath = args[0]
        # orgpath = remotepath
        if not (rfsi.isfile(remotepath) or remotepath == "*"):
            self.stdout.write(
                Text("Error: to download a whole directory use '*'.\n", "red")
            )
            return
        if mode not in ("r", "R", "w", "W"):
            self.stdout.write(Text("Error: Unknown mode!\n", "red"))
            return
        lfsi = self.FSIs[INTERN_FS_ID]
        shellcommand = " ".join(args[2:])
        self.stdout.write("Creating tempdir... ")
        localpath = os.path.join(tempfile.gettempdir(), "stash_mc_run")
        if os.path.exists(localpath):
            shutil.rmtree(localpath)
        os.mkdir(localpath)
        self.stdout.write(Text("Done", "green"))
        self.stdout.write(".\n")
        op = os.getcwd()
        if remotepath == "*":
            remotepath = rfsi.get_path()
            cd_path = None
        else:
            cd_path = localpath
        try:
            lfsi.cd(localpath)
            splitted = remotepath.split("/")
            if len(splitted) >= 2:
                lfp = splitted[-2]
            else:
                lfp = remotepath
            while lfp.startswith("/"):
                lfp = lfp[1:]
            if lfp == "":
                lfp = "exec"
            rawcpcmd = '{ri} "{rp}" {li} "{lfp}"'
            self.do_cp(rawcpcmd.format(ri=rid, rp=remotepath, lfp=lfp, li=INTERN_FS_ID))
            if mode in ("w", "W"):
                self.stdout.write("Scanning content... ")
                oldstate = modified(localpath, prev=None)
                self.stdout.write(Text("Done", "green"))
                self.stdout.write(".\n")
            if cd_path is None:
                cd_path = os.path.join(localpath, os.listdir(localpath)[0])
            self.do_shell('cd "{p}"'.format(p=cd_path))
            self.do_shell(shellcommand)
        except Exception as e:
            self.stdout.write(Text("Error: {e}!\n".format(e=e.message), "red"))
            return
        else:
            try:
                if mode in ("w", "W"):
                    self.stdout.write("Checking for content modification... ")
                    moded = modified(localpath, prev=oldstate)
                    self.stdout.write(Text("Done", "green"))
                    self.stdout.write(".\nContent modified: {m}\n".format(m=moded))
                    if moded:
                        self.stdout.write("Copying modifified content... \n")
                        if lfp == "exec":
                            tp = "/"
                        else:
                            tp = remotepath
                        if os.path.isfile(lfp):
                            if tp != "/":
                                if tp.endswith("/"):
                                    tp = tp[:-1]
                                tp = "/".join(tp.split("/")[:-1])
                            lfp = lfsi.get_path()
                            if lfp.endswith("/"):
                                lfp = lfp[1:]
                            lfsi.cd(lfp)
                            lfp = lfp.split("/")[-1]
                        rawcpcmd = '{li} "{lfp}" {ri} "{tp}"'
                        cpcmd = rawcpcmd.format(lfp=lfp, ri=rid, tp=tp, li=INTERN_FS_ID)
                        self.do_cp(cpcmd)
                        self.stdout.write(Text("Copying finished.\n", "green"))
                else:
                    pass
            except Exception as e:
                self.stdout.write(Text("Error: {m}!\n".format(m=e.message), "red"))
        finally:
            self.stdout.write("Cleaning up... ")
            self.do_shell('cd "{p}"'.format(p=op))
            try:
                shutil.rmtree(localpath)
            except:
                pass
            self.stdout.write(Text("Done", "green"))
            self.stdout.write(".\n")

    def parse_fs_command(self, command, nargs=0, ret=str):
        """parses a filesystem command. returns the interface and the actual command.
        nargs specifies the number of arguments, -1 means any number."""
        args = shlex.split(command)
        if len(args) < 1 or (len(args) != nargs + 1 and nargs != -1):
            self.stdout.write(Text("Error: invalid argument count!\n", "red"))
            return None, None
        i = args[0]
        if i not in self.FSIs:
            self.stdout.write(Text("Error: Interface not found!\n", "red"))
            return None, None
        if ret is str:
            if len(args) > 1:
                args = " ".join(args[1:])
            else:
                args = ""
        elif ret is tuple:
            args = args[1:]
        else:
            raise ValueError("Unknown return type!")
        fsi = self.FSIs[i]
        return fsi, args

    def help_usage(self, *args):
        """prints help about the usage."""
        help = """USAGE
===============
This guide describes how to use mc.

1.) using filesystem
	First, you need to connect to a filesystem.
	Use the 'connect'-command for this.
	Usage:
		connect <id> <fsi-name> [args [args ...]]

		'id' is a number used to identify the connection in commands.
			The ID 0 should not be used, as it is used internally.
		'fsi-name' is the name of the FSI you want to use (e.g. 'local').
		'args' is passed to the FSI and may contain server, username...
	Example:
		connect 1 local
			>opens the local filesystem.
			>you can later use this filesystem by passing 1 to commands.
		connect 2 ftp ftp.example.org 21 YourName YourPswd -s
			>connects to FTP-server ftp.example.org on port 21
			>switch over to SFTP
			>login as YourName with YourPswd
			>you can later use this filesystem by passing 2 to commands.
	If you want to get a list of connected filesystems, use 'connected'.
	If you want to disconnect, use disconnect <id>.
	If you want to get a list of aviable FSIs, use help fsis.
	If you want to see help on a FSI, use help fsi_<name>
2.) Using commands
	After you are connected, you can use any aviable command.
	To get a list of aviable commands, type '?' or 'help'.
	To see the Usage of a command, use 'help <command>'.
3.) Quitting
	To quit, use the 'exit' command.
4.) Tips
	You can run shell commands while using mc:
		!echo test
		shell python
5.) Additional Info
	-mc does not transfer file deletions when running a command on the remote fs
	-mc may behave weird in subdirs
"""
        self.stdout.write(help + "\n")

    def help_troubleshooting(self, *args):
        """shows help on troubleshooting"""
        av = """TROUBLESHOOTING
==================

I get the Error "to download a whole directory use '*'." when
trying to copy a file:
	-Check that the path refers to a file.
	-Check that the file exists.
My files arent updated in "w" mode:
	-only files you downloaded are updated.
		If you want to update other files, download the whole dir with '*' as path.
	-mc does not transfer file deletions (at the moment)
I dont know how to use FSI XXX:
	-see '!man mounting(5)'
I dont know how to use mc:
	-see 'help usage'
I dont know how to use command XXX:
	-see 'help XXX'
Running a command in a subdir on the remote filesystem behaves weirdly:
	-this is a bug
I dont know how to quit the command loop:
	-use 'exit' or 'quit'
I cant copy/move/... a file with a space in its name:
	-use something like 'cp 1 "name with space" 1 "some othrr name with spaces"'
I cant copy/move a directory on the same interface:
	-this is because mc is designed to be flexible and only
	require a minimal API to the target filesystem.
		Due to this, there is no real working directory but the interface
			keep track of the CWD.
		While this is very flexible, it prevents the cp/mv-commands to
			work on the same interface.
		You can fix this by creating a second interface with the same
			dir and copy/move between them instead.
"""
        sys.stdout.write(av + "\n")

    help_helpme = help_troubleshooting

    def help_fsis(self, *args):
        """shows a list of aviable FSIs"""
        self.do_shell("man mounting(5)")

    def help_remote_run(self, *args):
        """shows help on running commands on remote"""
        av = """Help on running remote commands:
	mc offers the the ability to run commands on the remote filesystem.
	It does so by doing the following:
		1) download files into a temorary folder
		2) scan files
		3) cd into the temporary folder
		4) run the command
		5) cd back
		6) scan for differences between the files in the folder and
			the data collected in 2)
		7) upload the files
		8) remove the tempdir
	The actions 2,6 and 7 are only done in "w"-mode (more about this later).

	HOW TO RUN A COMMAND REMOTELY
		You do this by using the 'run' command.
		USAGE:
			run <ID> <FILENAME> <MODE> <COMMAND> [ARGS [ARGS...]]

			'ID': the interface to use.
			'FIlENAME': which file to download. Passing a dir *should* work.
				Passing "*" downloads the current dir.
			'MODE': How to handle the files. Possible values:
				"r" or "R": only download the files. Changes will be discarded.
				"w" or "W": download the files and upload the changes after
					the command has been executed.
			'COMMAND' and 'ARGS':
				passed to the shell-subcommand.
		INFO:
			Currently, file deletions are never transferred, regardless of mode.

			In "w"-mode, only previously downloaded files are uploaded.
			(You can simple use '*' as a path)

			At the moment, there is a bug when trying to run a script in
				a dir which is not the current dir (e.g. tests/test.py).
			However, you can simply cd into the target dir and run the
				script from there.
"""
        self.stdout.write(av + "\n")


if __name__ == "__main__":
    McCmd().cmdloop()
