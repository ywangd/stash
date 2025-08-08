# code: utf-8
"""
Installer program to help install tools registered on the Pythonista Tools GitHub repo.
"""

import os
import sys
import requests
import re
import functools
import shutil
import json
import zipfile

from urllib.parse import urljoin

try:
    import ui
    import console
    import webbrowser
except ImportError:
    import dummyui as ui
    import dummyconsole as console

__version__ = "1.0.0"

INSTALL_PATH_DEFAULT = "bin"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONF_FILE = os.path.join(SCRIPT_DIR, "ptinstaller.conf")


class InvalidGistURLError(Exception):
    pass


class NoFilesInGistError(Exception):
    pass


class GistDownloadError(Exception):
    pass


class GitHubAPI(object):
    API_URL = "https://api.github.com"

    @staticmethod
    def contents(owner, repo):
        r = requests.get(
            urljoin(GitHubAPI.API_URL, "repos/{}/{}/contents".format(owner, repo))
        )
        return r.json()


class PythonistaToolsRepo(object):
    """
    Manage and gather information from the Pythonista Tools repo.
    """

    PATTERN_NAME_URL_DESCRIPTION = re.compile(
        r"^\| *\[([^]]+)\] *(\[([^]]*)\])?[^|]+\| *(.*) *\|", re.MULTILINE
    )
    PATTERN_NAME_URL = re.compile(r"^\[([^]]+)\]: *(.*)", re.MULTILINE)

    def __init__(self):
        self.owner = "Pythonista-Tools"
        self.repo = "Pythonista-Tools"

        self.cached_tools_dict = {}

    def get_categories(self):
        """
        Get URL of all the markdown files that list Pythonista tools of different categories.
        """
        categories = {}
        for content in GitHubAPI.contents(self.owner, self.repo):
            name = content["name"]
            if name.endswith(".md") and name not in ["README.md"]:
                categories[os.path.splitext(name)[0]] = {
                    "url": content["download_url"],
                    "sha": content["sha"],
                }
        return categories

    def get_tools_from_md(self, url_md):
        """
        Retrieve markdown file from the given URL and parse its content to build a dict
        of tools.
        :return:
        """
        # If results are available in the cache, avoid hitting the web
        if url_md not in self.cached_tools_dict:
            md = requests.get(url_md).text
            # Find all script name and its url
            tools_dict = {}
            for name, _, url, description in self.PATTERN_NAME_URL_DESCRIPTION.findall(
                md
            ):
                tools_dict[name] = {"url": url, "description": description.strip()}

            for name, url in self.PATTERN_NAME_URL.findall(md):
                if name in tools_dict:
                    tools_dict[name]["url"] = url
                else:
                    for tool_name, tool_content in tools_dict.items():
                        if tool_content["url"] == name:
                            tool_content["url"] = url
                        if tool_content["description"] == "[%s]" % name:
                            tool_content["description"] = url

            # Filter out tools that has no download url
            self.cached_tools_dict[url_md] = {
                k: v for k, v in tools_dict.items() if v["url"]
            }

        return self.cached_tools_dict[url_md]


class GitHubRepoInstaller(object):
    PATTERN_USER_REPO = r"^https?://github.com/(.+)/(.+)"

    @staticmethod
    def get_github_user_repo(url):
        m = re.match(GitHubRepoInstaller.PATTERN_USER_REPO, url)
        return m.groups() if m else None

    def download(self, url):
        user_name, repo_name = self.get_github_user_repo(url)
        zipfile_url = urljoin(url, "/%s/%s/archive/master.zip" % (user_name, repo_name))
        tmp_zipfile = os.path.join(os.environ["TMPDIR"], "%s-master.zip" % repo_name)

        r = requests.get(zipfile_url)
        with open(tmp_zipfile, "wb") as outs:
            outs.write(r.content)

        return tmp_zipfile

    def install(self, url, target_folder):
        tmp_zipfile = self.download(url)
        base_dir = os.path.splitext(os.path.basename(tmp_zipfile))[0] + "/"
        with open(tmp_zipfile, "rb") as ins:
            zipfp = zipfile.ZipFile(ins)
            for name in zipfp.namelist():
                data = zipfp.read(name)
                name = name.split(base_dir, 1)[-1]  # strip the top-level target_folder
                if name == "":  # skip top-level target_folder
                    continue

                fname = os.path.join(target_folder, name)
                if fname.endswith("/"):  # A target_folder
                    if not os.path.exists(fname):
                        os.makedirs(fname)
                else:
                    with open(fname, "wb") as fp:
                        fp.write(data)


