import os

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
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_Crop_init',
                                                 str(e),
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()



    def cropper_pipeline(self, start, end, crop):
        for leaf in range(start, end):
            try:
                self.Cropper.run(leaf, crop)
            except Exception as e:
                self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_Crop_cropper_pipeline',
                                                     str(e),
                                                     self.book.logger))
                self.ProcessHandler.ThreadQueue.join()

            else:
                exec_time = self.Cropper.get_last_exec_time()
                self.complete_process(leaf, exec_time)
