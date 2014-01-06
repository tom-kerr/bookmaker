import os

from util import Util
from .operation import Operation
from datastructures import Box


class OCR(Operation):

    components = {'tesseract': {'class': 'Tesseract',
                                'callback': None}}

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        self.ocr_data = None
        try:
            super(OCR, self).__init__(OCR.components)
            self.init_components(self.book)
        except:
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))

    def tesseract_hocr_pipeline(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        for leaf in range(start, end):
            #if page is blank, we skip ocr on it
            #if not self.book.contentCrop.box[leaf].is_valid():
            #    self.complete_process(leaf, None)
            #    continue            
            try:
                self.Tesseract.run(leaf, **kwargs)
            except:
                pid = self.make_pid_string('tesseract_hocr_pipeline')
                self.ProcessHandler.join((pid, Util.exception_info()))