class GistInstaller(object):
    PATTERN_GIST_ID = r"http(s?)://gist.github.com/([0-9a-zA-Z_-]*)/([0-9a-f]*)"

    @staticmethod
    def get_gist_id(url):
        m = re.match(GistInstaller.PATTERN_GIST_ID, url)
        return m.group(3) if m else None

    def download(self, url):
        gist_id = self.get_gist_id(url)
        if gist_id:
            json_url = "https://api.github.com/gists/" + gist_id
            try:
                gist_info = requests.get(json_url).json()
                files = gist_info["files"]
            except:
                raise GistDownloadError()
            file_info_list = []
            for file_info in files.values():
                lang = file_info.get("language", None)
                if lang != "Python" and not file_info["filename"].endswith(".pyui"):
                    continue
                file_info_list.append(file_info)
            if len(file_info_list) == 0:
                raise NoFilesInGistError()
            else:
                return file_info_list
        else:
            raise InvalidGistURLError()

    def install(self, url, target_folder):
        for file_info in self.download(url):
            with open(os.path.join(target_folder, file_info["filename"]), "w") as outs:
                outs.write(file_info["content"])


class InstallButton(object):
    INSTALL = "  Install  "
    UNINSTALL = "  Uninstall  "
    LOADING = "  Loading  "

    def __init__(self, app, cell, category_name, tool_name, tool_url):
        self.app, self.cell = app, cell
        self.category_name, self.tool_name, self.tool_url = (
            category_name,
            tool_name,
            tool_url,
        )

        self.btn = ui.Button()
        self.cell.content_view.add_subview(self.btn)
        self.btn.font = ("Helvetica", 12)
        self.btn.background_color = "white"
        self.btn.border_width = 1
        self.btn.corner_radius = 5
        self.btn.size_to_fit()
        self.btn.width = 58
        self.btn.x = self.app.nav_view.width - self.btn.width - 8
        self.btn.y = (self.cell.height - self.btn.height) / 2

        if self.app.is_tool_installed(self.category_name, tool_name):
            self.set_state_uninstall()
        else:
            self.set_state_install()

    def set_state_loading(self):
        self.btn.title = self.LOADING
        self.btn.action = None
        self.btn.tint_color = "green"
        self.btn.border_color = "green"

    def set_state_install(self):
        self.btn.title = self.INSTALL
        self.btn.action = functools.partial(self.app.install, self)
        self.btn.tint_color = "blue"
        self.btn.border_color = "blue"

    def set_state_uninstall(self):
        self.btn.title = self.UNINSTALL
        self.btn.action = functools.partial(self.app.uninstall, self)
        self.btn.tint_color = (0, 0.478, 1)
        self.btn.border_color = (0, 0.478, 1)


class ToolsTable(object):
    def __init__(self, app, category_name, category_url):
        self.app = app
        self.category_name = category_name
        self.category_url = category_url
        self.view = ui.TableView(frame=(0, 0, 640, 640))
        self.view.name = category_name

        self.tools_dict = self.app.repo.get_tools_from_md(category_url)
        self.tool_names = sorted(self.tools_dict.keys())

        self.view.data_source = self
        self.view.delegate = self

    def tableview_number_of_sections(self, tableview):
        return 1

    def tableview_number_of_rows(self, tableview, section):
        return len(self.tools_dict)

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell("subtitle")
        tool_name = self.tool_names[row]
        tool_url = self.tools_dict[tool_name]["url"]
        cell.text_label.text = tool_name
        cell.detail_text_label.text = self.tools_dict[tool_name]["description"]
        # TODO: Cell does not increase its height when label has multi lines of text
        # cell.detail_text_label.line_break_mode = ui.LB_WORD_WRAP
        # cell.detail_text_label.number_of_lines = 0

        InstallButton(self.app, cell, self.category_name, tool_name, tool_url)

        return cell

    def tableview_can_delete(self, tableview, section, row):
        return False

    def tableview_can_move(self, tableview, section, row):
        return False


