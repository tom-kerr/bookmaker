#import yappi
import os, sys, time
from collections import OrderedDict
from datetime import date
import multiprocessing, threading
import Queue

from util import Util
from environment import Environment, Scandata

from core.featuredetection import FeatureDetection
from core.derive import Derive
from core.crop import Crop
from core.ocr import OCR
from gui.common import Common


class ProcessHandling:

    thread_count_ignore = ('drain_queue',
                           'handle_thread_exceptions',
                           'distribute',
                           'run_pipeline')

    def __init__(self):
        try:
            self.cores = multiprocessing.cpu_count()
        except NotImplemented:
            self.cores = 1

        self.processes = 0
        self._active_threads = {}
        self._inactive_threads = self.new_queue()
        self.item_queue = self.new_queue()

        self._ExceptionQueue = Queue.Queue()
        self.handled_exceptions = []

        self.polling_threads = False
        self.polling_exceptions = False

        self.OperationObjects = {}


    def _init_polls(self):
        if Environment.interface == 'command' and not self.polling_exceptions:
            self._init_exception_poll()
        if not self.polling_threads:
            self._init_thread_poll()


    def _init_thread_poll(self):
        self.polling_threads = True
        self._thread_poll = threading.Thread(None, self._poll_threads,
                                            '_poll_threads')
        self._thread_poll.start()


    def _init_exception_poll(self):
        self.polling_exceptions = True
        self._exception_poll = threading.Thread(None, self._poll_ExceptionQueue,
                                               '_poll_ExceptionQueue')
        self._exception_poll.start()


    def _already_processing(self, pid):
        if pid in self._active_threads:
            return True
        else:
            return False


    def new_queue(self):
        return OrderedDict()


    def drain_queue(self, queue, mode):
        self._init_polls()
        pids = []
        for pid, data in queue.items():
            pids.append(pid)
            func, args, logger, callback = data
            #print func, args, logger, callback
            if mode == 'sync':
                if not isinstance(args, tuple):
                    args = tuple((args,)) if args is not None else ()
                try:
                    func(*args)
                except:
                    self.join((func.__name__,
                               Util.exception_info(),
                               logger))
            elif mode == 'async':
                self.add_process(func, pid, args, logger, callback)
            finished = 0
            active_pids = []
            for pid, thread in self._active_threads.items():
                active_pids.append(pid)
            for id in pids:
                if id not in active_pids and id not in self.item_queue:
                    finished += 1
            if finished == len(pids):
                break
            else:
                time.sleep(1)


    def add_process(self, func, pid, args, logger=None, call_back=None):
        self._init_polls()
        time.sleep(0.25)
        if self._already_processing(pid):
            return False
        self.clear_exceptions(pid)
        if self.processes >= self.cores:
            self._wait(func, pid, args)
            return False
        else:
            if not isinstance(args, tuple):
                args = tuple((args,)) if args is not None else ()
            try:
                new_thread = threading.Thread(None, func, pid, args)
            except:
                self.join(pid+'_new_thread_'+func.__name__,
                          Util.exception_info(), logger)
            new_thread.func = func.__name__
            new_thread.daemon = True
            new_thread.logger = logger
            new_thread.call_back = call_back
            new_thread.start_time = Util.microseconds()
            try:
                new_thread.start()
            except:
                self.join(pid+'_start_thread_'+func.__name__,
                          Util.exception_info(), logger)
            self._active_threads[pid] = new_thread
            if new_thread.func not in ProcessHandling.thread_count_ignore:
                self.processes += 1
                #print 'added ' + str(pid) + ' #processes:' + str(self.processes)
            if logger:
                new_thread.logger.message('New Thread Started -->   ' +
                                          'Identifier: ' + str(pid) +
                                          '   Task: ' + str(func), 'processing')
            return True


    def _wait(self, func, pid, args):
        #print pid + ' waiting...'
        if not pid in self.item_queue:
            self.item_queue[pid] = (func, args)


    def _submit_waiting(self):
        queue = []
        for pid, item in self.item_queue.items():
            if self.add_process(item[0], pid, item[1]):
                queue.append(pid)
            else:
                break
        queue.reverse()
        for pid in queue:
            del self.item_queue[pid]


    def finish(self, identifier=None):
        #print 'finishing'
        destroy = []
        for pid, thread in self._active_threads.items():
            destroy.append(pid)
        for pid in destroy:
            self.destroy_thread(pid)
        self.item_queue = self.new_queue()
        self.polling_threads = False
        self.polling_exceptions = False
        if identifier:
            for _class, op_obj in self.OperationObjects[identifier].items():
                op_obj.terminate_child_processes()
        else:
            for identifier, class_obj in self.OperationObjects.items():
                for _class, op_obj in class_obj.items():
                    op_obj.terminate_child_processes()


    def clear_exceptions(self, pid):
        remove = None
        for num, item in enumerate(self.handled_exceptions):
            if item == pid:
                remove = num
            if remove is not None:
                del self.handled_exceptions[remove]


    def destroy_thread(self, pid):
        if pid in self._active_threads:
            if self._active_threads[pid].logger:
                self._active_threads[pid].logger.message('Destroying Thread ' + str(pid), 'processing')
            if self._active_threads[pid].func not in ProcessHandling.thread_count_ignore:
                self.processes -= 1
            self._active_threads[pid]._Thread__stop()
            del self._active_threads[pid]

    def _clear_inactive(self):
        inactive = {}
        for pid, thread in self._active_threads.items():
            if not thread.is_alive():
                thread.end_time = Util.microseconds()
                if thread.logger:
                    thread.logger.message('Thread ' + str(pid) + ' Finished', 'processing')
                inactive[pid] = thread
        for pid, thread in inactive.items():
            if thread.call_back is not None:
                thread.call_back(thread)
            if thread.func not in ProcessHandling.thread_count_ignore:
                self.processes -= 1
                #print 'thread ' + pid + ' finished   #processes ' + str(self.processes)
            self._inactive_threads[pid] = thread
            del self._active_threads[pid]


    def _are_active_processes(self):
        if (self.processes == 0 and
            not [thread.func for pid, thread in self._active_threads.items()
                 if thread.func in ProcessHandling.thread_count_ignore]):
            return False
        else:
            return True


    def _poll_threads(self):
        while True:
            if not self.polling_threads:
                return
            time.sleep(1.0)
            self._clear_inactive()
            self._submit_waiting()
            if not self._are_active_processes():
                self.polling_threads = False
                return


    def _poll_ExceptionQueue(self):
        while True:
            if not self.polling_exceptions:
                return
            time.sleep(1.0)
            self.check_ExceptionQueue()
            if not self._are_active_processes():
                self.polling_exceptions = False
                return


    def check_ExceptionQueue(self):
        try:
            pid, traceback, logger = self._ExceptionQueue.get_nowait()
        except Queue.Empty:
            pass
        else:
            self.handled_exceptions.append(pid)
            msg = 'Exception in ' + pid + ':\n' + traceback
            identifier = pid.split('_')[0]
            if Environment.interface == 'gui':
                self.finish(identifier)
                Common.dialog(message=msg)
            elif Environment.interface == 'command':
                self.finish(identifier)
                Util.bail(msg, logger)
            return True


    def join(self, args):
        self._ExceptionQueue.put(args)
        self._ExceptionQueue.join()


    def _create_operation_instance(self, identifier, _class, method, book):
        if _class not in globals():
            raise LookupError('Could not find module \'' + _class + '\'')
        else:
            if identifier not in self.OperationObjects:
                self.OperationObjects[identifier] = {}
            self.OperationObjects[identifier][_class] = globals()[_class](self, book)
            function = getattr(self.OperationObjects[identifier][_class], method)
            return function


    def multi_threaded(f):
        def distribute(self, identifier, _class, method, book, *args):
            function = self._create_operation_instance(identifier, _class, method, book)
            queue = self.new_queue()
            chunk = (book.page_count-2)/self.cores
            for core in range(0, self.cores):
                start = (core * chunk) + 1
                if core == self.cores - 1:
                    end = book.page_count-1
                else:
                    end = (start + chunk)
                fargs = [start, end]
                for arg in args:
                    fargs.append(arg)
                queue[book.identifier + '_' + str(start) + function.__name__] = (function,
                                                                                 tuple(fargs),
                                                                                 book.logger, None)
            return f(self, queue)
        return distribute


    @multi_threaded
    def run_pipeline_distributed(self, queue):
        try:
            self.drain_queue(queue, 'async')
        except:
            self.join(('run_pipeline_distributed',
                       Util.exception_info(), None))


    def run_pipeline(self, identifier, _class, method, book, args):
        function = self._create_operation_instance(identifier, _class, method, book)
        queue = self.new_queue()
        queue[book.identifier + '_' + _class + '_' + function.__name__] = (function,
                                                                           args,
                                                                           book.logger, None)
        try:
            self.drain_queue(queue, 'async')
        except:
            self.join((book.identifier + '_' + _class + '_' + function.__name__,
                       Util.exception_info(), None))



    """
    def derive_formats(self, book, formats):
        self.Derive = Derive(self, book)
        queue = self.new_queue()
        for f, args in formats.items():
            if f == 'text':
                if self.OCR is not None:
                    ocr_data = self.OCR.ocr_data
                else:
                    ocr_data = None
                queue[book.identifier + '_' + f] = (self.Derive.full_plain_text,
                                                    ocr_data, book.logger, None)
            elif f == 'pdf':
                queue[book.identifier + '_' + f] = (self.Derive.pdf,
                                                    args, book.logger, None)
            elif f == 'djvu':
                queue[book.identifier + '_' + f] = (self.Derive.djvu,
                                                    args, book.logger, None)
            elif 'epub':
                self.Derive.epub()
                pass

        try:
            self.drain_queue(queue, 'async')
            self.Derive.ImageOps.complete(book.identifier + '_derive')
        except Exception as e:
            Util.bail(str(e))
            """
