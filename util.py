import os
import signal
import sys
import subprocess
import re
import math
import time
import traceback

class Util(object):
    """ Used mostly to manage system calls, including
        spawning, terminating, and collecting process 
        execution time and output. 
    """

    def __init__(self):
        self.active_procs = {}

    def exec_cmd(self, cmd, stdout=None, stdin=None,
                 retval=False, return_output=False, print_output=False,
                 current_wd=None, logger=None):
        devnull = open(os.devnull, 'w')
        if stdout:
            stdout = open(stdout, 'wb')
        elif return_output or print_output:
            stdout = subprocess.PIPE
        else:
            stdout = devnull
        if stdin:
            stdin = open(stdin, 'rb')

        start = Util.microseconds()
        if current_wd is not None:
            p = subprocess.Popen(cmd, cwd=current_wd, 
                                 stdout=stdout, stdin=stdin)
        else:
            p = subprocess.Popen(cmd, stdout=stdout, stdin=stdin)
        pid = p.pid
        self.active_procs[pid] = p
        output = p.communicate()
        end = Util.microseconds()
        if print_output:
            for o in output:
                if o:
                    print (o.decode('utf-8'))            
        del self.active_procs[pid]

        if retval:
            return p.returncode
        if return_output:
            return {'output': output[0].decode('utf-8'),
                    'exec_time': end - start,
                    'pid': pid}
        else:
            return {'exec_time': end - start,
                    'pid': pid}

    def end_active_processes(self):
        for pid, proc in self.active_procs.items():
            proc.terminate()
            time.sleep(0.5)
            alive = proc.poll()
            if alive is None:
                os.kill(pid, signal.SIGINT)
                
    @staticmethod
    def exception_info():
        exc_type, exc_obj, exc_tb = sys.exc_info()
        stack = traceback.format_exc()
        return str(stack)

    @staticmethod
    def bail(message, logger=None):
        print ('Bookmaker Fatal Error: ' + str(message))
        if logger is not None:
            logger.error('Fatal Error: ' + str(message))
        sys.exit(1)

    @staticmethod
    def microseconds():
        return time.time()

    @staticmethod
    def stats(data):
        sum = 0
        delta_sum = 0
        min = 0
        max = 0
        for value in data:
            if value > max:
                max = value
            if value < min:
                min = value
            sum += value
        mean = sum/len(data)
        for value in data:
            delta_sum += math.pow(mean - value, 2)
        var = delta_sum/len(data)
        sd =  math.sqrt(var)
        return {'mean': mean,
                'var': var,
                'sd': sd,
                'min': min,
                'max': max}

    @staticmethod
    def stats_hist(data, statobj):
        freq = {'below_2SD': [],
                'below_1SD': [],
                'below_mean': [],
                'above_mean': [],
                'above_1SD': [],
                'above_2SD': []}
        for value in data:
            if value < statobj['mean'] - statobj['sd']*2:
                freq['below_2SD'].append(value)
            if (value < statobj['mean'] - statobj['sd'] and
                value >= statobj['mean'] - statobj['sd']*2):
                freq['below_1SD'].append(value)
            if (value < statobj['mean'] and
                value >= statobj['mean'] - statobj['sd']):
                freq['below_mean'].append(value)
            if (value >= statobj['mean'] and
                value < statobj['mean'] + statobj['sd']):
                freq['above_mean'].append(value)
            if (value >= statobj['mean'] + statobj['sd'] and
                value < statobj['mean'] + statobj['sd']*2):
                freq['above_1SD'].append(value)
            if (value >= statobj['mean'] + statobj['sd']*2):
                freq['above_1SD'].append(value)
        return freq


