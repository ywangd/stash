# coding: utf-8
"""Opens the given URL in the webbrowser or an App."""
import argparse
import webbrowser
import ui
from objc_util import on_main_thread


@on_main_thread
def open_webbrowser(url, modal=False):
    """opens the url in the webbrowser"""
    webbrowser.open(url, modal)


def open_webview(url, modal=False):
    """opens the url in a view."""
    v = ui.WebView()
    v.present("fullscreen")
    v.load_url(url)
    if modal:
        v.wait_modal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="url to open", action="store")
    parser.add_argument("-m", "--modal", help="wait until the user closed the webbrowser", action="store_true", dest="modal")
    parser.add_argument(
        "-n",
        "--insecure",
        help="prefix the url with http:// instead of https:// if no prefix is given",
        action="store_const",
        const="http://",
        default="https://",
        dest="prefix"
    )
    parser.add_argument("-f", "--foreground", help="Open the url in the foreground", action="store_true", dest="foreground")
    ns = parser.parse_args()
    url = ns.url
    if "://" not in url:
        url = ns.prefix + url
    if not ns.foreground:
        open_webbrowser(url, ns.modal)
    else:
        open_webview(url, ns.modal)
