# StaSh - Shell Like an Expert in Pythonista
Inspired by
[shellista](http://omz-forums.appspot.com/pythonista/post/5302343285342208) and
its variants, [StaSh](https://github.com/ywangd/stash) is a serious attempt to
implement a Bash-like shell for [Pythonista](http://omz-software.com/pythonista/).

Since its initial release, valuable contributions and advices have been received
constantly from the Pythonista community (especially from
[@briarfox](https://github.com/briarfox),
[@dgelessus](https://github.com/dgelessus),
[@jsbain](https://github.com/jsbain), [@pudquick](https://github.com/pudquick)
and [@oefe](https://github.com/oefe)).

StaSh stands for Pythoni**sta** **Sh**ell. While **Sta** may not be the best
abbreviation for Pythonista, it forms a concise and meaningful word with the
following **Sh** part. So the name StaSh was chose to indicate it is a confined
environment and great treasures may be found within.

## Notable Features
StaSh has a pile of features which are to be expected from a real shell. These
features are what really set the difference from shellista.

* **Panel UI** program that is completely event driven. This means:
    * **No blocking thread**, builtin interactive prompt is accessible at all time
    * Almost all scripts can be called from within StaSh, including programs
      using UI and **Scene** packages. You can even launch another
      **panel** UI program and the new UI will simply replace StaSh (not really
      a good use case but it is possible).
    * Being a pure UI program, it is possible to launch and forget. The program
      **stays active indefinitely**. Non-UI scripts can only run for 10 minuntes
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
    * A UI button, "Tab", is provided to enable command line auto-completion.
    * It is clever to auto-completes either commands or files based on the
      input position
    * It also completes environment variables and aliases.
    * It also features a sub-command auto-completion system. For an example,
      type `git sta` and press `Tab`. It will auto-completes to `git status `.
      You can easily add your own sub-commands completion via a JSON file.

* Customisable **virtual keys for commonly used symbols**, e.g. `~/.-*|>`.
    * The Symbols can be customized via the `VK_SYMBOLS` option in
      stash config file (default is `.stash_config`).

* **Command line history** management. Three UI buttons are provided to navigate
  through the history.

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

* The UI can be configured via **configuration file** to customize its font
  size and color. The default config file is `.stash_config` under StaSh
  installation root.

* **Easy self update** by running a single `selfupdate` command from within the
  shell.
    - The `selfupdate` script manages StaSh installation folder and may delete
      files in the process. It is therefore recommend to **not** put your own
      scripts under `$STASH_ROOT/bin`. Instead, save your own scripts
      in`~/Documents/bin` or customise the locations with `BIN_PATH` environment
      variable. 
    - Self-update defaults to the master branch. To update from a different
      branch, e.g. the **dev** branch, run **`SELFUPDATE_BRANCH=dev
      selfupdate`**
    - You may need to restart StaSh after the update.

* Input request from scripts being executed can be terminated by **Ctrl-D
  (C-D)** button.

* StaSh employs Python threads to execute scripts. It maintains a stack of
  threads that forms a family of **linear** threads. This means no parallel
  **foreground** threads are allowed. You can use the **Ctrl-C (C-C)** button
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


## Installation
The code is hosted on GitHub (https://github.com/ywangd/stash). 

A gist file is also provided as a single file installation
(https://gist.github.com/ywangd/7fbb2c1aa17e8734defd).

### Single File Installation with Gist
* Either use the [New from
  Gist](https://gist.github.com/omz/b0644f5ed1d94bd32805) script or simply
  copy/paste to get the gist file, `getstash.py`, at
  https://gist.github.com/ywangd/7fbb2c1aa17e8734defd
* Run `getstash.py` to download the minimal sets of files for StaSh. The files
  will be downloaded and saved in a folder named **stash** under your document
  root.
* Run **stash.py** to launch StaSh (Note the Shell is not yet fully installed at this step).
* In the terminal, type and run `selfupdate` to retrieve rest of the
  files. 

### Install from GitHub
If you have a GitHub tool available in Pythonista, such as
[gitview](http://omz-forums.appspot.com/pythonista/post/5810965861892096) or
[gitrepo](http://omz-forums.appspot.com/pythonista/post/5795611756462080),
simply clone or download the repository.

## Usage
The usage of StaSh is in principle similar to Bash. A few things to note are:

* The search paths for executable scripts is set via an environment variable
  called `BIN_PATH` as `PATH` is used by the system. The default `BIN_PATH` is
  `~/Documents/bin:$STASH_ROOT/bin`.

* The executable files are either Python scripts or StaSh scripts, with `.py`
  and `.sh` extensions respectively. Note the extensions are important as StaSh
  relies on them to tell the file type and whether the file is executable. 
  * When
  Invoking a script, you can omit the extension, StaSh will try find the file
  with one of the extensions. For an example, StaSh interprets the command
  `selfupdate` and find the file `selfupdate.sh` to execute.
  * Note a file without extension is considered as a shell script. It just
    won't show up as an auto-completion possibility.

* Command can only be written in a single line. No line continuation is
  available. However, multiple commands can be written in a single line by
  separating them with semicolons, e.g. `ls -1 > file_list; cat file_list`.

* There are many Python scripts provided along with StaSh (special thanks to
  [@briarfox](https://github.com/briarfox),
  [@dgelessus](https://github.com/dgelessus) and
  [@jsbain](https://github.com/jsbain). These scripts range from performing
  regular shell tasks to advanced terminal utilities like `ssh`. Note the
  scripts are by no means complete when compared to a real Linux shell. The
  scripts will be gradually expanded should the need arise. It is also expected
  and appreciated that the community would come up with more scripts.
    * `alias.py`
    * `cat.py`
    * `cd.py`
    * `cls.py`
    * `copy.py` - Copy to iOS clipboard
    * `cp.py`
    * `cut.py` - Cut out selection portions of each line of a file
    * `echo.py`
    * `edit.py` - Open any text type files in Pythonista editor
    * `env.py`
    * `find.py` - Powerful file searching tool
    * `git.py` - Git client ported from shellista
    * `grep.py`
    * `httpserver.py` - A simple HTTP server with upload function (ripped from
      https://gist.github.com/UniIsland/3346170)
    * `ls.py`
    * `mail.py` - Send emails with optional file attachment
    * `man.py` - Show help message (docstring) of a given command
    * `md5sum.py` - Print or check MD5 checksums
    * `mkdir.py`
    * `mv.py`
    * `openin.py` - Show the **open in** dialog to open a file in external apps.
    * `paste.py` - Paste from iOS clipboard
    * `pip.py` - Search, download, install, update and uninstall pure Python
      packages from PyPI.
    * `printenv.py` - List environment variables
    * `printhex.py` - Print hexadecimal dump of the given file 
    * `pwd.py`
    * `python.py` - Run python scripts or modules
    * `quicklook.py` - iOS quick look for files of known types
    * `rm.py`
    * `scp.py` - Copy files from/to remote servers. 
    * `scsm.py` - An attempt to build an Index and client for managing StaSh
      command scripts
    * `sha1sum.py` - Print of check SHA1 checksums
    * `sha256sum.py` - Print of check SHA256 checksums
    * `sort.py`
    * `source.py` - Evaluate a script in the current environment
    * `ssh.py` - SSH client to either execute a command or spawn an interactive
      session on remote servers. [pyte](https://github.com/selectel/pyte) is
      used for terminal emulation and gives the command the feel of a
      full-fledged SSH client. 
    * `ssh-keygen.py` - Generate RSA/DSA SSH Keys.
    * `tar.py` - Manipulate archive files
    * `touch.py` - Update timestamp of the given file or create it if not exist
    * `uniq.py`
    * `unzip.py`
    * `version.py` - Show StaSh installation and version information
    * `wc.py` - Line, word, character counting
    * `wget.py`
    * `which.py` - Find the exact path to a command script
    * `xargs.py` - Command constructing and executing utility
    * `zip.py`

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
* The terminal flickers up and down a bit while output texts are being rolled
  out. This is caused by the incorrect value of `content_size` reported by the
  UI system. If you know a way to fix it, please let me know.
* Rotating the device sometimes makes the input textfield barely visible.
  Restart the shell to fix it.
* Executing a script using the "Run" button while StaSh is running leads to
  corrupted namespaces and leaves StaSh unusable. However, running scripts from
  "Action Menu" is OK.
    - This is because Pythonista clears all global variables before running a
      script. This is the default behaviour and can be turned off in
      "Interpreter Options" in settings.
* Pickled objects are not restored correctly and generate `AttributeError` as
  if the class definition cannot be found. An example is the
  [DropboxSync](https://gist.github.com/freekrai/4183134) script.


## Contributing
* Check any open issues or open a new issue to start discussions about your
  ideas of features and/or bugs
* Fork the repository, make changes, and send pull requests 
    - Please send pull requests to the **dev** branch instead of master



