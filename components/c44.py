import os

from component import Component

class C44(Component):
    """
    Creates DjVu

    """

    args = ['slice', 'size', 'bpp', 'percent', 'dpi',
            'gamma', 'decibel', 'dbfrac', 'crcb',
            'crcbdelay', 'mask', 'in_file', 'out_file']

    executable = 'c44'

    def __init__(self, book):
        super(C44, self).__init__(C44.args)
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + self.book.identifier + '_derived'}
        self.book.add_dirs(dirs)

        
    def run(self):
        if not os.path.exists(self.in_file):
            raise IOError('Cannot find ' + self.in_file)
        try:
            self.execute()
        except Exception as e:
            raise e
