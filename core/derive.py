import os
import glob
import re

from PyPDF2 import PdfFileReader, PdfFileWriter
from lxml import etree

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
            print ('raising')
            raise Exception('ASDsd')
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
        hocr_files = tesseract.get_hocr_files(start, end)
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




    """ 
class EPUB(Operation):

    def __init__(self):
        pass

    def epub(self):
        self.book.logger.message('Creating EPUB...')
        #self.write_mimetype()
        #self.write_container()
        self.ImageOps.complete(self.book.identifier + '_epub')


    def write_container(self):
        try:
            os.mkdir(self.book.dirs['derived'] + '/META-INF', 0o755)
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_epub_container',
                                                 'Failed to create META-INF.',
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        container_file = self.book.dirs['derived'] + '/META-INF/container.xml'
        root = etree.Element('container')
        root.set('version', '1.0')
        root.set('xmlns', 'urn:oasis:names:tc:opendocument:xmlns:container')
        rootfiles = etree.SubElement(root, 'rootfiles')
        rootfile = etree.SubElement(rootfiles, 'rootfile')
        rootfile.set('media-type', 'application/oebps-package+xml')
        rootfile.set('full-path', 'OEBPS/content.opf')
        doc = etree.ElementTree(root)
        try:
            container = open(container_file, 'w')
            doc.write(container, pretty_print=True)
            container.close()
        except:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_epub_container',
                                                 'Failed to write container.xml.',
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()



    def write_mimetype(self):
        mimetype = 'application/epub+zip'
        mimefile = self.book.dirs['derived'] + '/mimetype'
        try:
            f = open(mimefile, 'w')
            f.write(mimetype)
            f.close
        except:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_epub_mimetype',
                                                 'Failed to create mimetype.',
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()


    def full_plain_text(self, ocr_data=None):
        self.book.logger.message('Creating Full Plain Text...')
        if ocr_data is None:
            if self.Tesseract.parse_hocr_files():
                ocr_data = self.Tesseract.ocr_data
            else:
                self.ProcessHandler.join((self.book.identifier + '_text',
                                          'Unable to derive full plain text: no ocr data found',
                                          self.book.logger))
        try:
            out_file = open(self.book.dirs['derived'] + '/' +
                            self.book.identifier + '_full_plain_text.txt', 'w')
        except IOError:
            self.ProcessHandler.join((self.book.identifier + '_text',
                                      'Could not open full plain text for writing',
                                      self.book.logger))

        string = ''
        for page in ocr_data:
            for paragraph in page.paragraphs:
                for line in paragraph.lines:
                    string += line.text_content() + "\n"
            string += "\n\n"
        try:
            out_file.write(string)
        except:
            self.ProcessHandler.join((self.book.identifier + '_text',
                                      'failed to write full plain text',
                                      self.book.logger))
 
            #self.ImageOps.complete(self.book.identifier +'_text')
        self.book.logger.message('Finished Text.')

        """
