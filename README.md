# StaSh - Shell Like an Expert in Pythonista
Inspired by
[shellista](http://omz-forums.appspot.com/pythonista/post/5302343285342208) and
its variants, [StaSh](https://github.com/ywangd/stash) is a serious attempt to
implement a Bash-like shell for [Pythonista](http://omz-software.com/pythonista/).

Since its initial release, valuable contributions and advices have been received
constantly from the Pythonista community. 
The two most popular utilities are 
**`pip`** (authored by [@briarfox](https://github.com/briarfox))
 and **`git`** (authored by [@jsbain](https://github.com/jsbain)). 
Remarkable contributions are also made by
[@dgelessus](https://github.com/dgelessus),
[@pudquick](https://github.com/pudquick),
[@oefe](https://github.com/oefe), 
[@cclauss](https://github.com/cclauss),
[@georg.viehoever](https://github.com/GeorgViehoever),
[@BBOOXX](https://github.com/BBOOXX),
[@bennr01](https://github.com/stars/bennr01) and
[@glider-gun](https://github.com/glider-gun). 

StaSh stands for Pythoni**sta** **Sh**ell. While **Sta** may not be the best
abbreviation for Pythonista, it forms a concise and meaningful word with the
following **Sh** part. So the name StaSh was chosen to indicate it is a confined
environment and great treasures may be found within.


## Installation
**StaSh can be easily installed via one line of python command**
(courtesy of [@whitone](https://forum.omz-software.com/user/whitone)). 
```Python
import requests as r; exec(r.get('https://bit.ly/get-stash').text)
```
Simply copy the above line, paste into Pythonista interactive prompt and
execute. It installs StaSh as a Python module under the `site-packages` 
folder (`~/Documents/site-packages/stash`) and copies **a launching script, 
`~/Documents/launch_stash.py`** for easy access.

*StaSh works with both Pythonista 2 and 3. Though it always runs with the
Python 2 interpreter, there is no need to change your default interpreter setting
thanks to [the shebang line](http://omz-software.com/pythonista/docs/ios/new.html)
in the launch script*

*If you have previous versions of StaSh installed (e.g. v0.4.x), 
You may need to restart Pythonista BEFORE the installation.*

*If you have a GitHub tool available in Pythonista, such as
[gitview](http://omz-forums.appspot.com/pythonista/post/5810965861892096) or
[gitrepo](http://omz-forums.appspot.com/pythonista/post/5795611756462080),
you can choose to directly clone or download the
[repository](https://github.com/ywangd/stash).*

*StaSh requires Pythonista v2.0 as the new ObjC feature is heavily used. For
older Pythonista 1.5 compatible version, please refer to the
[v0.4](https://github.com/ywangd/stash/tree/v0.4) branch.*


## Upgrade
Once StaSh is installed, it can be easily updated by running the `selfupdate`
command from within the shell. 
* `selfupdate` defaults to the `master` branch. To update from a different
  branch, e.g. `dev`, use `selfupdate dev`.
* By default, `selfupdate` compares local and remote versions and only performs
  update if newer version is found. You can however force the update without
  version checking via `selfupdate -f`.
* To check for newer version without actually install it, use `selfupdate -n`.
* `selfupdate` manages StaSh installation folder and may delete files in the
  process. It is therefore recommended to **not** place your own scripts under
  `$STASH_ROOT/bin`. Instead, save your own scripts in`~/Documents/bin` or
  customise the locations with the `BIN_PATH` environment variable. 
* You may need to restart Pythonista after the update for changes to take full
  effects.

*selfupdate cannot be used for version 0.4.x and under. A fresh
[installation](#installation) is needed.*

## Notable Features
StaSh has a pile of features that are expected from a real shell. These
features are what really set the difference from shellista.

* **Panel UI** program that is completely event driven
    * **No blocking thread**, builtin interactive prompt is accessible at all time
    * Consistent look and feel as a proper PC terminal
    * Almost all scripts can be called from within StaSh, including programs
      using UI and **Scene** packages.
    * **Attributed text (color and style) support**
    * Multiple sessions are possible by opening additional Panel tabs
    * Being a pure UI program, it is possible to launch and forget. The program
      **stays active indefinitely**. Non-UI scripts can only run for 10 minutes
      in background. But StaSh can stay up forever (till memory runs out due to
      other Apps). You can just launch StaSh to run a few commands and leave it.
      It will still be there for you when you return later.
	
* **Comprehensive** command line parsing and handling using
  [pyparsing](http://pyparsing.wikispaces.com)
    * Environmental variables, e.g `echo $HOME`, `NAME=value`
    * Aliases, e.g. `alias l1='ls -1'`
    * Single and double quotes behave like Bash, e.g. `"*"` means literal `*`,
      `"$HOME"` expands while `'$HOME'` does not.
    * Backslash escaping, e.g. `ls My\ Script.py`
    * Glob, e.g. `ls ~/*.py`
    * **Backtick quotes** for subprocess, e.g. ``touch `ls *.py` ``
    * **Pipes** to chain commands, e.g. `find . -name "*.txt" | grep interesting`
    * **IO redirect** (actually just Output redirect), e.g. `ls *.py > py_files.txt`. 
      Input redirect can be achieved by using pipes.
        - It is possible to redirect to the Pythonista builtin console, 
          e.g. `ls > &3`
    * Bang(!) to search command history, e.g. `ls -1`, `!l`. Bang commands like
      `!!` and `!-1` also works.

* Smart **auto-completion** just as expected
    * One UI button, `Tab`, is provided to enable command line auto-completion.
    * It is smart to complete either commands or files based on the
      **cursor** position
    * It also completes environment variables and aliases.
    * It also features a sub-command auto-completion system. For an example,
      type `git sta` and press `Tab`. It will auto-completes to `git status `.
      You can easily add your own sub-commands completion via JSON files.

* **Thread management allows multiple commands running in parallel**
    * One foreground jobs and unlimited number of background jobs can run 
      simultaneously.
    * A foreground job can be stopped by pressing the **CC** button or **Ctrl-C**
      on an external keyboard.
    * A background job is issued by appending an ampersand character (**`&`**)
      at the end of a normal command, e.g. `httpserver &`. It can be terminated
      by the `kill` command using its job ID.
    * A few utilities are provided for thread management. 
        - `jobs` to list current running background jobs.
        - `kill` to kill a running job.
        - `fg` to bring background jobs to foreground
        - `CZ` button (Ctrl-Z) to send a foreground job to background
    
* **Command line history** management. Three UI buttons are provided to navigate
  through the history.

* **On-screen virtual keys** - an extra row of keys on top of the on-screen
  keyboard to provide control functions and easier access to symbols
    * Virtual keys for control functions including:
        * **Tab** - command line auto-completion
        * **CC** (Ctrl-C) - terminate the running job
        * **CD** (Ctrl-D) - end of Input
        * **CU** (Ctrl-U) - kill line
        * **CZ** (Ctrl-Z) - Send current running foreground job to background
        * **KB** - show/hide keyboard
        * **H** - display a popup window to show command history
        * **Up** - recall the previous command in history
        * **Dn** - recall the next command in history
    * Customisable **virtual keys for commonly used symbols**, e.g. `~/.-*|>`.
        * The Symbols can be customized via the `VK_SYMBOLS` option in stash
          config file (default is `.stash_config`).

* **Swipe on the virtual key row to position cursor** (similar to what Pythonista
  builtin editor offers)

* **External keyboard support**
	* Tab key for auto-completion
	* Up (↑) / Down (↓) for navigating through command history
	* Ctrl-A and Ctrl-E to jump to the beginning and end of the input line, 
	  respectively
	* Ctrl-U to erase the input line
	* Ctrl-W to erase one word before cursor
	* Ctrl-L to clear the screen

* You can **run (almost) any regular python scripts** from within StaSh
    * There is no need to customize them for the shell. If it can be executed by
      a python interpreter via `python your_script.py`, you can just call it from
      within StaSh by just typing `your_script`
    * The shell object is made available to scripts being called. This enables a
      range of complex interactions between the shell and called scripts.
      For an example, the running script can use the shell object to execute
      more commands, e.g. `_stash('pwd')`.

* You can give it a **resource file**, similar to `.bashrc`, to customize its
  behaviour. Like the Bash resource file, aliases, environment
  variables can be set here. The default resource file is `.stashrc` under
  StaSh installation root (i.e. `~/Documents/site-packages/stash`).
    * The prompt is customizable with the `PROMPT` environment variable.
        * `\w` - current working directory with HOME folder abbreviated as `~`
        * `\W` - last path component of current working directory
        * All other strings are displayed literally
        * The default setting is `PROMPT='[\W]$ '`

* **Easy self update** to keep update with the development by running a single
  `selfupdate` command from within the shell.

* The UI can be configured via **configuration file** to customize its font
  size and color. The default config file is `.stash_config` or `stash.cfg` 
  under StaSh installation root.


## Usage
The usage of StaSh is in principle similar to Bash. A few things to note are:

* The search paths for executable scripts is set via an environment variable
  called `BIN_PATH` as `PATH` is used by the system. The default `BIN_PATH` is
  `~/Documents/bin:$STASH_ROOT/bin`.

* The executable files are either Python scripts or StaSh scripts. The type of
  script is determined by looking at the file extensions ".py" and ".sh".
  A file without extension is considered as a shell script.
  * When invoking a script, you can omit the extension, StaSh will try find the file
  with one of the extensions. For an example, StaSh interprets the command
  `selfupdate` and find the file `selfupdate.py` to execute.
  * Files without extension won't show up as an auto-completion possibility.

* Commands can only be written in a single line. No line continuation is
  possible. However, multiple commands can be written in a single line by
  separating them with semicolons, e.g. `ls -1 > file_list; cat file_list`.

* There are many Python scripts provided along with StaSh. 
  These scripts range from performing
  regular shell tasks to advanced utilities like `ssh` and `git`. Note the
  scripts are by no means complete when compared to a real Linux shell. The
  collection will be gradually expanded should the need arise. It is
  also expected and appreciated that the community would come up with more
  scripts.
    * `alias.py` - Define or print aliases
    * `cat.py` - Print contents of file
    * `cd.py` - Change current directory
    * `clear.py` - Clear console
    * `cp.py` - Copy file
    * `crypt.py` - File encryption using AES in CBC mode
    * `curl.py` - Transfer from an URL
    * `cut.py` - Cut out selection portions of each line of a file
    * `du.py` - Summarize disk usage of the set of FILEs, recursively for directories
    * `echo.py` - Output text to console
    * `edit.py` - Open any text type files in Pythonista editor
    * `find.py` - Powerful file searching tool
    * `fg.py` - Bring a background job to foreground
    * `ftpserver.py` - A simple FTP server
    * `gci.py` - Interface to Python's built-in garbage collector
    * `git.py` - Git client ported from shellista
    * `grep.py` - search contents of file(s)
    * `head.py` - Display first lines of a file
    * `httpserver.py` - A simple HTTP server with upload function (ripped from
      https://gist.github.com/UniIsland/3346170)
    * `jobs.py` - List all jobs that are currently running
    * `kill.py` - Terminate a running job
    * `ls.py` - List files
    * `mail.py` - Send emails with optional file attachment
    * `man.py` - Show help message (docstring) of a given command
    * `mc.py` - Easily work with multiple filesystems (e.g. local and FTP) 
      synchronously.
    * `md5sum.py` - Print or check MD5 checksums
    * `mkdir.py` - Create directory
    * `monkeylord.py` - Manage monkey patches with the goal to make Pythonista more viable
    * `mv.py` - Move file
    * `openin.py` - Show the **open in** dialog to open a file in external apps.
    * `pbcopy.py` - Copy to iOS clipboard
    * `pbpaste.py` - Paste from iOS clipboard
    * `pip.py` - Search, download, install, update and uninstall pure Python
      packages from PyPI.
    * `printenv.py` - List environment variables
    * `printhex.py` - Print hexadecimal dump of the given file 
    * `pwd.py` - Print current directory
    * `python.py` - Run python scripts or modules
    * `quicklook.py` - iOS quick look for files of known types
    * `rm.py` - delete (remove) file
    * `scp.py` - Copy files from/to remote servers. 
    * `selfupdate.py` - Update StaSh from its GitHub repo
    * `sha1sum.py` - Print of check SHA1 checksums
    * `sha256sum.py` - Print of check SHA256 checksums
    * `sort.py` - Sort a list, also see unique
    * `source.py` - Evaluate a script in the current environment
    * `ssh.py` - SSH client to either execute a command or spawn an interactive
      session on remote servers. [pyte](https://github.com/selectel/pyte) is
      used for terminal emulation and gives the command the feel of a
      full-fledged SSH client. 
    * `ssh-keygen.py` - Generate RSA/DSA SSH Keys.
    * `stashconf.py` - Change StaSh configuration on the fly
    * `tail.py` - Print last lines of a FILE.
    * `tar.py` - Manipulate archive files
    * `touch.py` - Update timestamp of the given file or create it if not exist
    * `uniq.py` - Remove duplicates from list, also see sort
    * `unzip.py` - Unzip file, also see zip
    * `version.py` - Show StaSh installation and version information
    * `wc.py` - Line, word, character counting
    * `wget.py` - get data from the net
    * `which.py` - Find the exact path to a command script
    * `wol.py`- Wake on LAN using MAC address for launching a sleeping system
    * `xargs.py` - Command constructing and executing utility
    * `zip.py` - Zip file, also see unzip


## Acknowledgements
* [Pythonista](http://omz-software.com/pythonista/) is a wonderful piece of
  software.
* StaSh is inspired by
  [shellista](http://omz-forums.appspot.com/pythonista/post/5302343285342208)
  and its variants, including
  [ShellistaExt](https://github.com/briarfox/ShellistaExt) and
  [ShellistaUI](https://github.com/transistor1/shellista/tree/dev-modular).
* The UI part of StaSh has its root from ShellistaUI.
* Many of the command scripts, e.g. `ls.py`, `cp.py`, `mv.py`, are taken from
  ShellistaExt with some modifications. 


## Known Issues
* Pickled objects are not restored correctly and generate `AttributeError` as
  if the class definition cannot be found. 


## Contributing
* Check any open issues or open a new issue to start discussions about your
  ideas of features and/or bugs
* Fork the repository, make changes, and send pull requests 
    - Please send pull requests to the **dev** branch instead of master

