from util import Util

class Operation(object):
    """ Base Class for processing operations.
    """
    def __init__(self, components):
        self.halt = False
        self._import_components(components)        
        self.init_bookkeeping()

    def init_bookkeeping(self):
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
                                           [_class,], -1)
        self.imports = components

    def init_components(self, book):
        self.components = []
        for component, info in self.imports.items():
            _class = info['class']
            if 'callback' in info:
                callback = info['callback']
            else:
                callback = None
            instance = getattr(globals()[_class], _class)(book)
            self.components.append( (instance, callback) )
            setattr(self, _class, instance)

    def make_pid_string(self, func_name):
        return '.'.join((self.book.identifier, 
                         self.__class__.__name__, 
                         func_name))

    def terminate_child_processes(self):
        for item in self.components:
            component, callback = item
            component.Util.end_active_processes()     

    def complete_process(self, cls, leaf, exec_time):
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

