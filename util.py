import os
import sys
import subprocess
import re
import math
import time

class Util:

    active_procs = []

    @staticmethod
    def exec_cmd(cmd, stdout=None, stdin=None,
                 retval=False, return_output=False, print_output=False,
                 current_wd=None, logger=None):
        devnull = open(os.devnull, 'w')
        if stdout:
            stdout = open(stdout, 'wb')
        elif return_output:
            stdout = subprocess.PIPE
        else:
            stdout = devnull
        if stdin:
            stdin = open(stdin, 'rb')
            #print cmd
        try:
            start = Util.microseconds()
            if current_wd is not None:
                p = subprocess.Popen(cmd, cwd=current_wd, stdout=stdout, stdin=stdin)
            else:
                p = subprocess.Popen(cmd, stdout=stdout, stdin=stdin)

            output = p.communicate()
            
            if print_output:
                print output
            end = Util.microseconds()

        except Exception as e:
            fname, lineno = Util.exception_info()
            raise Exception(str(e) + ' (' + fname + ', line ' + str(lineno) + ')')

        if retval:
            return p.returncode

        if return_output:
            return {'output': output[0],
                    'exec_time': end - start,
                    'pid': p.pid}
        else:
            return {'exec_time': end - start,
                    'pid': p.pid}


    @staticmethod
    def end_active_processes():
        for p in Util.active_procs:
            try:
                p.terminate()
            except:
                pass


    @staticmethod
    def exception_info():
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        return (fname, exc_tb.tb_lineno)


    @staticmethod
    def halt(message=None, logger=None):
        if logger is not None:
            logger.message('Halting...', 'global')
        sys.exit(0)


    @staticmethod
    def bail(message, logger=None):
        print 'Fatal Error: ' + str(message)
        if logger is not None:
            logger.message('Fatal Error: ' + str(message), 'global')
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


