import os
import glob
import re

from PyPDF2 import PdfFileReader, PdfFileWriter

from util import Util
from .operation import Operation
from components.tesseract import Tesseract


class PDF(Operation):
    components = {'hocr2pdf': {'class': 'HOCR2Pdf',
                               'callback': None}}

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(PDF, self).__init__(PDF.components)
            self.init_components(self.book)
        except:
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))
        
    def make_pdf_with_hocr2pdf(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        else:
            if  start == 0:
                start = 1
            if end == self.book.page_count:
                end = self.book.page_count-1
        kwargs.update({'start': start, 'end': end})
        self.hocr2pdf_pipeline(**kwargs)

    def hocr2pdf_pipeline(self, start=None, end=None, **kwargs):
        tesseract = Tesseract(self.book)
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        hocr_files = tesseract.get_hocr_files()
        dummy_hocr = self.book.dirs['derived'] + '/html.hocr'
        for leaf in range(start, end):
            self.book.logger.debug('hocr2pdf: leaf ' + str(leaf))
            leafnum = '%04d' % leaf
            if leaf in hocr_files:
                hocr = hocr_files[leaf]
                self.book.logger.debug('found hocr: leaf ' + str(leaf))
            else:
                self.book.logger.debug('dummy hocr: leaf ' + str(leaf))
                if not os.path.exists(dummy_hocr):
                    hocr = open(dummy_hocr, 'w')
                    hocr.write('<html/>')
                    hocr.close()
                hocr = dummy_hocr

            out_file = self.book.dirs['derived'] + '/' + \
                self.book.identifier + '_' + leafnum + '.pdf'
            
            kwargs.update({'hocr_file': hocr,
                           'out_file': out_file})
            try:
                self.HOCR2Pdf.run(leaf, **kwargs)
            except:
                pid = self.make_pid_string('make_pdf_hocr_pipeline')
                self.ProcessHandler.join((pid, Util.exception_info()))
            else:
                exec_time = self.HOCR2Pdf.get_last_exec_time()
                self.complete_process('HOCR2Pdf', leaf, exec_time)
                
            if not os.path.exists(out_file):
                pid = self.make_pid_string('make_pdf_hocr_pipeline')
                self.ProcessHandler.join((pid, 'cannot make pdf: failed to create ' +
                                          out_file,))
        try:
            if os.path.exists(dummy_hocr):
                os.remove(dummy_hocr)
        except Exception as e:
            self.book.logger.warning('Failed to remove dummy hocr; ' + str(e))
            
    def assemble_pdf_with_pypdf(self, **kwargs):
        self.book.logger.debug('assembling pdf with pypdf')
        pdf_files = glob.glob(self.book.dirs['derived'] + '/*.pdf')
        pdf_files = sorted([p for p in pdf_files 
                            if re.search('_[0-9]+.pdf$', p)])
        pdf_out = PdfFileWriter()
        for pdf_file in pdf_files:
            self.book.logger.debug('pypdf adding ' + pdf_file)
            pdf_page = PdfFileReader(open(pdf_file, 'rb'))
            pdf_out.addPage(pdf_page.getPage(0))
            os.remove(pdf_file)
        pdf = open(self.book.dirs['derived'] + '/' + 
                   self.book.identifier + '.pdf', 'wb')
        pdf_out.write(pdf)
        pdf.close()

