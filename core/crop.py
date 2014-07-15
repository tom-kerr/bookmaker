import os

from util import Util
from .operation import Operation
from environment import Environment


class Crop(Operation):
    """ Handles the cropping of images.
    """
    components = [('cropper', 'Cropper')]
                              
    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(Crop, self).__init__(Crop.components)
            self.init_components(self.book)
        except (Exception, BaseException):
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))            

    @Operation.multithreaded
    def cropper_pipeline(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 0, self.book.page_count
        for leaf in range(start, end):
            self.book.logger.debug('Cropping leaf ' + str(leaf))
            try:
                self.Cropper.run(leaf, **kwargs)
            except (Exception, BaseException):
                pid = self.make_pid_string('cropper_pipeline')
                self.ProcessHandler.join((pid, Util.exception_info()))
            else:
                exec_time = self.Cropper.get_last_exec_time()
                self.complete_process('Cropper', leaf, exec_time)
