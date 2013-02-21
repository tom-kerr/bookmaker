import sys
import os
import re
from util import Util
from environment import Environment

class ImageOps:

    ops = {
        'pageDetection': { 
            'args' : ['in_file','rotation_direction','out_file','debug_out' ],
            'cmd' : '{PATH}/bin/pageDetector/./pageDetector^ {in_file} {rotation_direction} {out_file}' ,
            'message':'RUNNING PAGE DETECTOR',            
            },
        'fastCornerDetection': {
            'args': ['in_file','out_file','t','s','n','l'],
            'cmd': '{PATH}/bin/cornerDetection/./fast_{PLAT_ARCH}^ -t {t} {s} -n {n} {l} {in_file} {out_file}',
            'message': 'RUNNING FAST CORNER DETECTOR',            
            },
        'cornerFilter': { 
            'args': ['in_file', 'out_file', 'l', 'r', 't', 'b', 'thumb_width', 'thumb_height'],
            'cmd': '{PATH}/bin/cornerFilter/cornerFilter^ {in_file} {out_file} {l} {r} {t} {b} {thumb_width} {thumb_height}',
            'message': 'RUNNING CORNER FILTER',            
            },
        'slidingWindow': {
            'args': ['in_file','out_file','window_width','window_height','skew_angle','center_x','center_y','log'],
            'cmd': '{PATH}/bin/clusterAnalysis/slidingWindow/./slidingWindow^ {in_file} {out_file} {window_width} {window_height} {skew_angle} {center_x} {center_y}',
            'message': 'RUNNING SLIDING WINDOW CLUSTER ANALYSIS',            
            },
        'rawtothumb': {
            'args': ['in_file','scale_factor','rotation_direction','out_file'],
            'cmd': '{PATH}/bin/./jpegScale^ {in_file} {scale_factor} {rotation_direction} {out_file}',
            'message': 'SCALING RAW',            
            },
        'jpegtopnm': {
            'args': ['in_file','out_file'],
            'cmd': 'jpegtopnm^ {in_file} > {out_file}',
            'message': 'CREATING PNM FROM RAW',            
            },
        'pnmflip': {
            'args': ['rotation','in_file','out_file'],
            'cmd': 'pnmflip^ -r{rotation} {in_file} > {out_file}',
            'message': 'FLIPPING PNM',            
            },
        'pnmnorm': {
            'args': ['in_file','out_file'],
            'cmd': 'pnmnorm^ {in_file} > {out_file}',
            'message': 'NORMALIZING PNM',            
            },
        'pnminvert': {
            'args': ['in_file','out_file'],
            'cmd': 'pnminvert^ {in_file} > {out_file}',
            'message': 'INVERTING PNM',            
            },
        'pamcut': {
            'args': ['l','r','t','b','in_file','out_file'],
            'cmd': 'pamcut^ -left={l} -right={r} -top={t} -bottom={b} {in_file} > {out_file}',
            'message': 'CUTTING OUT AREA',            
            },
        'ppmtopgm': {
            'args': ['in_file','out_file'],
            'cmd': 'ppmtopgm^ {in_file} > {out_file}',
            'message': 'CREATING GRAYSCALE PNM',            
            },
        'pnmrotate': {
            'args': ['rotation','in_file','out_file'],
            'cmd': 'pnmrotate^ {rotation} {in_file} > {out_file}',
            'message': 'ROTATING PNM',            
            },
        'tesseract':{
            'args': ['in_file','out_base','language','psm', 'hocr'],
            'cmd': 'tesseract^ {in_file} {out_base} -l {language} {psm} {hocr}',
            'message': 'RUNNING TESSERACT',
            },
        'hocr2pdf': {
            'args': ['in_file', 'out_file', 'hocr_file'],
            'cmd': 'hocr2pdf^ -i^ {in_file} -o^ {out_file} < {hocr_file}',
            'message': 'RUNNING HOCR2PDF'
            },
        'c44': {
            'args': ['slice', 'bpp', 'percent', 'decibel', 'dbfrac', 'mask', 'dpi', 'gamma', 'in_file', 'out_file'],
            'cmd': 'c44^ {slice} {bpp} {percent} {decibel} {dbfrac} {mask} {dpi} {gamma} {in_file} {out_file}',
            'message': 'RUNNING C44'
            },
        'djvused': {
            'args': ['options', 'script', 'djvu_file'],
            'cmd': 'djvused^ {options} {script} {djvu_file}',
            'message': 'RUNNING DJVUSED'
            },
        'djvm': {
            'args': ['options', 'out_file', 'in_files'],
            'cmd': 'djvm^ {options} {out_file} {in_files}',
            'message': 'RUNNING DJVM'
            }
        }


    def __init__(self):
        self.exec_times = {}
        for cmd in ImageOps.ops:
            self.exec_times[cmd] = { 'total_exec_time': 0,
                                     'avg_exec_time': None,
                                     'image_exec_times': {} }
            self.completed_ops = {}
            self.total_exec_time = 0
            self.avg_exec_time = 0
            
        
    def execute(self, leaf, cmd, args, logger, log='global', current_wd=None,
                redirect=False, return_output=False, print_output=False):
        if cmd in ImageOps.ops:
            CMD = ImageOps.ops[cmd]['cmd']
        else:
            Util.bail('invalid image operation')                
        for arg, value in args.iteritems():
            if type(value) == type(list()):
                value = ''.join([str(v) + '^' for v in value if value not in (None, '', ' ')])
            elif value not in (None, '', ' '):
                value = str(value) + '^'
            if arg in ImageOps.ops[cmd]['args']:
                pattern = '\{'+str(arg)+'\}'
                CMD = re.sub(pattern, value, CMD)
            else:
                Util.bail('invalid argument "' +str(arg)+ ' ' +str(value)+ '" sent to imgops')
        CMD = re.sub('\{PATH\}', Environment.current_path, CMD)

        if cmd == 'fastCornerDetection':
            CMD = re.sub('\{PLAT_ARCH\}', Environment.platform + '_' + Environment.architecture, CMD)

        logger.message(ImageOps.ops[cmd]['message'], log)
        logger.message(CMD.replace('^', ' '), log)
        try:
            output = Util.cmd(CMD, current_wd=current_wd, logger=logger, 
                              redirect=redirect, return_output=return_output, print_output=print_output)
        except Exception as e:
            raise Exception(str(e))
        self.current_pid = output['pid']
        self.exec_times[cmd]['total_exec_time'] += output['exec_time']
        if leaf not in self.exec_times[cmd]['image_exec_times'].keys():
            self.exec_times[cmd]['image_exec_times'][leaf] = 0
        self.exec_times[cmd]['image_exec_times'][leaf] += output['exec_time']
        self.exec_times[cmd]['avg_exec_time'] = (self.exec_times[cmd]['total_exec_time']/
                                                 len(self.exec_times[cmd]['image_exec_times']))
        self.total_exec_time += output['exec_time']
        self.avg_exec_time = self.total_exec_time/len(self.exec_times[cmd]['image_exec_times'])
        logger.message('executed ' + cmd + ' in ' + str(output['exec_time']), log);
        self.complete(leaf, cmd + str(output['exec_time']))
        if return_output:
            return output['output']


    def complete(self, leaf, op_string):
        if leaf not in self.completed_ops:
            self.completed_ops[leaf] = []
        self.completed_ops[leaf].append(op_string)


    def return_total_leaf_exec_time(self, leaf):
        total = 0        
        for command in ImageOps.ops.items():
            cmd = command[0]
            if cmd in self.exec_times:
                if leaf in self.exec_times[cmd]['image_exec_times']:
                    total += self.exec_times[cmd]['image_exec_times'][leaf]
        return total
