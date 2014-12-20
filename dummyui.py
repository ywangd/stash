"""
Stub ui to allow debug on PC
"""

AUTOCAPITALIZE_NONE = 0


def in_background(func):
    return func

def get_screen_size():
    return (100, 100)


class View(object):

    def __init__(self, *args, **kwargs):
        self.width = 100
        self.height = 100
        self.content_size = (100, 100)
        self.content_offset = (0, 0)
        self.superview = None
        self.subviews = []

    def add_subview(self, v):
        self.subviews.append(v)
        v.superview = self

    def present(self, style='popover'):
        pass

    def wait_modal(self):
        pass

    def size_to_fit(self):
        pass

    def send_to_back(self):
        pass

    def bring_to_front(self):
        pass

    def begin_editing(self):
        pass

class TextField(View):
    def __init__(self, *args, **kwargs):
        super(TextField, self).__init__(*args, **kwargs)
        self.text = ''

class TextView(View):
    def __init__(self, *args, **kwargs):
        super(TextView, self).__init__(*args, **kwargs)
        self.text = ''

class Button(View):
    def __init__(self, *args, **kwargs):
        super(Button, self).__init__(*args, **kwargs)


class TableView(View):
    def __init__(self, *args, **kwargs):
        super(TableView, self).__init__(*args, **kwargs)

class ListDataSource(object):
    def __init__(self, lst):
        pass