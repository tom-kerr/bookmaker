import os

from component import Component

class HOCR2Pdf(Component):
    """
    Creates Pdf pages from hocr and images.

    """

    args = ['no_image', 'sloppy', 'resolution',
            ['-i', 'in_file'], ['-o','out_file'], 'hocr_file']
    executable = 'hocr2pdf'

    def __init__(self, book):
        super(HOCR2Pdf, self).__init__(HOCR2Pdf.args)
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + self.book.identifier + '_derived',
                'cropped': self.book.root_dir + '/' + self.book.identifier + '_cropped'}
        self.book.add_dirs(dirs)
        

    def run(self):
        if not os.path.exists(self.in_file):
            raise IOError('cannot make pdf: input image file ' + str(self.in_file) + ' missing')
        try:
            stdin = self.hocr_file
            self.hocr_file = None
            self.execute(stdin=stdin)
        except Exception as e:
            raise e
