import os
import glob
import re

from lxml import etree

from util import Util
from .operation import Operation
from components.tesseract import Tesseract

class Djvu(Operation):
    components = {'c44': {'class': 'C44',
                          'callback': None},
                  'djvused': {'class': 'Djvused',
                              'callback': None},
                  'djvm': {'class': 'Djvm',
                           'callback': None}}

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(Djvu, self).__init__(Djvu.components)
            self.init_components(self.book)
        except:
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))

    def make_djvu_with_c44(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        else:
            if  start == 0:
                start = 1
            if end == self.book.page_count:
                end = self.book.page_count-1
        kwargs.update({'start': start, 'end': end})
        self.c44_pipeline(**kwargs)
        self.djvused_add_ocr_pipeline(**kwargs)

    def c44_pipeline(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        for leaf in range(start, end):
            try:
                self.C44.run(leaf, **kwargs)
            except:
                pid = self.make_pid_string('c44_pipeline')
                self.ProcessHandler.join((pid, Util.exception_info()))
            else:
                exec_time = self.C44.get_last_exec_time()
                self.complete_process('C44', leaf, exec_time)
        
    def djvused_add_ocr_pipeline(self, start=None, end=None, **kwargs):
        tesseract = Tesseract(self.book)
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        hocr_files = tesseract.get_hocr_files()
        self.tmpocrlisp = self.book.dirs['derived'] + '/tmpocrlisp.txt'
        self.set_text = self.book.dirs['derived'] +"/set_text"
        for leaf in range(start, end):
            if leaf in hocr_files:
                hocr = tesseract.parse_hocr(hocr_files[leaf])
                #print (hocr, hocr_files[leaf])
                if hocr is None:
                    continue
                self.book.logger.debug('djvused: leaf ' + str(leaf))
                ocrlisp = Tesseract.hocr2lisp(hocr)
                #print (ocrlisp)
                
                try:
                    with open(self.tmpocrlisp, 'w') as f:
                        f.write(ocrlisp)
                except IOError:
                    pid = self.make_pid_string('djvused_add_ocr_pipeline')
                    self.ProcessHandler.join((pid, Util.exception_info()))

                if not os.path.exists(self.set_text):
                    try:
                        with open(self.set_text, 'w') as f:
                            f.write("select 1; set-txt " + self.tmpocrlisp + "; save")
                    except IOError:
                        pid = self.make_pid_string('djvused_add_ocr_pipeline')
                        self.ProcessHandler.join((pid, Util.exception_info()))

                kwargs.update({'options': '-f',
                               'script': self.set_text})                
                try:
                    self.Djvused.run(leaf, **kwargs)
                except:
                    pid = self.make_pid_string('djvused_add_ocr_pipeline')
                    self.ProcessHandler.join((pid, Util.exception_info()))
                else:
                    exec_time = self.Djvused.get_last_exec_time()
                    self.complete_process('Djvused', leaf, exec_time)
        
    def assemble_djvu_with_djvm(self, **kwargs):
        self.book.logger.debug('assembling djvu with djvm')
        kwargs['options'] = '-c'
        try:
            self.Djvm.run(**kwargs)
            self.Djvm.remove_in_files()
        except:
            pid = self.make_pid_string('assemble_with_djvm')
            self.ProcessHandler.join((pid, Util.exception_info()))
        else:
            exec_time = self.Djvm.get_last_exec_time()
            self.complete_process('Djvm', range(1, self.book.page_count-1), exec_time)
        finally:
            for f in (self.tmpocrlisp, self.set_text):
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as e:
                    self.book.logger.warning('Failed to remove ' + f +'; ' + str(e))

