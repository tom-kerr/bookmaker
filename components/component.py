from environment import Environment
from util import Util

class Component(object):
    """ Base Class for individual processes.
    """
    def __init__(self):
        self.exec_times = []
        self.Util = Util()

    def run(self, **kwargs):
        """Method to override"""
        pass

    def execute_callback(self, callback, *args, **kwargs):
        if isinstance(callback, str):
            getattr(self, callback)(*args, **kwargs)
        elif hasattr(callback, '__call__'):
            callback(*args, **kwargs)

    def execute(self, kwargs, stdout=None, stdin=None,
                retval=False, return_output=False, print_output=False,
                current_wd=None, logger=None):
        cmd = [self.executable]
                        
        for arg in self.args:
            if 'stdout' == arg:
                stdout = arg
            elif 'stdin' == arg:
                stdin = arg
            else:
                if isinstance(arg, list):
                    #value = [arg[0], getattr(self, arg[1])]
                    value = [arg[0], kwargs[arg[1]]]
                else:
                    value = kwargs[arg]
                if value is not None:
                    if not isinstance(value, list):
                        value = [value,]
                    for v in value:
                        if v not in (None, ''):
                            cmd.append(str(v))
        
        output = self.Util.exec_cmd(cmd, stdout, stdin,
                                    retval, return_output,
                                    print_output, current_wd, 
                                    logger)
        self.exec_times.append(output['exec_time'])
        return output

    def get_last_exec_time(self):
        if self.exec_times:
            return self.exec_times[-1]
        else:
            return 0

    def get_avg_exec_time(self):
        return sum(self.exec_times)/len(self.exec_times)
