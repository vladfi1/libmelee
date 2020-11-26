import sys
import threading
from time import sleep
import _thread as thread

class TimeoutException(Exception):
    pass

def quit_function(fn_name):
    # print to stderr, unbuffered in Python 2.
    print('{0} took too long'.format(fn_name), file=sys.stderr)
    sys.stderr.flush() # Python 3 stderr is likely buffered.
    raise TimeoutException("timeout!")

class Timeout(object):
    def __init__(self, f, seconds):
        self.func = f
        self.s = seconds

    def __call__(self, *args, **kwargs):
        timer = threading.Timer(self.s, quit_function, args=[self.func.__name__])
        timer.start()
        ret = False
        try:
            self.func(*args, **kwargs)
            ret = True
        except TimeoutException:
            ret = False
        finally:
            timer.cancel()
            return ret

    def __get__(self, instance, owner):
        from functools import partial
        return partial(self.__call__, instance)