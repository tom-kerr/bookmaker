import os
import sys
import subprocess
import re
import math
import time

class Util:

    HALT = False

    @staticmethod
    def cmd(cmd, redirect=False, return_output=False, logger=None):
        if Util.HALT:
            Util.halt('Halting command ' + str(cmd), logger)
        if redirect is not False:
            if redirect == 'stdout':
                components = cmd.split(' > ')
                mode = 'wb'
            elif redirect == 'stdin':
                components = cmd.split(' < ')           
                mode = 'rb'
            cmd = components[0]
            components[1] = [re.sub("^ +", '', c) for c in components[1].split('^') if c is not ''][0]
            redir = open(str(components[1]), mode)
        else:
            redir = subprocess.PIPE

        cmd = [re.sub("^ +", '', c) for c in cmd.split('^') if c is not '']
                
        try:
            start = Util.microseconds()
            if redirect in ('stdout', False):
                p = subprocess.Popen(cmd, stdout=redir)
            elif redirect == 'stdin':
                p = subprocess.Popen(cmd, stdin=redir)
            output = p.communicate()
            #if p.returncode != 0:
            #    raise Exception('Non-Zero Return Value')  
            end = Util.microseconds()
        except Exception as e:
            Util.bail('\nCommand: ' + str(' '.join(cmd)) + ' \n\nException: ' + str(e), logger)

        if return_output:
            return  {'output': output[0], 
                     'exec_time': end - start,
                     'pid': p.pid}
        else:
            return {'exec_time': end - start,
                    'pid': p.pid}

    """
    @staticmethod
    def eval(cmd, return_output = False):
        try:
            start = Util.microseconds()
            output = eval(cmd)
            end = Util.microseconds()
        except Exception as e:
            Util.bail('failed to evaluate ' + str(cmd) + ' ' + str(e))
        if return_output:
            return {'output':output,
                    'exec_time':end - start}
        else:
            return {'exec_time':end - start}
            """


    @staticmethod
    def halt(message, logger=None):
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


