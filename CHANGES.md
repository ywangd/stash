# Change Log #

### Version 0.2.0 - 2014-12-31
* More bin commands added 
    - `ssh.py` - SSH client to either execute a command or spawn an interactive
      session on remote servers. [pyte](https://github.com/selectel/pyte) is
      used for terminal emulation and gives the command the feel of a
      full-fledged SSH client. 
    - `scp.py` - Copy files from/to remote servers. 
    - `ssh-keygen.py` - Generate RSA/DSA SSH Keys.
    - `man.py` - Show help message (docstring) of a given command
    - `httpserver.py` - A simple HTTP server with upload function (ripped from
      https://gist.github.com/UniIsland/3346170)
    - `edit.py` - Open any text type files in Pythonista editor
    - `openin.py` - Show the **open in** dialog to open a file in external apps.
    - `quicklook.py` - iOS quick look for files of known types
    - `touch.py` - Update timestamp of the given file or create it if not exist
    - `source.py` - Evaluate a script in the current environment
    - `python.py` - run python scripts or modules
    - `which.py` - Find the exact path to a command script
    - `printhex.py` - Print hexadecimal dump of the given file 
    - `version.py` - Show StaSh installation and version information
* Existing bin commands changes
    - `env.py` - Replaced by `printenv.py` (`env` is now an alias to `printenv`)
    - `bh.py` - Removed. `/dev/null` is accessible in StaSh
    - `selfupdate.sh` - The GitHub branch to retrieve can now be customized via
      environment variable `SELFUPDATE_BRANCH` (default is `master`)
* Added virtual keys for commonly used symbols, e.g. `~/.-*|>`
    - The keys can be customized with `VK_SYMBOLS` option in `.stash_config`
* Parser is redesigned and optimized. It should be more efficient and faithful
  to Bash in some edge cases.
* Runtime is optimized to make clear sub-shell emulation, especially on 
  variable and environment passing between shells of different levels. 
    - Shell scripts can now access arguments with special environment variables
      (`$0`, `$1`, ..., `$#`, `$@`)
    - Exit status is now available as `$?`
    - Multi-line shell scripts are now executed in a single thread for improved
      efficiency
* Background jobs are now allowed by appending an ampersand at the end of a
  command, e.g. `httpserver &`.
    - Background jobs are executed in Pythonista main thread and can be
      terminated by tap the close button on the interactive prompt panel. This
      enables a script to perform housekeeping tasks recieving the
      `KeyboardInterrupt` exception. An example is the `httpserver` command. It
      releases the binding port when terminated and allows subsequent calls to
      the same command without restarting Pythonista.
* Auto-completion enhanced
* Command line history management enhanced
* Various bug fixes

### Version 0.1.0 - 2014-12-10
* initial release

