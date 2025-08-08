# -*- coding: utf-8 -*-
"""Create or update StaSh action shortcut"""

from pathlib import Path
import pythonista_add_action as actions

_stash = globals()["_stash"]


def _err(msg):
    print(_stash.text_style(f"{msg}\n", {"color": "red", "traits": ["bold"]}))


def _info(msg):
    print(_stash.text_style(f"{msg}\n", {"color": "green"}))


def _warn(msg):
    print(_stash.text_style(f"{msg}\n", {"color": "yellow"}))


def _input(msg):
    print(_stash.text_style(f"{msg}", {"color": "cyan"}), end="")
    return input()


def create_or_update_action_stash(force_overwrite: bool = False) -> None:
    """
    Creates or updates a shortcut for the 'stash' script in Pythonista's action menu.
    """
    stash_action = {
        "scriptName": "site-packages/stash/__main__.py",
        "title": "StaSh",
        "iconColor": "58C37D",
        "iconName": "pythonista",
        # "resetEnvironment": 1,
        # "arguments": "stash"
    }

    script_path = stash_action["scriptName"]
    full_script_path = Path("~").expanduser() / "Documents" / script_path
    should_overwrite = False

    if not full_script_path.exists():
        _err(f"Error: The 'stash' script was not found at {full_script_path}.")
        return

    try:
        current_actions = actions.get_actions()
        script_names = [str(action["scriptName"]) for action in current_actions]

        if script_path in script_names:
            _warn("Warning: A 'StaSh' shortcut already exists.")
            if not force_overwrite:
                overwrite = _input("Do you want to overwrite it? [yes/no]: ").lower()
                if overwrite in {"yes", "y"}:
                    should_overwrite = True
                else:
                    _warn("Exiting: The 'StaSh' shortcut will not be updated.")
                    return
            else:
                should_overwrite = True

        if should_overwrite:
            _warn("Warning: The 'StaSh' shortcut will be updated.")
            print("* Removing existing shortcut...")
            index_to_remove = script_names.index(script_path)
            actions.remove_action_at_index(index_to_remove)
            print("* Existing shortcut removed.")

        print("* Creating new shortcut...")
        actions.add_action(**stash_action)
        actions.save_defaults()
        _info("Success: New 'StaSh' shortcut created.")

    except Exception as e:
        _err(f"Error: An error occurred: {e}")


if __name__ == "__main__":
    import argparse

    pa = argparse.ArgumentParser(
        "pinstash", description="Create or update StaSh action shortcut"
    )
    pa.add_argument(
        "-f", "--force", action="store_true", help="Force overwrite of shortcut"
    )
    args = pa.parse_args()
    create_or_update_action_stash(args.force)
