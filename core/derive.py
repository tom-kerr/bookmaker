import os
from pyPdf import PdfFileReader, PdfFileWriter
from lxml import etree

from operation import Operation


class Derive(Operation):
    """
    Handles the processing for various export formats.

    """
    components = {'tesseract': 'Tesseract',
                  'c44': 'C44',
                  'djvused': 'Djvused',
                  'djvm': 'Djvm',
                  'hocr2pdf': 'HOCR2Pdf'}

    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(Derive, self).__init__(Derive.components)
            self.init_components( [self.book,self.book,
                                   self.book,self.book,
                                   self.book] )
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_Derive_init',
                                                 str(e),
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()


    def make_djvu_with_c44(self, start, end, *args):
        djvu_files = self.c44_pipeline(start, end, args)
        self.djvused_add_ocr_pipeline(start, end)
        self.assemble_djvu_with_djvm(djvu_files)


    def c44_pipeline(self, start, end, slices=None, size=None,
                     bpp=None, percent=None, dpi=None, gamma=None, decibel=None,
                     dbfrac=None, crcbnorm=None, crcbhalf=None, crcbfull=None,
                     crcbnone=None, crcbdelay=None, mask=None):
        djvu_files = []
        for leaf in range(start, end):
            if slices:
                self.C44.slice = '-slice ' + str(slices)
            else:
                self.C44.slice = None
            if size:
                self.C44.size = '-size ' + str(size)
            else:
                self.C44.size = None
            if bpp:
                self.C44.bpp = '-bpp ' + str(bpp)
            else:
                self.C44.bpp = None
            if percent:
                self.C44.percent = '-percent ' + str(percent)
            else:
                self.C44.percent = None
            if dpi:
                self.C44.dpi = '-dpi ' + str(dpi)
            else:
                self.C44.dpi = None
            if gamma:
                self.C44.gamma = '-gamma ' + str(gamma)
            else:
                self.C44.gamma = None
            if decibel:
                self.C44.decibel = '-decibel ' + str(decibel)
            else:
                self.C44.decibel = None
            if dbfrac:
                self.C44.dbfrac = '-dbfrac ' + str(dbfrac)
            else:
                self.C44.dbfrac = None
            if crcbnorm:
                self.C44.crcb = '-crcbnormal'
            elif crcbhalf:
                self.C44.crcb = '-crcbhalf'
            elif crcbfull:
                self.C44.crcb = '-crcbfull'
            elif crcbnone:
                self.C44.crcb = '-crcbnone'
            else:
                self.C44.crcb = None
            if crcbnorm or crcbhalf:
                if crcbdelay:
                    self.C44.crcbdelay = '-crcbdelay ' + str(crcbdelay)
                else:
                    self.C44.crcbdelay = None
            if mask:
                self.C44.mask = '-mask ' + str(mask)
            else:
                self.C44.mask = None

            leafnum = "%04d" % leaf
            self.C44.in_file = (self.book.dirs['cropped'] + '/' +
                                self.book.identifier + '_' + leafnum + '.JPG')
            self.C44.out_file =( self.book.dirs['derived'] + '/' +
                                 self.book.identifier + '_' + leafnum + '.djvu')

            try:
                self.C44.run()
            except Exception as e:
                self.ProcessHandler.ThreadQueue.put((self.book.identifier + '_Derive_c44_pipeline',
                                                     str(e),
                                                     self.book.logger))
                self.ProcessHandler.ThreadQueue.join()
            djvu_files.append(self.C44.out_file)
        return djvu_files


    def djvused_add_ocr_pipeline(self, start, end):
        hocr_files = self.Tesseract.get_hocr_files()
        for leaf in range(start, end):
            if leaf in hocr_files:
                hocr = self.Tesseract.parse_hocr(hocr_files[leaf])
                if hocr is None:
                    continue
                ocrlisp = self.Tesseract.hocr2lisp(hocr)
                tmpocrlisp = self.book.dirs['derived'] + '/tmpocrlisp.txt'
                try:
                    with open(tmpocrlisp, 'w') as f:
                        f.write(ocrlisp)
                        f.close()
                except IOError as e:
                    self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                         '_Derive_djvused_add_ocr_pipeline',
                                                         str(e),
                                                         self.book.logger))
                    self.ProcessHandler.ThreadQueue.join()

                set_text = self.book.dirs['derived'] +"/set_text"
                if not os.path.exists(set_text):
                    try:
                        with open(set_text, 'w') as f:
                            f.write("select 1; set-txt " + tmpocrlisp + "; save")
                            f.close()
                    except IOError as e:
                        self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                             '_Derive_djvused_add_ocr_pipeline',
                                                             str(e),
                                                             self.book.logger))
                        self.ProcessHandler.ThreadQueue.join()

                self.Djvused.options = '-f'
                self.Djvused.script = set_text

                leafnum = "%04d" % leaf
                self.Djvused.djvu_file = (self.book.dirs['derived'] + '/' +
                                          self.book.identifier + '_' + leafnum + '.djvu')

                try:
                    self.Djvused.run()
                except Exception as e:
                    self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                         '_Derive_djvused_add_ocr_pipeline',
                                                         str(e),
                                                         self.book.logger))
                    self.ProcessHandler.ThreadQueue.join()
        try:
            os.remove(tmpocrlisp)
        except:
            pass
        try:
            os.remove(set_text)
        except:
            pass


    def assemble_djvu_with_djvm(self, djvu_files):
        self.Djvm.out_file = self.book.dirs['derived'] + '/' + self.book.identifier + '.djvu '
        self.Djvm.options = '-c'
        self.Djvm.in_files = djvu_files
        try:
            self.Djvm.run()
            self.Djvm.remove_in_files()
        except Exception as e:
            self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                 '_Derive_assemble_with_djvm',
                                                 str(e),
                                                 self.book.logger))
            self.ProcessHandler.ThreadQueue.join()


    def make_pdf_with_hocr2pdf(self, start, end,
                          no_image=None, sloppy=None, ppi=None):
        pdf_files = self.hocr2pdf_pipeline(start, end, no_image, sloppy, ppi)
        self.assemble_pdf_with_pypdf(pdf_files)


    def hocr2pdf_pipeline(self, start, end,
                          no_image=None, sloppy=None, ppi=None):
        hocr_files = self.Tesseract.get_hocr_files()
        pdf_files = []
        for leaf in range(start, end):
            if leaf in hocr_files:
                hocr = hocr_files[leaf]
            else:
                dummy_hocr = self.book.dirs['derived'] + '/html.hocr'
                if not os.path.exists(dummy_hocr):
                    hocr = open(dummy_hocr, 'w')
                    hocr.write('<html/>')
                    hocr.close()
                hocr = dummy_hocr

            if no_image:
                self.HOCR2Pdf.no_image = '-n'
            else:
                self.HOCR2Pdf.no_image = None
            if sloppy:
                self.HOCR2Pdf.sloppy = '-s'
            else:
                self.HOCR2Pdf.sloppy = None
            if ppi:
                self.HOCR2Pdf.resolution = '-r ' + str(ppi)
            else:
                self.HOCR2Pdf.resolution = None

            self.HOCR2Pdf.hocr_file = hocr

            leafnum = '%04d' % leaf
            self.HOCR2Pdf.in_file = (self.book.dirs['cropped'] + '/' +
                                     self.book.identifier + '_' + leafnum + '.JPG')
            self.HOCR2Pdf.out_file = (self.book.dirs['derived'] + '/' +
                                      self.book.identifier + '_' + leafnum + '.pdf')

            try:
                self.HOCR2Pdf.run(leaf)
            except Exception as e:
                self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                     '_Derive_make_pdf_hocr_pipeline',
                                                     str(e),
                                                     self.book.logger))
                self.ProcessHandler.ThreadQueue.join()

            if not os.path.exists(self.HOCR2Pdf.out_file):
                self.ProcessHandler.ThreadQueue.put((self.book.identifier +
                                                     '_Derive_make_pdf_hocr_pipeline',
                                                     'cannot make pdf: failed to create ' +
                                                     self.HOCR2Pdf.out_file,
                                                     self.book.logger))
                self.ProcessHandler.ThreadQueue.join()
            else:
                pdf_files.append(self.HOCR2Pdf.out_file)
        try:
            os.remove(dummy_hocr)
        except:
            pass
        return pdf_files


    def assemble_pdf_with_pypdf(self, pdf_files):
        pdf_out = PdfFileWriter()
        for pdf_file in pdf_files:
            pdf_page = PdfFileReader(file(pdf_file, 'rb'))
            pdf_out.addPage(pdf_page.getPage(0))
            os.remove(pdf_file)
        pdf = file(self.book.dirs['derived'] + '/' + self.book.identifier + '.pdf', 'wb')
        pdf_out.write(pdf)
        pdf.close()













    def epub(self):
        self.book.logger.message('Creating EPUB...')
        #self.write_mimetype()
        #self.write_container()
        self.ImageOps.complete(self.book.identifier + '_epub')


    def write_container(self):
        try:
            os.mkdir(self.book.dirs['derived'] + '/META-INF', 0755)
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
        self.ImageOps.complete(self.book.identifier +'_text')
        self.book.logger.message('Finished Text.')

