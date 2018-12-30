

class ObjCClass(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return ObjCClass()

    def __getattr__(self, item):
        return ObjCClass()



class ObjCInstance(ObjCClass):
    pass

class UIColor(ObjCClass):

    @classmethod
    def blackColor(cls):
        pass

    @classmethod
    def redColor(cls):
        pass

    @classmethod
    def greenColor(cls):
        pass

    @classmethod
    def brownColor(cls):
        pass

    @classmethod
    def blueColor(cls):
        pass

    @classmethod
    def magentaColor(cls):
        pass

    @classmethod
    def cyanColor(cls):
        pass

    @classmethod
    def whiteColor(cls):
        pass

    @classmethod
    def grayColor(cls):
        pass

    @classmethod
    def yellowColor(cls):
        pass

    @classmethod
    def colorWithRed_green_blue_alpha_(cls, *args, **kwargs):
        pass

class NSRange(ObjCClass):
    pass


def create_objc_class(*args, **kwargs):
    return ObjCClass()

def ns(*args, **kwargs):
    return ObjCInstance()

def on_main_thread(func):
    return func


class ctypes(object):

    class pythonapi(object):
        @staticmethod
        def PyThreadState_SetAsyncExc(tid, exectype,):
            return 1

    @staticmethod
    def c_long(val):
        return val

    @staticmethod
    def py_object(val):
        return val