"""
Test color support
"""

_stash = globals()["_stash"]

def get_all_bg_colors():
    """
    Return a list of all known bg colors
    """
    return _stash.renderer.BG_COLORS.keys()


def get_all_fg_colors():
    """
    Return a list of all known fg colors
    """
    return _stash.renderer.FG_COLORS.keys()


def main():
    """
    The main function
    """
    print("============ COLOR TEST ===================")
    bg_colors = get_all_bg_colors()
    fg_colors = get_all_fg_colors()
    print("------------ available colors -------------")
    print("Known FG colors: " + ", ".join(fg_colors))
    print("Known BG colors: " + ", ".join(bg_colors))
    print("------- showing all combinations ----------")
    for fg in stash.renderer.FG_COLORS:
        for bg in stash.renderer.BG_COLORS:
            for bold in (False, True):
                for italics in (False, True):
                    for underscore in (False, True):
                        for strikethrough in (False, True):
                            for reverse in (False, True):
                                traits = []
                                if bold:
                                    traits.append("bold")
                                if italics:
                                    traits.append("italic")
                                if underscore:
                                    traits.append("underline")
                                if strikethrough:
                                    traits.append("strikethrough")
                                desc = "{}-{}{}{}".format(fg, bg, ("-" if len(traits) > 0 else ""), "-".join(traits))
                                s = _stash.text_style(
                                    desc,
                                    dict(
                                        color=fg,
                                        bgcolor=bg,
                                        traits=traits,
                                        )
                                    )
                                print(s)
    print("================= Done =====================")


if __name__ == "__main__":
    main()
