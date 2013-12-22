
class Operation(object):
    """
    Base Class for processing operations.

    """


    def __init__(self, components):
        try:
            self._import_components(components)
        except ImportError as e:
            raise e
        self.completed = {}
        self.exec_times = []


    def _import_components(self, components):
        for component, _class  in components.items():
            globals()[_class] = __import__('components.'+component,
                                           globals(), locals(),
                                           [_class,], -1)
        self.imports = components


    def init_components(self, args):
        self.components = []
        for component, _class in self.imports.items():
            instance = getattr(globals()[_class], _class)(args.pop(0))
            self.components.append(instance)
            setattr(self, _class, instance)

            
    def terminate_child_processes(self):
        for component in self.components:
            component.Util.end_active_processes()


    def complete_process(self, leaf, exec_time):
        self.completed[leaf] = exec_time
        self.exec_times.append(exec_time)


    def get_avg_exec_time(self):
        return sum(self.exec_times)/len(self.exec_times)


