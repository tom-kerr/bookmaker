import os
from lxml import html
from collections import OrderedDict

from environment import Environment
from component import Component
from datastructures import Box

class Tesseract(Component):
    """
    Tesseract
    ---------

    Performs OCR related tasks.

    """

    languages = OrderedDict([
        ('Bulgarian', 'bul'),
        ('Catalonian', 'cat'),
        ('Chinese (simplified)', 'chin_sim'),
        ('Chinese (traditional)', 'chin_tra'),
        ('Cherokee', 'chr'),
        ('Danish (fraktur)', 'dan-frak'),
        ('Danish', 'dan'),
        ('Dutch (fraktur)', 'deu-frak'),
        ('Dutch', 'deu'),
        ('Greek', 'ell'),
        ('English', 'eng'),
        ('Finnish', 'fin'),
        ('French', 'fra'),
        ('Hungarian', 'hun'),
        ('Indonesian', 'ind'),
        ('Italian', 'ita'),
        ('Japanese', 'jpn'),
        ('Korean', 'kor'),
        ('Latvian', 'lav'),
        ('Lithuanian', 'lit'),
        ('Norwegian', 'nor'),
        ('Polish', 'pol'),
        ('Portuguese', 'por'),
        ('Romanian', 'ron'),
        ('Russian', 'rus'),
        ('Serbian', ''),
        ('Slovakian', 'slv'),
        ('Swedish (fraktur)', 'swe-frak'),
        ('Swedish', 'swe'),
        ('Spanish', ''),
        ('Tagalog', 'tgl'),
        ('Turkish', 'tur'),
        ('Ukranian', 'ukr'),
        ('Vietnamese', 'vie')])

    args = ['in_file','out_base','language','psm', 'hocr']
    executable = 'tesseract'

    def __init__(self, book):
        super(Tesseract, self).__init__(Tesseract.args)
        self.book = book
        dirs = {'tesseract_ocr': self.book.root_dir + '/' + self.book.identifier + '_tesseract_ocr',
                'cropped': self.book.root_dir + '/' + self.book.identifier + '_cropped'}
        self.book.add_dirs(dirs)


    def run(self):
        if not os.path.exists(self.in_file):
            raise IOError(self.in_file + ' does not exist.')
        try:
            self.execute()
        except Exception as e:
            raise e


    def parse_hocr_files(self):
        hocr_files = self.get_hocr_files()
        if not hocr_files:
            raise IOError('Could not parse hocr files: no files found.')
        self.ocr_data = []
        for leaf, hocr in hocr_files.items():
            self.ocr_data.append(OCR.parse_hocr(hocr))
        return True


    def get_hocr_files(self):
        files = {}
        for leaf in range(1, self.book.page_count-1):
            leafnum = "%04d" % leaf
            base = self.book.dirs['tesseract_ocr'] + '/' + self.book.identifier + '_' + leafnum
            if os.path.exists(base + '.html'):
                try:
                    os.rename(base + '.html', base + '.hocr')
                except:
                    raise IOError('Failed to rename tesseract hocr output for leaf ' + str(leaf))
            if os.path.exists(base + '.hocr'):
                files[leaf] = base + '.hocr'
        return files


    @staticmethod
    def parse_hocr(filename):
        try:
            hocr = open(filename, 'r')
        except IOError:
            print 'failed to open ' + filename
            return None

        try:
            parsed = html.parse(hocr)
        except Exception as e:
            print 'lxml failed to parse file ' + filename
            return None

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
                line.words = []
                for num, word in enumerate(words):
                    line.words.append(Box())
                    dims = word.get('title').split(' ')
                    line.words[num].set_dimension('l', int(dims[1]))
                    line.words[num].set_dimension('t', int(dims[2]))
                    line.words[num].set_dimension('r', int(dims[3]))
                    line.words[num].set_dimension('b', int(dims[4]))
                    if word.text:
                        line.words[num].text = word.text.replace("\"", "'").encode('utf-8')
                    else:
                        line.words[num].text = ''
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