class CategoriesTable(object):
    def __init__(self, app):
        self.app = app
        self.view = ui.TableView(frame=(0, 0, 640, 640))
        self.view.name = "Categories"
        self.categories_dict = {}
        self.load()

    @ui.in_background
    def load(self):
        self.app.activity_indicator.start()
        try:
            self.categories_dict = self.app.repo.get_categories()
            categories_listdatasource = ui.ListDataSource(
                {"title": category_name, "accessory_type": "disclosure_indicator"}
                for category_name in sorted(self.categories_dict.keys())
            )
            categories_listdatasource.action = self.category_item_tapped
            categories_listdatasource.delete_enabled = False

            self.view.data_source = categories_listdatasource
            self.view.delegate = categories_listdatasource
            self.view.reload()
        except Exception:
            console.hud_alert("Failed to load Categories", "error", 1.0)
        finally:
            self.app.activity_indicator.stop()

    @ui.in_background
    def category_item_tapped(self, sender):
        self.app.activity_indicator.start()
        try:
            category_name = sender.items[sender.selected_row]["title"]
            category_url = self.categories_dict[category_name]["url"]
            tools_table = ToolsTable(self.app, category_name, category_url)
            self.app.nav_view.push_view(tools_table.view)
        except Exception:
            console.hud_alert("Failed to load tools list", "error", 1.0)
        finally:
            self.app.activity_indicator.stop()


class PythonistaToolsInstaller(object):
    def __init__(self):
        self.repo = PythonistaToolsRepo()
        self.github_installer = GitHubRepoInstaller()
        self.gist_installer = GistInstaller()

        self.activity_indicator = ui.ActivityIndicator(flex="LTRB")
        self.activity_indicator.style = 10

        categories_table = CategoriesTable(self)
        self.nav_view = ui.NavigationView(categories_table.view)
        self.nav_view.name = "Pythonista Tools Installer"

        self.nav_view.add_subview(self.activity_indicator)
        self.activity_indicator.frame = (
            0,
            0,
            self.nav_view.width,
            self.nav_view.height,
        )
        self.activity_indicator.bring_to_front()

    @staticmethod
    def get_install_path():
        install_path = INSTALL_PATH_DEFAULT
        try:
            with open(CONF_FILE, "r") as f:
                config = json.load(f)
                install_path = config["install_path"]
        except Exception:
            install_path = INSTALL_PATH_DEFAULT
        return install_path

    @staticmethod
    def get_target_folder(category_name, tool_name):
        install_path = PythonistaToolsInstaller.get_install_path()
        install_root = os.path.expanduser("~/Documents/%s" % install_path)
        return os.path.join(install_root, category_name, tool_name)

    @staticmethod
    def is_tool_installed(category_name, tool_name):
        return os.path.exists(
            PythonistaToolsInstaller.get_target_folder(category_name, tool_name)
        )

    def install(self, btn, sender):
        btn.set_state_loading()
        self._install(btn)

    @ui.in_background
    def _install(self, btn):
        self.activity_indicator.start()
        install_path = PythonistaToolsInstaller.get_install_path()
        target_folder = PythonistaToolsInstaller.get_target_folder(
            btn.category_name, btn.tool_name
        )
        try:
            if self.gist_installer.get_gist_id(btn.tool_url):
                if not os.path.exists(target_folder):
                    os.makedirs(target_folder)
                self.gist_installer.install(btn.tool_url, target_folder)
            elif self.github_installer.get_github_user_repo(btn.tool_url):
                if not os.path.exists(target_folder):
                    os.makedirs(target_folder)
                self.github_installer.install(btn.tool_url, target_folder)
            else:  # any other url types, including iTunes
                webbrowser.open(btn.tool_url)
            btn.set_state_uninstall()
            console.hud_alert(
                "%s installed at %s" % (btn.tool_name, install_path), "success", 1.0
            )
        except Exception as e:
            # clean up the directory
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder)
            btn.set_state_install()  # revert the state
            # Display some debug messages
            etype, evalue, tb = sys.exc_info()
            sys.stderr.write("%s\n" % repr(e))
            import traceback

            traceback.print_exception(etype, evalue, tb)
            console.hud_alert("Installation failed", "error", 1.0)
        finally:
            self.activity_indicator.stop()

    def uninstall(self, btn, sender):
        target_folder = PythonistaToolsInstaller.get_target_folder(
            btn.category_name, btn.tool_name
        )
        if os.path.exists(target_folder):
            shutil.rmtree(target_folder)
        btn.set_state_install()
        console.hud_alert("%s uninstalled" % btn.tool_name, "success", 1.0)

    def launch(self):
        self.nav_view.present("fullscreen")


if __name__ == "__main__":
    ptinstaller = PythonistaToolsInstaller()
    ptinstaller.launch()
