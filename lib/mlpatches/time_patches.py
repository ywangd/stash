from mlpatches import base
import time


class ClockPatch(base.FunctionPatch):
    """patch for os.listdir()"""

    PY3 = True
    module = "time"
    function = "clock"
    replacement = time.perf_counter


CLOCK_PATCH = ClockPatch()
