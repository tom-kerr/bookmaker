from environment import Environment
from util import Util

class Component(object):
    """
    Base Class for individual processes.

    """

    def __init__(self, args):
        for arg in args:
            if isinstance(arg, list):
                self.set_property(arg)
            else:
                setattr(self, arg, None)
        self.exec_times = []


    def set_property(self, arg):
        nstring = str(arg[1])
        setattr(self, '__'+arg[1], None)
        def get(self):
            return getattr(self, '__'+nstring)
        def set(self, value):
            setattr(self, '__'+nstring, value)
        def delete(self):
            pass
        setattr(self, arg[1], property(get, set, delete, ''))


    def execute(self, stdout=None, stdin=None,
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
                    value = [arg[0], getattr(self, arg[1])]
                else:
                    value = getattr(self, arg)
                if value:
                    if not isinstance(value, list):
                        value = [value]
                    for v in value:
                        if v is not None:
                            cmd.append(str(v))

        try:
            output = Util.exec_cmd(cmd, stdout=stdout, stdin=stdin,
                                   retval=retval, return_output=return_output,
                                   print_output=print_output,
                                   current_wd=current_wd, logger=logger)
            self.exec_times.append( output['exec_time'] )
        except Exception as e:
            raise e
        else:
            return output


    def get_last_exec_time(self):
        return self.exec_times[-1]


    def get_avg_exec_time(self):
        return sum(self.exec_times)/len(self.exec_times)
