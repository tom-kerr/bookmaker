from util import Util

class Operation(object):
    """ Base Class for processing operations.
    """
    def __init__(self, components):
        self._import_components(components)
        self.halt = False
        self.completed = {}
        self.exec_times = []

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

    def complete_process(self, leaf, exec_time):
        self.completed[leaf] = exec_time
        self.exec_times.append(exec_time)

    def get_avg_exec_time(self):
        return sum(self.exec_times)/len(self.exec_times)

