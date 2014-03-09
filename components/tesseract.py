import os
import json

from lxml import html
from lxml.etree import ParseError
from collections import OrderedDict

from environment import Environment
from .component import Component
from datastructures import Box

class Tesseract(Component):
    """ Performs OCR related tasks.
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
        super(Tesseract, self).__init__()
        self.book = book
        dirs = {'tesseract_ocr': self.book.root_dir + '/' + \
                    self.book.identifier + '_tesseract_ocr',
                'cropped': self.book.root_dir + '/' + \
                    self.book.identifier + '_cropped'}
        self.book.add_dirs(dirs)

    def run(self, leaf, in_file=None, out_base=None, 
            lang='eng', psm='-psm 3', hocr='hocr', hook=None, **kwargs):
        leafnum = '%04d' % leaf
        if not in_file:
            in_file = (self.book.dirs['cropped'] + '/' +
                       self.book.identifier + '_' + str(leafnum) + '.JPG')
        if not os.path.exists(in_file):
            raise OSError(in_file + ' does not exist.')

        if not out_base:
            out_base = (self.book.dirs['tesseract_ocr'] + '/' +
                        self.book.identifier + '_' + str(leafnum))

        lang = '-l ' + str(lang)

        kwargs.update({'in_file': in_file,
                       'out_base': out_base,
                       'language': lang,
                       'psm': psm, 
                       'hocr': hocr})
        
        output = self.execute(kwargs, return_output=True)
        if hook:
            self.execute_hook(hook, leaf, output, **kwargs)
        else:
            return output

    def get_hocr_files(self, start=None, end=None):
        if None in (start, end):
            start, end = 1, self.book.page_count-1
        files = {}
        for leaf in range(start, end):
            leafnum = "%04d" % leaf
            base = self.book.dirs['tesseract_ocr'] + '/' + \
                self.book.identifier + '_' + leafnum
            if os.path.exists(base + '.html'):
                try:
                    os.rename(base + '.html', base + '.hocr')
                except OSError:
                    raise OSError('Failed to rename tesseract hocr output for leaf ' 
                                  + str(leaf))
            if os.path.exists(base + '.hocr'):
                files[leaf] = base + '.hocr'
        return files

    def parse_html(self, filename):
        try:
            parsed = html.parse(filename)
        except IOError as e:
            self.book.logger.warning('Failed to open ' + filename + 
                                     '\n' + str(e))
            return None
        except ParseError as e:
            self.book.logger.warning('lxml failed to parse file ' + filename +
                                     '\n' + str(e))
            return None
        else:
            return parsed

    def parse_hocr(self, filename):
        parsed = self.parse_html(filename)
        if parsed is None: 
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
                    xword = word.find_class('ocrx_word')
                    if xword and xword[0].text:
                        txt = xword[0].text
                        line.words[num].text = json.dumps(txt)
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
        string += '\n(page %s %s %s %s' % (page.box.l, page.box.t, 
                                           page.box.r, page.box.b)
        for par in page.paragraphs:
            for line in par.lines:
                string += '\n (line %s %s %s %s' % \
                    (line.box.l, (page.box.b - line.box.b),
                     line.box.r, (page.box.b - line.box.t))
                for word in line.words:
                    string += '\n  (word %s %s %s %s %s)' % \
                        (word.l, (page.box.b - word.b),
                         word.r, (page.box.b - word.t), word.text)
                string += ')'
        string += ')'
        #print (string)
        return string
