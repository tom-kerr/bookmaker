import os
import math

from operation import Operation
from environment import Environment
from datastructures import Crop

class FeatureDetection(Operation):
    """
    Handles running various feature detectors on scanned book pages.

    """

    components = {'pagedetector': 'PageDetector',
                  'fastcornerdetection': 'FastCornerDetection',
                  'swclustering': 'SWClustering'}

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book

        self.book.pageCropScaled = Crop('pageCrop', self.book.page_count,
                                        self.book.raw_image_dimensions,
                                        scale_factor=4)

        self.book.contentCropScaled = Crop('contentCrop', self.book.page_count,
                                           self.book.raw_image_dimensions,
                                           scale_factor=4)
        try:
            super(FeatureDetection, self).__init__(FeatureDetection.components)
            self.init_components([(self.book),(self.book),(self.book)])
            self.book.clean_dirs()
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_FeatureDetection_init',
                                                 str(e),
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()



    def pipeline(self):
        self.book.logger.message('Entering FeatureDetection pipeline...','global')
        if self.book.settings['respawn']:
            self.book.scandata.new(self.book.identifier, self.book.page_count,
                                   self.book.raw_image_dimensions,
                                   self.book.scandata_file)
        for leaf in range(0, self.book.page_count):
            self.book.logger.message('...leaf ' + str(leaf) + ' of ' +
                                     str(self.book.page_count) + '...',
                                     ('global','featureDetection'))
            leaf_exec_time = 0
            for component in self.components:
                try:
                    component.run(leaf)
                    exec_time = component.get_last_exec_time()
                    leaf_exec_time += exec_time
                except Exception as e:
                    self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                         '_FeatureDetection_pipeline',
                                                         str(e), self.book.logger))
                    self.ProcessHandler.ThreadQueue.join()
                else:
                    self.book.logger.message('\t\t\t\t\t\t{}: {} Seconds'.
                                             format( str(component.__class__.__name__),
                                                     str(round(exec_time, 3)) ),
                                                     'featureDetection')

            self.complete_process(leaf, leaf_exec_time)
            self.book.logger.message('Finished Processing leaf ' +
                                     str(leaf) + ' in ' + str(round(leaf_exec_time, 3)) + ' Seconds\n\n',
                                     ('global', 'featureDetection'))

        self.SWClustering.analyse_noise()
        if self.book.settings['respawn']:
            self.book.pageCrop.xml_io('export')
        self.book.contentCrop.xml_io('export')
        self.make_standard_crop()


    def make_standard_crop(self):
        standardcrop = StandardCrop(self.book)
        standardcrop.make_standard_crop()
