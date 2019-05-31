#-*- coding: utf-8 -*-
"""
StaSh input history
"""
from io import open
import json


class ShHistory(object):
    """
    This class is responsible for input history.
    """
    
    ENCODING = "utf-8"
    
    def __init__(self, config):
        self._histories = {}
        self._current = None
        self.allow_double = config.getboolean("history", "allow_double_lines")
        self.hide_whitespace = config.getboolean("history", "hide_whitespace_lines")
        self.maxsize = config.getint("history", "maxsize")
    
    @classmethod
    def load(cls, path, config):
        """
        Load the history from a path.
        :param path: path to load from.
        :type path: str
        :param config: config for the ShHistory object
        :type config: ConfigParser
        :return: the history loaded from the file
        :rtype: ShHistory
        """
        shh = cls(config)
        try:
            with open(path, "r", encoding=cls.ENCODING) as fin:
                h = json.loads(u"" + fin.read())
        except ValueError:
            h = {"StaSh.runtime": cls.load_old_format(path)}
        shh._histories = h
        return shh
    
    @classmethod
    def load_old_format(cls, path):
        """
        Load the content of an old-style history.
        :param path: path to load from
        :type path: str
        :return: the lines loaded from the file
        :rtype: list of str
        """
        with open(path, "r", encoding=cls.ENCODING) as fin:
            lines = [line.strip() for line in fin.readlines()]
        return lines
    
    def save(self, path):
        """
        Save the history to a path.
        :param path: path to save to.
        :type path: str
        """
        with open(path, "w", encoding=self.ENCODING) as fout:
            s = json.dumps(self._histories)
            fout.write(u"" + s)  # ensure unicode
    
    def clear(self, target):
        """
        Clear the history
        :param target: history to clear
        :type history: str
        """
        if target in self._histories:
            del self._histories[target]
    
    def swap(self, target):
        """
        Swap the history
        :param target: identifier to get the history for
        :type target: str or None
        """
        self._current = target
    
    def add(self, line, always=False):
        """
        Add a line to the history.
        :param line: line to add to history
        :type line: str
        :param always: always add this line, regardless of config
        :type always: bool
        """
        if self._current not in self._histories:
            self._histories[self._current] = []
        stripped = line.strip()
        last_line = (self._histories[self._current][-1] if len(self._histories[self._current]) > 0 else None)
        if not always:
            # check if this line should be added
            if stripped == last_line and not self.allow_double:
                # prevent double lines
                return
            if line.startswith(" ") and self.hide_whitespace:
                # hide lines starting with a whitespace
                return
        self._histories[self._current].append(stripped)
        # ensure maxsize
        while len(self._histories[self._current]) > max(0, self.maxsize):
            self._histories[self._current].pop(0)
    
    def getlist(self):
        """
        Return a list of the current history.
        :return: list of current history entries
        :rtype: list of str
        """
        if self._current not in self._histories:
            self._histories[self._current] = []
        return self._histories[self._current][::-1]