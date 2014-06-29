import time
from threading import Thread
from queue import Empty

import gi
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GObject

from util import Util
from environment import Environment
from gui.common import CommonActions as ca

class PollsFactory(object):
    """ Returns a polling object geared towards either shell use or the gui. The 
        reason for having separate poll objects is because gui dialogs cannot be 
        produced from a separate thread; we must use gobject's add_timeout to 
        allow this, and so the poll semantics are slightly different.
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
    """ Monitors the CPU bound threads, submitting waiting processes when others 
        finish, and will abort a process when an exception arises. In the event 
        of an exception, all processes running in conjunction to the failed 
        process will also be shutdown, i.e., tasks distributed across multple 
        cores will see all their associated threads terminate. The exception will 
        also be printed to the screen and logged.
    """
    def __init__(self, ProcessHandler):
        super(ShellPolls, self).__init__(ProcessHandler)

    def _start_thread_poll(self):
        if not self._is_polling_threads:
            self._tpoll = Thread(target=self._thread_poll)
            self._tpoll.start()
            self._is_polling_threads = True

    def _thread_poll(self):
        while True:
            time.sleep(1.0)
            self.ProcessHandler._clear_inactive()
            self.ProcessHandler._submit_waiting()
            
    def _start_exception_poll(self):
        if not self._is_polling_exceptions:
            self._epoll = Thread(target=self._exception_poll)
            self._epoll.start()
            self._is_polling_exceptions = True

    def _exception_poll(self):
        while True:
            time.sleep(1.0)
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
                


class GUIPolls(BasePolls):
    """ Monitors the CPU bound threads, submitting waiting processes when others 
        finish, and will abort a process when an exception arises. In the event 
        of an exception, all processes running in conjunction to the failed 
        process will also be shutdown, i.e., tasks distributed across multple 
        cores will see all their associated threads terminate. The exception will 
        also be displayed in a dialog box and logged.
    """
    def __init__(self, ProcessHandler):
        super(GUIPolls, self).__init__(ProcessHandler)

    def _start_thread_poll(self):
        if not self._is_polling_threads:
            GObject.timeout_add(1000, self._thread_poll)
            self._is_polling_threads = True
        
    def _thread_poll(self):
        self.ProcessHandler._clear_inactive()
        self.ProcessHandler._submit_waiting()
        return True

    def _start_exception_poll(self):
        if not self._is_polling_exceptions:
            GObject.timeout_add(1000, self._exception_poll)
            self._is_polling_exceptions = True

    def _exception_poll(self):
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
            
