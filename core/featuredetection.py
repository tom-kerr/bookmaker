import os
import math
from collections import OrderedDict
import logging

from util import Util
from .operation import Operation
from environment import Environment
from datastructures import Crop
from standardcrop import StandardCrop

class FeatureDetection(Operation):
    """ Handles running various feature detectors on scanned book pages.
    """
    components = OrderedDict(
        [('pagedetector', {'class': 'PageDetector',
                           'callback': 'post_process'}),
         ('fastcornerdetection', {'class': 'FastCornerDetection',
                                  'callback': 'post_process'},),
         ('swclustering', {'class': 'SWClustering',
                           'callback': 'post_process'})])

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(FeatureDetection, self).__init__(FeatureDetection.components)
            self.init_components(self.book)
            if self.book.settings['respawn']:
                self.book.clean_dirs()
            if self.book.settings['respawn']:
                self.book.scandata.new(self.book.identifier, self.book.page_count,
                                       self.book.raw_image_dimensions,
                                       self.book.scandata_file)
        except (Exception, BaseException) as e:
            self.book.logger.error(str(e))
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))
                                      
    def pipeline(self, start=None, end=None):
        if None in (start, end):
            start, end = 0, self.book.page_count
        for leaf in range(start, end):
            self.book.logger.debug('...leaf ' + str(leaf) + ' of ' +
                                   str(self.book.page_count) + '...')                             
            leaf_exec_time = 0
            for item in self.components:
                component, callback = item
                cls = component.__class__.__name__
                try:
                    component.run(leaf, callback=callback)
                    exec_time = component.get_last_exec_time()
                    leaf_exec_time += exec_time
                except (Exception, BaseException) as e:
                    self.book.logger.error(str(e))
                    pid = self.make_pid_string('pipeline.'+ str(start))
                    self.ProcessHandler.join((pid, Util.exception_info()))  
                else:
                    self.complete_process(cls, leaf, leaf_exec_time)
                    self.book.logger.debug(
                        'leaf {} completed {}: {} Seconds'.\
                            format(leaf, 
                                   str(component.__class__.__name__),
                                   str(round(exec_time, 3)) ))                    
            self.book.logger.debug('Finished FeatureDetection processing leaf ' + 
                                   str(leaf) + ' in ' + str(round(leaf_exec_time, 3)) + 
                                   ' Seconds')
                             
    def post_process(self):
        self.SWClustering.analyse_noise()
        if self.book.settings['respawn']:
            self.book.pageCrop.xml_io('export')
        self.book.contentCrop.xml_io('export')        
        self.make_standard_crop()

    def make_standard_crop(self):
        standardcrop = StandardCrop(self.book)
        standardcrop.make_standard_crop()
