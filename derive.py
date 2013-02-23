import os
from pyPdf import PdfFileReader, PdfFileWriter

from util import Util
from imageops import ImageOps
from ocr import OCR


class Derive:


    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        self.OCR = OCR(ProcessHandler, self.book)
        self.ImageOps = ImageOps()


    def epub(self):
        self.book.logger.message('Creating EPUB...')
        self.ImageOps.complete('epub') 



    def write_mimetype(self):
        mimetype = 'application/epub+zip'
        mimefile = self.book.dirs['derived'] + '/mimetype'
        try:
            f = open(mimefile, 'w')
            f.write(mimetype)
            f.close
        except:
            Util.bail('Failed to create mimetype', self.book.logger)
        



    def djvu(self, ocr_data=None):
        self.book.logger.message('Creating Searchable DjVu...')
        hocr_files = self.OCR.get_hocr_files()
        djvu_files = []
        for leaf in range(1, self.book.page_count-1):
            leafnum = '%04d' % leaf
            in_file = self.book.dirs['cropped'] + '/' + self.book.identifier + '_' + leafnum + '.pnm'
            if not os.path.exists(in_file):
                self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_djvu',
                                                'cannot make djvu: input image file(s) missing',
                                                self.book.logger))
                self.ProcessHandler.ThreadQueue.join()
                
            out_file = self.book.dirs['derived'] + '/' + self.book.identifier + '_' + leafnum + '.djvu'
            cmd = 'c44'
            args = {'slice': '', 
                    'bpp': '', 
                    'percent': '', 
                    'decibel': '', 
                    'dbfrac': '', 
                    'mask': '', 
                    'dpi': '', 
                    'gamma': '', 
                    'in_file': in_file,
                    'out_file': out_file}
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation')
            djvu_files.append(out_file)

            #if ocr_data is None:
            if leaf in hocr_files:
                hocr = self.OCR.parse_hocr(hocr_files[leaf])
                ocrlisp = self.OCR.hocr2lisp(hocr)            
                tmpocrlisp = self.book.dirs['derived'] + '/tmpocrlisp.txt'
                f = open(tmpocrlisp, 'w')
                f.write(ocrlisp)
                f.close()

                set_text = self.book.dirs['derived'] +"/set_text"
                if not os.path.exists(set_text):
                    f = open(set_text, 'w')
                    f.write("select 1; set-txt " + tmpocrlisp + "; save")
                    f.close()

                djvu_file = out_file
                cmd = 'djvused'
                args = {'options': "-f",
                        'script': set_text,
                        'djvu_file': djvu_file}
                self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation')
        
        djvu_out = self.book.dirs['derived'] + '/' + self.book.identifier + '.djvu '
        cmd = 'djvm'
        args = {'options': '-c',
                'out_file': djvu_out,
                'in_files': djvu_files}
        self.ImageOps.execute('djvm', cmd, args, self.book.logger)
        self.ImageOps.complete('djvu') 
        self.book.logger.message('Finished DjVu.')
        

        try:
            os.remove(tmpocrlisp)
        except:
            pass
        try:
            os.remove(set_text)
        except:
            pass
        
        for djvu_file in djvu_files:
            try:
                os.remove(djvu_file)
            except:
                pass
        

    def pdf(self):
        self.book.logger.message('Creating Searchable PDF...')
        hocr_files = self.OCR.get_hocr_files()
        if not hocr_files: 
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_pdf',
                                            'cannot make pdf: no hocr files found', 
                                            self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        pdf_out = PdfFileWriter()
        for leaf in range(1, self.book.page_count-1):
            if leaf in hocr_files:
                hocr = hocr_files[leaf]
            else:
                dummy_hocr = self.book.dirs['derived'] + '/html.hocr'
                if not os.path.exists(dummy_hocr):
                    hocr = open(dummy_hocr, 'w')
                    hocr.write('<html/>')
                    hocr.close()
                hocr = dummy_hocr
            leafnum = '%04d' % leaf
            in_file = self.book.dirs['cropped'] + '/' + self.book.identifier + '_' + leafnum + '.pnm'
            if not os.path.exists(in_file):
                self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_pdf',
                                                'cannot make pdf: input image file ' + str(in_file) + ' missing', 
                                                self.book.logger))
                self.ProcessHandler.ThreadQueue.join()
            out_file = self.book.dirs['derived'] + '/' + self.book.identifier + '_' + leafnum + '.pdf'
            cmd = 'hocr2pdf'
            args = {'in_file': in_file,
                    'out_file': out_file,
                    'hocr_file': hocr}
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdin')
            pdf_page = PdfFileReader(file(out_file, 'rb'))
            pdf_out.addPage(pdf_page.getPage(0))
            os.remove(out_file)
        try:
            os.remove(dummy_hocr)
        except:
            pass
        pdf = file(self.book.dirs['derived'] + '/' + self.book.identifier + '.pdf', 'wb')
        pdf_out.write(pdf)
        pdf.close()
        self.ImageOps.complete('pdf') 
        self.book.logger.message('Finished PDF.')
        
                                
    def full_plain_text(self, ocr_data=None):        
        self.book.logger.message('Creating Full Plain Text...')
        if ocr_data is None:
            if self.OCR.parse_hocr_stack():
                ocr_data = self.OCR.ocr_data
            else:
                self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_text',
                                                'Unable to derive full plain text: no ocr data found', 
                                                self.book.logger))
                self.ProcessHandler.ThreadQueue.join()
        try:
            out_file = open(self.book.dirs['derived'] + '/' + self.book.identifier + '_full_plain_text.txt', 'w')
        except IOError:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_text',
                                            'Could not open full plain text for writing', 
                                            self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        string = ''
        for page in ocr_data:
            for paragraph in page.paragraphs:
                for line in paragraph.lines:
                    string += line.text_content() + "\n"
            string += "\n\n"
        try:
            out_file.write(string)
        except:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_text',
                                            'failed to write full plain text', 
                                            self.book.logger))
            self.ProcessHandler.ThreadQueue.join()
        self.ImageOps.complete('text') 
        self.book.logger.message('Finished Text.')
        
