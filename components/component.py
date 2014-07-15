from events import OnEvents
from environment import Environment
from util import Util

class Component(OnEvents):
    """ Base Class for individual processes.
    """
    def __init__(self):
        super(Component, self).__init__()
        self.exec_times = []
        self.Util = Util()

    def run(self, **kwargs):
        pass
                           
    def execute(self, kwargs, stdout=None, stdin=None,
                return_output=False, print_output=False,
                current_wd=None, logger=None, hook=True):
        cmd = [self.executable]
                        
        for arg in self.args:
            if 'stdout' == arg:
                stdout = arg
            elif 'stdin' == arg:
                stdin = arg
            else:
                if isinstance(arg, list):
                    #value = [arg[0], getattr(self, arg[1])]
                    if kwargs[arg[1]] is not None:
                        value = [arg[0], kwargs[arg[1]]]
                    else:
                        value = None
                else:
                    value = kwargs[arg]
                if value is not None:
                    if not isinstance(value, list):
                        value = [value,]
                    for v in value:
                        if v not in (None, '') and not (not v and isinstance(v, bool)):
                            cmd.append(str(v))        
        output = self.Util.exec_cmd(cmd, stdout, stdin,
                                    return_output, print_output, 
                                    current_wd, logger)
        self.exec_times.append(output['exec_time'])        
        if hook:
            retval = output['retval']
            kwargs.update({'output': output})
            success = True if retval == 0 else False
            self.event_trigger(success, **kwargs)            
        return output

    def get_last_exec_time(self):
        if self.exec_times:
            return self.exec_times[-1]
        else:
            return 0

    def get_avg_exec_time(self):
        return sum(self.exec_times)/len(self.exec_times)
