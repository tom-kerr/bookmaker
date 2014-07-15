from copy import copy

from events import OnEvents, handle_events
from util import Util

class Operation(OnEvents):
    """ Base Class for processing operations.
    """
    def __init__(self, components):
        super(Operation, self).__init__()
        self._import_components(components)        
        self.init_bookkeeping()

    def init_bookkeeping(self):
        """ In order to cleanly exit on completion/exception and display progress
            to the user, we keep track of how many cores are committed to the 
            operation, the completed tasks involved and their execution times.
        """
        self.thread_count = 0
        self.completed = {'__finished__': False}
        self.exec_times = {}
        for component in self.imports:
            cls = component[1]
            self.completed[cls] = {}
            self.exec_times[cls] = []

    def init_components(self, book):
        self.components = []
        for component in self.imports:
            cls = component[1]
            instance = getattr(globals()[cls], cls)(book)
            self.components.append(instance)
            setattr(self, cls, instance)

    def _import_components(self, components):
        self.imports = []
        for component in components:
            mod, cls = component
            globals()[cls] = __import__('components.'+mod,
                                        globals(), locals(),
                                        [cls,], 0)
        self.imports = components

    def _get_chunk(self, threads, pagecount, chunk):
        remainder = pagecount % threads
        pagecount = pagecount - remainder
        chunksize = pagecount/threads
        start = chunksize * chunk
        end = start + chunksize
        if chunk == threads-1:
            end += remainder
        return int(start), int(end)
    
    def multithreaded(f):
        @handle_events
        def distribute(self, *args, **kwargs):
            if not isinstance(args, list):
                if not args:
                    args = [self, ]
                else:
                    args = [args, ]
            if not kwargs:
                kwargs = {}
            queue = self.ProcessHandler.new_queue()
            available_threads = self.ProcessHandler.cores - self.ProcessHandler.processes
            self.thread_count = available_threads
            self.book.start_time = Util.microseconds()
            for chunk in range(0, available_threads):
                start, end = self._get_chunk(available_threads, self.book.page_count, chunk)
                kwargs['start'], kwargs['end'] = start, end
                queue.add(self.book, self.__class__.__name__+'.'+str(chunk), 
                          f, args, copy(kwargs))
            return queue.drain(mode='async')
        return distribute

    def make_pid_string(self, func_name):
        return '.'.join((self.book.identifier, 
                         self.__class__.__name__, 
                         func_name))

    def terminate_child_processes(self):
        """ Signal to subprocesses to terminate """
        for component in self.components:
            component.Util.end_active_processes()     

    def complete_process(self, cls, leaf, exec_time):
        """ Bookkeeping """
        if isinstance(leaf, list):
            etime = exec_time/len(leaf)
            for l in leaf:
                self.complete_process(cls, l, etime)
            return
        else:
            self.completed[cls][leaf] = exec_time
            self.exec_times[cls].append(exec_time)

    def set_finished(self):
        self.completed['__finished__'] = True

    def get_avg_exec_time(self, cls):
        return sum(self.exec_times[cls])/len(self.exec_times[cls])

    def on_exit(self, **kwargs):
        self.set_finished()
