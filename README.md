# StaSh - Shell Like an Expert in Pythonista
Inspired by
[shellista](http://omz-forums.appspot.com/pythonista/post/5302343285342208) and
its variants, [StaSh](https://github.com/ywangd/stash) is a serious attempt to
implement a bash-like shell for [Pythonista](http://omz-software.com/pythonista/).

StaSh behaves more like a real Shell, such as Bash. It is feature rich and
allows users focus on tasks without getting in the way. 

Since the initial release of StaSh, it has recieved valuable and constant
contributions and advices from [@briarfox](https://github.com/briarfox),
[@dgelessus](https://github.com/dgelessus) and
[@jsbain](https://github.com/jsbain). 


## Background
StaSh stands for Pythoni**sta** **Sh**ell. While **Sta** may not be the best
alias for Pythonista, it forms a concise and meaningful word with the following
**Sh** part. So the name StaSh is chosed to indicate it is a confined
environment and awesome treasures could be found within.


## Notable Features
StaSh has a pile of features which are to be expected from a real shell. The
features are also what really set the difference from shellista.

* Panel UI program that is completely event driven. This means:
    * **No blocking thread**, builtin interactive prompt is accessible at all time
    * Almost all scripts can be called from within StaSh, including programs
      using UI and **Scene** packages. In theory, you can even launch another
      **panel** UI program. The new UI will simply replace StaSh.
    * Being a pure UI program, it is possible to launch and forget. The program
      stays active indefinitely. Normal script can only run 10 minuntes in
      background. But StaSh can stay up forever (till memory runs out due to
      other Apps). You can just launch StaSh to run a few commands and leave it.
      It will still be there for you when you return later.

* **Comprehensive** command line parsing and handling using
  [pyparsing](http://pyparsing.wikispaces.com)
    * Environmental variables, e.g $HOME
    * Aliases, e.g. `alias l1='ls -1'; l1`
    * Single and double quotes behave like Bash, e.g. `"*"` means literal `*`,
      `"$HOME"` expands while `'$HOME'` does not.
    * Backslash escaping, e.g. `ls My\ Script.py`
    * Glob, e.g. `ls ~/*.py`
    * **Backtick quotes** for subprocess, e.g. ``l`echo s` `` is the same as `ls`
    * **Pipes** to chain commands, e.g. `cat some_file | grep interesting`
    * **IO redirect** (actually just Output redirect), e.g. `ls *.py > py_files.txt`. 
      Input redirect can be achieved by using pipes.
    * Bang(!) to search command history, e.g. `ls -1`, `!l`. Bang commands like
      `!!` and `!-1` also works.

* Smart **auto-completion** just as expected
    * A UI button, "Tab", is provided to enable command line auto-completion.
    * It is clever to auto-completes either commands or files based on the input
      position
    * It also completes environmental variables and aliases.

* Custmoisable **virtual keys for commonly used symbols**, e.g. `~/.-*|>`.
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
  StaSh's installation root.
    * The prompt is customizable with the `PROMPT` environment variable.
        * `\w` - current working directory with HOME folder abbreviated as `~`
        * `\W` - last path component of current working directory
        * All other strings are displayed literally
        * The default setting is `PROMPT='[\W]$ '`

* The UI can be configured using **configuration file** to customize its font
  size and color. The default config file is `.stash_config` under StaSh's
  installation root.

* Input request from scripts being executed can be terminated by **Ctrl-D
  (C-D)** button.

* StaSh employs Python threads to execute scripts. It maintains a stack of
  threads that forms a family of linear threads. This means no parallel
  **foreground** threads are allowed. You can use the **Ctrl-C (C-C)** button
  to terminate running foreground threads at (almost) any time.

* Number of **background** jobs (appending commands with the `&` directive) are
  not limited and will be executed in Pythonista main thread, i.e. the same
  thread of the interactive prompt.
    * Background job and StaSh foreground job can run simultaneously.
    * Pythonista automatically queues background jobs so only one of them will
      be executed at a given time.
    * Background jobs can be terminated by tap the close button on the
      interactive prompt panel. This enables a script to perform housekeeping
      tasks recieving the `KeyboardInterrupt` exception. An example is the
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
* Run **stash.py** to launch StaSh. 
    * Note the Shell is not yet fully installed at this step.
* In the terminal, type `selfupdate` or `selfupdate.sh` to retrieve rest of the
  files. 

### Install from GitHub
If you have a GitHub tool available in Pythonista, such as [git repo
manager](http://omz-forums.appspot.com/pythonista/post/5810965861892096), simply
clone the repository.

## Usage
The usage of StaSh is in principle similar to Bash. A few things to note are:

* The search paths for executable scripts is set via an environment variable
  called `BIN_PATH` as `PATH` is used by the system. The default `BIN_PATH` is
  `~/Documents/bin:$STASH_ROOT/bin`.

* The executable files are either Python scripts or StaSh scripts, with `.py`
  and `.sh` extensions respectively. Note the extensions are important as StaSh
  relies on them to tell the file type and whether the file is executable. When
  calling the script, you can omit the extensions, StaSh will try find the file
  with one of the extension. For an example, StaSh interprets the command
  `selfupdate` and find the file `selfupdate.sh` to execute.

* Command can only be read from a single line. No line continuation is
  available. However, multiple commands can be written in a single line by
  separating them with semicolons, e.g. `ls -1 > file_list; cat file_list`.

* There are currently 34 Python scripts provided along with StaSh (special
  thanks to @briarfox and @dgelessus for providing many valuable scripts).
  Categories of these scripts range from perfomring regular shell tasks to
  advanced terminal utilities like `SSH`. Note the scripts are by no means
  complete when compared to a real Linux shell. The scripts will be gradually
  expanded should the need arise. It is also expected and appreciated that the
  community would come up with more scripts.
    * `alias.py`
    * `cat.py`
    * `cd.py`
    * `cls.py`
    * `copy.py` - copy to iOS clipboard
    * `cp.py`
    * `echo.py`
    * `edit.py` - Open any text type files in Pythonista editor
    * `env.py`
    * `grep.py`
    * `httpserver.py` - A simple HTTP server with upload function (ripped from
      https://gist.github.com/UniIsland/3346170)
    * `ls.py`
    * `man.py` - Show help message (docstring) of a given command
    * `mkdir.py`
    * `mv.py`
    * `openin.py` - Show the **open in** dialog to open a file in external apps.
    * `paste.py` - paste from iOS clipboard
    * `printenv.py` - list environment variables
    * `printhex.py` - Print hexadecimal dump of the given file 
    * `pwd.py`
    * `python.py` - run python scripts or modules
    * `quicklook.py` - iOS quick look for files of known types
    * `rm.py`
    * `scp.py` - Copy files from/to remote servers. 
    * `sort.py`
    * `source.py` - Evaluate a script in the current environment
    * `ssh.py` - SSH client to either execute a command or spawn an interactive
      session on remote servers. [pyte](https://github.com/selectel/pyte) is
      used for terminal emulation and gives the command the feel of a
      full-fledged SSH client. 
    * `ssh-keygen.py` - Generate RSA/DSA SSH Keys.
    * `touch.py` - Update timestamp of the given file or create it if not exist
    * `uniq.py`
    * `unzip.py`
    * `version.py` - Show StaSh installation and version information
    * `wget.py`
    * `which.py` - Find the exact path to a command script

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
    - Please send pull requests to **dev** branch instead of master



