import os
from lxml import html
from glob import glob
from collections import OrderedDict

from util import Util
from imageops import ImageOps
from datastructures import Box


class OCR:
    
    languages = OrderedDict([('Bulgarian', 'bul'), ('Catalonian', 'cat'), ('Chinese (simplified)', 'chin_sim'), 
                             ('Chinese (traditional)', 'chin_tra'), ('Cherokee', 'chr'), ('Danish (fraktur)', 'dan-frak'), 
                             ('Danish', 'dan'), ('Dutch (fraktur)', 'deu-frak'), ('Dutch', 'deu'), ('Greek', 'ell'), 
                             ('English', 'eng'), ('Finnish', 'fin'), ('French', 'fra'), ('Hungarian', 'hun'), ('Indonesian', 'ind'), 
                             ('Italian', 'ita'), ('Japanese', 'jpn'), ('Korean', 'kor'), ('Latvian', 'lav'), ('Lithuanian', 'lit'), 
                             ('Norwegian', 'nor'), ('Polish', 'pol'), ('Portuguese', 'por'), ('Romanian', 'ron'), ('Russian', 'rus'), 
                             ('Serbian', ''), ('Slovakian', 'slv'), ('Swedish (fraktur)', 'swe-frak'), ('Swedish', 'swe'), 
                             ('Spanish', ''), ('Tagalog', 'tgl'), ('Turkish', 'tur'), ('Ukranian', 'ukr'), ('Vietnamese', 'vie')])


    def __init__(self, book):
        self.book = book
        self.ImageOps = ImageOps()
        self.ocr_data = None


    def tesseract_hocr_pipeline(self, ProcessHandler, start, end, lang='eng'):
        for leaf in range(start, end):
            
            #if page is blank, we skip ocr on it
            if not self.book.contentCrop.box[leaf].is_valid():
                self.ImageOps.complete(leaf, 'skipped ocr')
                continue

            leafnum = '%04d' % leaf
            cropped_file = self.book.dirs['cropped'] + '/' + self.book.identifier + '_' + str(leafnum) + '.pnm'
            html_out = self.book.dirs['ocr'] + '/' + self.book.identifier + '_' + str(leafnum)
            cmd = 'tesseract'
            args = {'in_file': cropped_file,
                    'out_base': html_out,
                    'psm': '-psm 3',
                    'language': lang,
                    'hocr': 'hocr'}
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, 'ocr')
            self.ImageOps.complete(leaf, 'finished ocr')

            if os.path.exists(html_out + '.html'):
                try:
                    os.rename(html_out + '.html', html_out + '.hocr')
                except:
                    Util.bail('failed to rename tesseract hocr output for leaf ' + str(leaf))

                    
    def parse_hocr_stack(self):
        hocr_files = self.get_hocr_files()
        if not hocr_files:
            Util.bail('cannot parse hocr stack: no files found')
        self.ocr_data = []
        for leaf, hocr in hocr_files.items():
            self.ocr_data.append(OCR.parse_hocr(hocr))
        return True


    def get_hocr_files(self):
        files = {}
        for leaf in range(1, self.book.page_count-1):
            leafnum = "%04d" % leaf            
            f = self.book.dirs['ocr'] + '/' + self.book.identifier + '_' + leafnum + '.hocr'
            if os.path.exists(f):
                files[leaf] = f
        if len(files) < 1:
            return False
        else:
            return files
        

    @staticmethod
    def parse_hocr(filename):
        try:
            hocr = open(filename, 'r')
        except IOError:
            print 'failed to open ' + filename
            return False

        try:
            parsed = html.parse(hocr)
        except:
            print 'lxml failed to parse file'
            return False

        root = parsed.getroot()
        page = root.find_class('ocr_page')
        dims = page[0].get('title').split(';')[1].split(' ')
        page[0].box = Box()
        page[0].box.set_dimension('l', int(dims[2]))
        page[0].box.set_dimension('t', int(dims[3]))
        page[0].box.set_dimension('r', int(dims[4]))
        page[0].box.set_dimension('b', int(dims[5]))
        page[0].paragraphs = root.find_class('ocr_par')
        for par in page[0].paragraphs:
            par.lines = par.find_class('ocr_line')
            for line in par.lines:
                dims = line.get('title').split(' ')
                line.box = Box()
                line.box.set_dimension('l', int(dims[1]))
                line.box.set_dimension('t', int(dims[2]))
                line.box.set_dimension('r', int(dims[3]))
                line.box.set_dimension('b', int(dims[4]))
                words = line.find_class('ocr_word')
                xwords = line.find_class('ocrx_word')
                line.words = []
                for num, word in enumerate(words):
                    line.words.append(Box())
                    dims = word.get('title').split(' ')
                    line.words[num].set_dimension('l', int(dims[1]))
                    line.words[num].set_dimension('t', int(dims[2]))
                    line.words[num].set_dimension('r', int(dims[3]))
                    line.words[num].set_dimension('b', int(dims[4]))
                    if xwords[num].text is None:
                        line.words[num].text = ''
                    else:
                        line.words[num].text = xwords[num].text.replace("\"", "'").encode('utf-8')
        return page[0]


    @staticmethod
    def hocr2lisp(hocr_page):
        if hocr_page is None:
            return False
        string = ''
        page = hocr_page
        #for page in hocr:
        string += '\n(page %s %s %s %s' % (page.box.l, page.box.t, page.box.r, page.box.b) 
        for par in page.paragraphs:
            for line in par.lines:
                string += '\n (line %s %s %s %s' % (line.box.l, (page.box.b - line.box.b), 
                                                    line.box.r, (page.box.b - line.box.t))
                for word in line.words:
                    string += '\n  (word %s %s %s %s \"%s\")' % (word.l, (page.box.b - word.b), 
                                                                 word.r, (page.box.b - word.t), word.text)
                string += ')'
        string += ')'
        return string
