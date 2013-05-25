from util import Util

class Component(object):

    def __init__(self, args):
        for arg in args:
            setattr(self, arg, None)


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
                cmd.append(str(getattr(self, arg)))
        try:
            return Util.exec_cmd(cmd, stdout=stdout, stdin=stdin,
                                 retval=retval, return_output=return_output,
                                 print_output=print_output,
                                 current_wd=current_wd, logger=logger)
        except Exception as e:
            raise e
