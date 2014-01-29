import os
import glob
import re

from PyPDF2 import PdfFileReader, PdfFileWriter
from lxml import etree

from util import Util
from .operation import Operation


class Derive(Operation):
    """ Handles the processing for various export formats.
    """

    components = {'tesseract': {'class': 'Tesseract',
                                'callback': None},
                  'c44': {'class': 'C44',
                          'callback': None},
                  'djvused': {'class': 'Djvused',
                              'callback': None},
                  'djvm': {'class': 'Djvm',
                           'callback': None},
                  'hocr2pdf': {'class': 'HOCR2Pdf',
                               'callback': None}}

    """
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
