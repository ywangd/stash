"""
Stub ui to allow debug on PC
"""

AUTOCAPITALIZE_NONE = 0


def measure_string(*args, **kwargs):
    return 12.0

def in_background(func):
    return func

def get_screen_size():
    return 100, 100


class View(object):

    def __init__(self, *args, **kwargs):
        self.on_screen = True
        self.width = 100
        self.height = 100
        self.content_size = (100, 100)
        self.content_offset = (0, 0)
        self.superview = None
        self.subviews = []
        self.delegate = None

    def add_subview(self, v):
        self.subviews.append(v)
        v.superview = self

    def remove_subview(self, v):
        self.subviews.remove(v)

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


class TextField(View):
    def __init__(self, *args, **kwargs):
        super(TextField, self).__init__(*args, **kwargs)
        self.text = ''

class TextView(View):
    def __init__(self, *args, **kwargs):
        super(TextView, self).__init__(*args, **kwargs)
        self.text = ''
        self.selected_range = (0, 0)

    def replace_range(self, rng, s):
        self.text = self.text[:rng[0]] + s + self.text[rng[1]:]
        tot_len = len(self.text)
        self.selected_range = (tot_len, tot_len)

    def begin_editing(self):
        pass

    def end_editing(self):
        pass

class ScrollView(View):
    pass


class Button(View):
    def __init__(self, *args, **kwargs):
        super(Button, self).__init__(*args, **kwargs)


class TableView(View):
    def __init__(self, *args, **kwargs):
        super(TableView, self).__init__(*args, **kwargs)

class ListDataSource(object):
    def __init__(self, lst):
        pass
