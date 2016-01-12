# StaSh - Shell Like an Expert in Pythonista
**NOTE: This is a legacy version mainly for Pythonista 1.5.**

Inspired by
[shellista](http://omz-forums.appspot.com/pythonista/post/5302343285342208) and
its variants, [StaSh](https://github.com/ywangd/stash) is a serious attempt to
implement a Bash-like shell for [Pythonista](http://omz-software.com/pythonista/).

Since its initial release, valuable contributions and advices have been received
constantly from the Pythonista community.
The two most popular utilities are 
**pip** (authored by [@briarfox](https://github.com/briarfox)) and 
**git** (authored by [@jsbain](https://github.com/jsbain)). 
Remarkable contributions are also made by
[@dgelessus](https://github.com/dgelessus),
[@pudquick](https://github.com/pudquick),
[@oefe](https://github.com/oefe), 
[@cclauss](https://github.com/cclauss) and
[@georg.viehoever] (https://github.com/GeorgViehoever).

StaSh stands for Pythoni**sta** **Sh**ell. While **Sta** may not be the best
abbreviation for Pythonista, it forms a concise and meaningful word with the
following **Sh** part. So the name StaSh was chose to indicate it is a confined
environment and great treasures may be found within.


## Installation
StaSh can be installed easily via a single line of python commands (courtesy of
@whitone). Simply copy and paste the following line into Pythonista interactive
prompt and run.

```Python
import urllib2; exec urllib2.urlopen('http://j.mp/gs0_4').read()
```

The above command installs StaSh to a folder named **stash** under your
document root, i.e. `~/Documents/stash`.

(If you have a GitHub tool available in Pythonista, such as
[gitview](http://omz-forums.appspot.com/pythonista/post/5810965861892096) or
[gitrepo](http://omz-forums.appspot.com/pythonista/post/5795611756462080),
you can choose to directly clone or download the
[repository](https://github.com/ywangd/stash).)


## Notable Features
StaSh has a pile of features which are to be expected from a real shell. These
features are what really set the difference from shellista.

* **Panel UI** program that is completely event driven
    * **No blocking thread**, builtin interactive prompt is accessible at all time
    * Consistent look and feel as a proper PC terminal
    * Almost all scripts can be called from within StaSh, including programs
      using UI and **Scene** packages. You can even launch another
      **panel** UI program and the new UI will simply replace StaSh (not really
      a good use case but it is possible).
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
    * Bang(!) to search command history, e.g. `ls -1`, `!l`. Bang commands like
      `!!` and `!-1` also works.

* Smart **auto-completion** just as expected
    * One UI button, "Tab", is provided to enable command line auto-completion.
    * It is smart to auto-completes either commands or files based on the
      **cursor** position
    * It also completes environment variables and aliases.
    * It also features a sub-command auto-completion system. For an example,
      type `git sta` and press `Tab`. It will auto-completes to `git status `.
      You can easily add your own sub-commands completion via JSON files.

* **Command line history** management. Three UI buttons are provided to navigate
  through the history.

* **On-screen virtual keys** - an extra row of keys on top of the on-screen
  keyboard to provide control functions and easier access to symbols
    * Virtual keys for control functions including:
        * **Tab** - command line auto-completion
        * **CC** (Ctrl-C) - terminate the running job
        * **CD** (Ctrl-D) - end of Input
        * **CU** (Ctrl-U) - kill line
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
	* **Tab** key for auto-completion
	* **⌘ (cmd) + up (↑) / down (↓)** for navigating through command history

* You can **run almost any regular python scripts** from within StaSh 
    * There is no need to customize them for the shell. If it can be executed by
      a python interpreter via `python your_script.py`, you can just call it from
      within StaSh by just typing `your_script`
    * The shell object is made available to scripts being called. This enables a
      range of complex interactions between the shell and called scripts.

* You can give it a **resource file**, similar to `.bashrc`, to customize its
  behaviour. Like the Bash resource file, aliases, environment
  variables can be set here. The default resource file is `.stashrc` under
  StaSh installation root.
    * The prompt is customizable with the `PROMPT` environment variable.
        * `\w` - current working directory with HOME folder abbreviated as `~`
        * `\W` - last path component of current working directory
        * All other strings are displayed literally
        * The default setting is `PROMPT='[\W]$ '`

* **Easy self update** to keep update with the development by running a single
  `selfupdate` command from within the shell.
    - The `selfupdate` script manages StaSh installation folder and may delete
      files in the process. It is therefore recommend to **not** put your own
      scripts under `$STASH_ROOT/bin`. Instead, save your own scripts
      in`~/Documents/bin` or customise the locations with `BIN_PATH` environment
      variable. 
    - Self-update defaults to the master branch. To update from a different
      branch, e.g. the **dev** branch, run **`SELFUPDATE_BRANCH=dev
      selfupdate`**
    - You may need to restart StaSh after the update.

* The UI can be configured via **configuration file** to customize its font
  size and color. The default config file is `.stash_config` under StaSh
  installation root.

* StaSh employs Python threads to execute scripts. It maintains a stack of
  threads that forms a family of **linear** threads. This means no parallel
  **foreground** threads are allowed. You can use the **Ctrl-C (CC)** button
  to terminate running foreground threads at (almost) any time.

* Number of **background** jobs (appending commands with the `&` directive) are
  not limited and will be executed in Pythonista main thread, i.e. the same
  thread of the interactive prompt.
  - Background job and StaSh foreground job can run simultaneously.
  - Pythonista automatically queues background jobs so only one of them will
      be executed at a given time.
  - Background jobs can be terminated by tap the close button on the
      interactive prompt panel. This enables a script to perform housekeeping
      tasks after catching the `KeyboardInterrupt` exception. An example is the
      `httpserver` command. It releases the binding port when terminated and
      allows subsequent calls to the same command without restarting Pythonista.


## Usage
The usage of StaSh is in principle similar to Bash. A few things to note are:

* The search paths for executable scripts is set via an environment variable
  called `BIN_PATH` as `PATH` is used by the system. The default `BIN_PATH` is
  `~/Documents/bin:$STASH_ROOT/bin`.

* The executable files are either Python scripts or StaSh scripts. The type of
  script is determined by looking at the file extensions ".py" and ".sh".
  A file without extension is considered a  shell script.
  * When invoking a script, you can omit the extension, StaSh will try find the file
  with one of the extensions. For an example, StaSh interprets the command
  `selfupdate` and find the file `selfupdate.sh` to execute.
  * Files without extension won't show up as an auto-completion possibility.

* Command can only be written in a single line. No line continuation is
  available. However, multiple commands can be written in a single line by
  separating them with semicolons, e.g. `ls -1 > file_list; cat file_list`.

* There are many Python scripts provided along with StaSh (special thanks to
  [@briarfox](https://github.com/briarfox),
  [@dgelessus](https://github.com/dgelessus) and
  [@jsbain](https://github.com/jsbain)). These scripts range from performing
  regular shell tasks to advanced utilities like `ssh` and `git`. Note the
  scripts are by no means complete when compared to a real Linux shell. The
  script collection will be gradually expanded should the need arise. It is
  also expected and appreciated that the community would come up with more
  scripts.
    * `alias.py` - Define or print aliases
    * `cat.py` - Print contents of file
    * `cd.py` - Change current directory
    * `clear.py` - Clear console
    * `cp.py` - Copy file
    * `crypt.py` - File encryption using AES in CBC mode
    * `cut.py` - Cut out selection portions of each line of a file
    * `echo.py` - Output text to console
    * `edit.py` - Open any text type files in Pythonista editor
    * `find.py` - Powerful file searching tool
    * `git.py` - Git client ported from shellista
    * `grep.py` - search contents of file(s)
    * `httpserver.py` - A simple HTTP server with upload function (ripped from
      https://gist.github.com/UniIsland/3346170)
    * `ls.py` - List files
    * `mail.py` - Send emails with optional file attachment
    * `man.py` - Show help message (docstring) of a given command
    * `md5sum.py` - Print or check MD5 checksums
    * `mkdir.py` - Create directory
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

* One StaSh script, `selfupdate.sh`, is provided to download the latest zip from
  GitHub and extract it locally to update corresponding files. 
    * It is a script formed by a few lines of commands as an example of StaSh
      script.
    * It is a very simple script in that it just naively performs the download
      and extraction without checking timestamps or versions.


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
* Executing a script using the "Run" button while StaSh is running leads to
  corrupted namespaces and leaves StaSh unusable. However, running scripts from
  "Action Menu" is OK.
    - This is because Pythonista clears all global variables before running a
      script. This is the default behaviour in Pythonista v1.5 and can be 
      turned off in "Interpreter Options" in settings.
    - In current Pythonista v1.6 beta, it is no longer possible to turn off
      the "global clearing" feature. To allow StaSh survive through the clearing,
      please run StaSh using the provided `launch_stash.py` script.
* Pickled objects are not restored correctly and generate `AttributeError` as
  if the class definition cannot be found. An example is the
  [DropboxSync](https://gist.github.com/freekrai/4183134) script.


## Contributing
* Check any open issues or open a new issue to start discussions about your
  ideas of features and/or bugs
* Fork the repository, make changes, and send pull requests 
    - Please send pull requests to the **dev** branch instead of master




