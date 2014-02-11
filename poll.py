import time
from threading import Thread
from queue import Empty

import gi
from gi.repository import GObject
GObject.threads_init()

from util import Util
from environment import Environment
from gui.common import CommonActions as ca

class Polls(object):
    """
    """
    def __new__(cls, ProcessHandler):
        if Environment.interface == 'shell':
            return ShellPolls(ProcessHandler)
        elif Environment.interface == 'gui':
            return GUIPolls(ProcessHandler)


class BasePolls(object):
    """ Polls base class
    """
    def __init__(self, ProcessHandler):
        self._should_poll = True
        self._is_polling_threads = False
        self._is_polling_exceptions = False
        self.ProcessHandler = ProcessHandler

    def start_polls(self):
        if self._should_poll:
            self._start_thread_poll()
            self._start_exception_poll()

    def stop_polls(self):
        self._should_poll = False

    def _start_thread_poll(self):
        pass

    def _thread_poll(self):
        pass

    def _start_exception_poll(self):
        pass

    def _exception_poll(self):
        pass


#TODO add some progress indicator for command line users
class ShellPolls(BasePolls):
    """
    """
    def __init__(self, ProcessHandler):
        super(ShellPolls, self).__init__(ProcessHandler)

    def _start_thread_poll(self):
        if not self._is_polling_threads:
            self._thread_poll = Thread(target=self._thread_poll)
            self._thread_poll.start()
            self._is_polling_threads = True

    def _thread_poll(self):
        while True:
            time.sleep(1.0)
            if (not self._should_poll or 
                not self.ProcessHandler._are_active_processes()):
                self._is_polling_threads = False
                self._should_poll = False
                break
            self.ProcessHandler._clear_inactive()
            self.ProcessHandler._submit_waiting()
            

    def _start_exception_poll(self):
        if not self._is_polling_exceptions:
            self._exception_poll = Thread(target=self._exception_poll)
            self._exception_poll.start()
            self._is_polling_exceptions = True

    def _exception_poll(self):
        while True:
            time.sleep(1.0)
            if (not self._should_poll or 
                not self.ProcessHandler._are_active_processes()):
                self._is_polling_exceptions = False
                self._should_poll = False
                break
            try:
                pid, traceback = self.ProcessHandler._exception_queue.get_nowait()
            except Empty:
                pass
            else:
                self.ProcessHandler._handled_exceptions.append(pid)
                msg = 'Exception in ' + pid + ':\n' + traceback
                identifier = pid.split('.')[0]
                self.ProcessHandler.finish(identifier)
                print (msg)
                #raise Exception(msg)
            #time.sleep(1.0)



class GUIPolls(BasePolls):
    """
    """
    def __init__(self, ProcessHandler):
        super(GUIPolls, self).__init__(ProcessHandler)

    def _start_thread_poll(self):
        if not self._is_polling_threads:
            GObject.timeout_add(1000, self._thread_poll)
            self._is_polling_threads = True

    def _thread_poll(self):
        time.sleep(1)
        if (not self._should_poll or 
            not self.ProcessHandler._are_active_processes()):
            self._is_polling_threads = False
            self._should_poll = False
            return False
        self.ProcessHandler._clear_inactive()
        self.ProcessHandler._submit_waiting()
        return True

    def _start_exception_poll(self):
        if not self._is_polling_exceptions:
            GObject.timeout_add(1000, self._exception_poll)
            self._is_polling_exceptions = True

    def _exception_poll(self):
        time.sleep(1)
        if (not self._should_poll or 
            not self.ProcessHandler._are_active_processes()):
            self._is_polling_exceptions = False
            self._should_poll = False
            return False
        try:
            pid, traceback = self.ProcessHandler._exception_queue.get_nowait()
        except Empty:
            return True
        else:
            self.ProcessHandler._handled_exceptions.append(pid)
            msg = 'Exception in ' + pid + ':\n' + traceback
            identifier = pid.split('.')[0]
            self.ProcessHandler.finish(identifier)
            ca.dialog(message=msg)
            return True
            #raise Exception(msg)
            
