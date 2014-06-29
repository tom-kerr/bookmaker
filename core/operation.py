from util import Util

class Operation(object):
    """ Base Class for processing operations.
    """
    def __init__(self, components):
        self._import_components(components)        
        self.init_bookkeeping()

    def init_bookkeeping(self):
        """ In order to cleanly exit on completion/exception and display progress
            to the user, we keep track of how many cores are committed to the 
            operation, the completed tasks involved and their execution times
        """
        self.thread_count = 0
        self.completed = {'__finished__': False}
        self.exec_times = {}
        for component, info  in self.imports.items():
            _class = info['class']
            self.completed[_class] = {}
            self.exec_times[_class] = []

    def _import_components(self, components):
        self.imports = {}
        for component, info  in components.items():
            _class = info['class']
            globals()[_class] = __import__('components.'+component,
                                           globals(), locals(),
                                           [_class,], 0)
        self.imports = components

    def init_components(self, book):
        self.components = []
        for component, info in self.imports.items():
            _class = info['class']
            if 'hook' in info:
                hook = info['hook']
            else:
                hook = None
            instance = getattr(globals()[_class], _class)(book)
            self.components.append( (instance, hook) )
            setattr(self, _class, instance)

    def make_pid_string(self, func_name):
        return '.'.join((self.book.identifier, 
                         self.__class__.__name__, 
                         func_name))

    def terminate_child_processes(self):
        """ Signal to subprocesses to terminate """
        for item in self.components:
            component, hook = item
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

