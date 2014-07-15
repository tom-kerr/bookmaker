import os
import glob
import re
from lxml import etree
import shutil
import zipfile

from PyPDF2 import PdfFileReader, PdfFileWriter

from util import Util
from .operation import Operation
from components.tesseract import Tesseract


class PDF(Operation):
    """ Handles PDF creation 
    """
    components = [('hocr2pdf', 'HOCR2Pdf')]

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(PDF, self).__init__(PDF.components)
            self.init_components(self.book)
        except (Exception, BaseException):
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))

    @Operation.multithreaded
    def make_pdf_with_hocr2pdf(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        else:
            if  start == 0:
                start = 1
            if end == self.book.page_count:
                end = self.book.page_count-1
        kwargs.update({'start': start, 'end': end})
        try:
            self.hocr2pdf_pipeline(**kwargs)
        except (Exception, BaseException):
            pid = self.make_pid_string('make_pdf_with_hocr.'+str(start))
            self.ProcessHandler.join((pid, Util.exception_info()))

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
            except (Exception, BaseException):
                raise
            else:
                exec_time = self.HOCR2Pdf.get_last_exec_time()
                self.complete_process('HOCR2Pdf', leaf, exec_time)                
            if not os.path.exists(out_file):
                raise OSError('cannot make pdf: failed to create ' + out_file)
        if os.path.exists(dummy_hocr):
            try:
                os.remove(dummy_hocr)
            except OSError as e:
                self.book.logger.warning('Failed to remove dummy hocr; ' + str(e))

    def on_success(self, *args, **kwargs):
        self.assemble_pdf_with_pypdf(**kwargs)
            
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
            try:
                os.remove(pdf_file)
            except (OSError, IOError):
                self.book.logger.warning('failed to remove pdf file ' + 
                                         pdf_file)
        try:
            with open(self.book.dirs['derived'] + '/' + 
                      self.book.identifier + '.pdf', 'wb') as pdf:
                pdf_out.write(pdf)
        except (OSError, IOError):
            raise
            

class Djvu(Operation):
    """ Handles DjVu creation 
    """
    components = [('c44', 'C44'),
                  ('djvused', 'Djvused'),
                  ('djvm', 'Djvm')]
                  
    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(Djvu, self).__init__(Djvu.components)
            self.init_components(self.book)
        except (Exception, BaseException):
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))

    @Operation.multithreaded
    def make_djvu_with_c44(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        else:
            if  start == 0:
                start = 1
            if end == self.book.page_count:
                end = self.book.page_count-1
        kwargs.update({'start': start, 'end': end})
        try:
            self.c44_pipeline(**kwargs)
            self.djvused_add_ocr_pipeline(**kwargs)
        except (Exception, BaseException):
            pid = self.make_pid_string('make_djvu_with_c44.' + str(start))
            self.ProcessHandler.join((pid, Util.exception_info()))

    def c44_pipeline(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        for leaf in range(start, end):
            try:
                self.C44.run(leaf, **kwargs)
            except (Exception, BaseException):
                raise
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
                if hocr is None:
                    continue
                self.book.logger.debug('djvused: leaf ' + str(leaf))
                ocrlisp = Tesseract.hocr2lisp(hocr)
                
                try:
                    with open(self.tmpocrlisp, 'w') as f:
                        f.write(ocrlisp)
                except IOError:
                    raise

                if not os.path.exists(self.set_text):
                    try:
                        with open(self.set_text, 'w') as f:
                            f.write("select 1; set-txt " + self.tmpocrlisp + "; save")
                    except IOError:
                        raise

                kwargs.update({'options': '-f',
                               'script': self.set_text})                
                try:
                    self.Djvused.run(leaf, **kwargs)
                except (Exception, BaseException):
                    raise
                else:
                    exec_time = self.Djvused.get_last_exec_time()
                    self.complete_process('Djvused', leaf, exec_time)

    def on_success(self, *args, **kwargs):
        self.assemble_djvu_with_djvm(**kwargs)
        
    def assemble_djvu_with_djvm(self, **kwargs):
        self.book.logger.debug('assembling djvu with djvm')
        kwargs['options'] = '-c'
        try:
            self.Djvm.run(**kwargs)
            self.Djvm.remove_in_files()
        except (Exception, BaseException):
            pid = self.make_pid_string('assemble_with_djvm')
            self.ProcessHandler.join((pid, Util.exception_info()))
        else:
            exec_time = self.Djvm.get_last_exec_time()
            self.complete_process('Djvm', range(1, self.book.page_count-1), 
                                  exec_time)
        finally:
            for f in (self.tmpocrlisp, self.set_text):
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except OSError as e:
                    self.book.logger.warning('Failed to remove ' + 
                                             f + '; ' + str(e))


class PlainText(Operation):
    """ Handles Plain-text creation 
    """
    components = [('tesseract', 'Tesseract')]

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(PlainText, self).__init__(PlainText.components)
            self.init_components(self.book)
            self.book.add_dirs({'derived': self.book.root_dir + '/' + 
                                self.book.identifier + '_derived'})
        except (Exception, BaseException):
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))

    @Operation.multithreaded        
    def make_full_plain_text(self, start=None, end=None, **kwargs):
        self.book.logger.info('Creating Full Plain Text...')
        self.files = {}
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        else:
            if  start == 0:
                start = 1
            if end == self.book.page_count:
                end = self.book.page_count-1
        self.get_ocr_files(start, end, **kwargs)
        
    def get_ocr_files(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        files = self.Tesseract.get_hocr_files(start, end)
        if not files:
            for leaf in range(start, end):
                self.Tesseract.run(leaf, **kwargs)
                exec_time = self.Tesseract.get_last_exec_time()
                self.complete_process('Tesseract', leaf, exec_time)
            files = self.Tesseract.get_hocr_files(start, end)
        else:
            self.complete_process('Tesseract', range(1, self.book.page_count), 0)
        self.files.update(files)

    def on_success(self, *args, **kwargs):
        self.assemble_ocr_text()
        
    def assemble_ocr_text(self):
        ocr_data = []
        for leaf, f in self.files.items():
            text = self.Tesseract.parse_hocr(f)
            if text is not None:
                ocr_data.append(text)
        try:
            out_file = open(self.book.dirs['derived'] + '/' +
                            self.book.identifier + '_full_plain_text.txt', 'w')
        except IOError:
            pid = self.make_pid_string('make_full_plain_text')
            self.ProcessHandler.join((pid, Util.exception_info()))
        string = ''
        for page in ocr_data:
            for paragraph in page.paragraphs:
                for line in paragraph.lines:
                    string += line.text_content() + "\n"
            string += "\n\n"
        try:
            out_file.write(string)
        except (Exception, BaseException):
            pid = self.make_pid_string('make_full_plain_text')
            self.ProcessHandler.join((pid, Util.exception_info()))
        else:
            self.book.logger.info('Finished deriving full plain text.')


class EPUB(Operation):
    """ Handles EPUB creation.
    """    
    components = [('cropper', 'Cropper'),
                  ('tesseract', 'Tesseract')]
                              
    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(EPUB, self).__init__(self.components)
            self.init_components(self.book)
            self.book.add_dirs({'derived': self.book.root_dir + '/' + 
                                self.book.identifier + '_derived'})
        except (Exception, BaseException):
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))

    @Operation.multithreaded
    def make_epub(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        self.book.logger.info('Creating EPUB...')
        self.parsed_hocr = {}
        hocr_files = self.get_hocr_files(start, end)
        for leaf, f in hocr_files.items():
            self.parsed_hocr[leaf] = self.Tesseract.parse_hocr(f)

    def get_hocr_files(self, start=None, end=None, **kwargs):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        files = self.Tesseract.get_hocr_files(start, end)
        if not files:
            for leaf in range(start, end):
                self.Tesseract.run(leaf, **kwargs)
                exec_time = self.Tesseract.get_last_exec_time()
                self.complete_process('Tesseract', leaf, exec_time)
            files = self.Tesseract.get_hocr_files(start, end)
        else:
            self.complete_process('Tesseract', range(1, self.book.page_count), 0)
        return files

    def hocr_to_epub(self, hocr):        
        main_doc = etree.Element('html')
        body = etree.SubElement(main_doc, 'body')
        for leaf, page in hocr.items():
            if leaf in self.book.cropBox.pagination:
                pagination = self.book.cropBox.pagination[leaf]
                if pagination:
                    if pagination[-1] in ('!', '?'):
                        pagination = pagination[:-1]
                    pdiv = etree.SubElement(body, 'div')
                    pdiv.set('class', 'newpage')
                    pdiv.set('id', 'page-'+str(pagination))
            for par in page.paragraphs:
                p = etree.SubElement(body, 'p')
                for line in par.lines:
                    text = []
                    for word in line.words:
                        if word.text:
                            text.append(word.text.lstrip('"').rstrip('"'))
                    p.text = " ".join(text)
        tree = etree.ElementTree(main_doc)
        try:
            with open(self.book.dirs['derived']+ '/OEBPS/' + 'main.html', 'wb') as f:
                tree.write(f, pretty_print=True)
        except (OSError, IOError):
            pid = self.make_pid_string('hocr_to_epub')
            self.ProcessHandler.join((pid, Util.exception_info()))        

    def write_mimetype(self):
        mimetype = 'application/epub+zip'
        mimefile = self.book.dirs['derived'] + '/mimetype'
        try:
            with open(mimefile, 'w') as f:
                f.write(mimetype)
        except (IOError, OSError):
            pid = self.make_pid_string('write_mimetype')
            self.ProcessHandler.join((pid, Util.exception_info))

    def write_container(self):
        cdir = self.book.dirs['derived'] + '/META-INF'
        if not os.path.exists(cdir):
            try:
                os.mkdir(cdir, 0o755)
            except OSError:
                pid = self.make_pid_string('write_container')
                self.ProcessHandler.join((pid, Util.exception_info()))
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
            with open(container_file, 'wb') as container:
                doc.write(container, pretty_print=True)
        except (IOError, OSError):
            pid = self.make_pid_string('write_container')
            self.ProcessHandler.join((pid, Util.exception_info()))

    def create_OEBPS(self):
        OEBPS_dir = self.book.dirs['derived'] + '/' + 'OEBPS'
        if not os.path.exists(OEBPS_dir):
            try:
                os.mkdir(OEBPS_dir, 0o755)
            except OSError:
                pid = self.make_pid_string('write_OEBPS')
                self.ProcessHandler.join((pid, Util.exception_info()))        
        self.hocr_to_epub(self.parsed_hocr)

    def create_opf(self):
        doc = etree.Element('package')
        #doc.set('xmlns', {'dc': 'http://purl.org/dc/elements/1.1/'})
        doc.set('xmlns', 'http://www.idpf.org/2007/opf') 
        doc.set('version', '2.0')
        doc.set('unique-identifier', 'bookid')
        metadata = etree.SubElement(doc, 'metadata')
        manifest = etree.SubElement(doc, 'manifest')
        main = etree.SubElement(manifest, 'item')
        main.set('href', 'main.html')
        main.set('id', 'main')
        main.set('media-type', 'application/xhtml+xml')
        spine = etree.SubElement(doc, 'spine')
        spine.set('toc', '') #todo
        mspine = etree.SubElement(spine, 'itemref')
        mspine.set('idref', 'main')
        tree = etree.ElementTree(doc)
        try:
            with open(self.book.dirs['derived'] + '/OEBPS/' + 'content.opf', 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True, 
                           pretty_print=True)
        except (OSError, IOError):
            pid = self.make_pid_string('create_opf')
            self.ProcessHandler.join((pid, Util.exception_info()))
                
    def on_success(self, *args, **kwargs):
        self.assemble_epub()

    def assemble_epub(self):
        self.write_mimetype()
        self.write_container()
        self.create_OEBPS()
        self.create_opf()
        self.zip_up()
        
    def zip_up(self):
        epub_dir = self.book.dirs['derived'] + '/epub'
        if os.path.exists(epub_dir):
            shutil.rmtree(epub_dir)
        os.mkdir(epub_dir, 0o755)
        z = zipfile.ZipFile(self.book.dirs['derived'] + '/' + 
                            self.book.identifier + '.epub', mode='w')
        for i in ('mimetype', 'META-INF', 'OEBPS'):
            shutil.move(self.book.dirs['derived'] + '/' + i, 
                        self.book.dirs['derived'] + '/epub/')
                                
        z.write(self.book.dirs['derived'] + '/epub/mimetype', 
                arcname='mimetype')
        z.write(self.book.dirs['derived'] + '/epub/OEBPS/content.opf', 
                arcname='OEBPS/content.opf')
        z.write(self.book.dirs['derived'] + '/epub/OEBPS/main.html', 
                arcname='OEBPS/main.html')
        z.write(self.book.dirs['derived'] + '/epub/META-INF/container.xml', 
                arcname='META-INF/container.xml')
        z.close()
