class TreeError(Exception): ...


class TreePermissionError(TreeError, PermissionError): ...


class TreeSortTypeError(TreeError, ValueError):
    possible_values = {'name', 'version', 'size', 'mtime', 'ctime'}

    def __init__(self, *args):
        self.message = "tree: missing argument to --sort"
        # self.message = "[--sort type should be one of {'name', 'version', 'size', 'mtime', 'ctime'}]"
        super().__init__(*args)


class TreeFileLimitError(TreeError, ValueError):
    def __init__(self, count, *args):
        self.count = count
        self.message = f"[{count} entries exceeds filelimit, not opening dir]"
        super().__init__(self.message, *args)
