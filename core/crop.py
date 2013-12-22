import os

from util import Util
from operation import Operation
from environment import Environment


class Crop(Operation):
    """
    Handles the cropping of images.

    """

    components = {'cropper': 'Cropper'}

    def __init__(self, ProcessHandler, book):
        self.Processhandler = ProcessHandler
        self.book = book
        try:
            super(Crop, self).__init__(Crop.components)
            self.init_components( [self.book,] )
        except:
            self.ProcessHandler.join((self.book.identifier + '_Crop_init',
                                      Util.exception_info(),
                                      self.book.logger))
            

    def cropper_pipeline(self, start, end, crop):
        for leaf in range(start, end):
            self.book.logger.message('Cropping leaf ' + str(leaf))
            try:
                self.Cropper.run(leaf, crop)
            except:
                self.ProcessHandler.join((self.book.identifier + '_Crop_cropper_pipeline',
                                          Util.exception_info(),
                                          self.book.logger))
            else:
                exec_time = self.Cropper.get_last_exec_time()
                self.complete_process(leaf, exec_time)
