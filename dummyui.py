"""
Stub ui to allow debug on PC
"""

def in_background(func):
    return func

def get_screen_size():
    return (100, 100)


class View(object):

    def __init__(self):
        self.width = 100
        self.height = 100
        self.content_size = (100, 100)
        self.content_offset = (0, 0)

    def add_subview(self, v):
        pass

    def present(self, style='popover'):
        pass

    def wait_modal(self):
        pass

class TextField(View):
    pass

class TextView(View):
    pass

class Button(View):
    pass

class TableView(View):
    pass

class ListDataSource(object):
    def __init__(self, lst):
        pass