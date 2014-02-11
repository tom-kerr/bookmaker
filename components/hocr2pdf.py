import os

from .component import Component

class HOCR2Pdf(Component):
    """ Creates Pdf pages from hocr and images.
    """

    args = ['no_image', 'sloppy', 'resolution',
            ['-i', 'in_file'], ['-o','out_file'], 'hocr_file']
    executable = 'hocr2pdf'

    def __init__(self, book):
        super(HOCR2Pdf, self).__init__()
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + \
                    self.book.identifier + '_derived',
                'cropped': self.book.root_dir + '/' + \
                    self.book.identifier + '_cropped'}
        self.book.add_dirs(dirs)        

    def run(self, leaf, in_file=None, out_file=None, hocr_file=None,
            no_image=None, sloppy=None, ppi=None, resolution=None, 
            callback=None, **kwargs):
        leafnum = '%04d' % leaf
        if not in_file:
            in_file = (self.book.dirs['cropped'] + '/' +
                       self.book.identifier + '_' + leafnum + '.JPG')
        if not os.path.exists(in_file):
            raise OSError(in_file + ' does not exist.')
        if not out_file:
            out_file = (self.book.dirs['derived'] + '/' +
                        self.book.identifier + '_' + leafnum + '.pdf')
        if no_image:
            no_image = '-n'
        if sloppy:
            sloppy = '-s'
        if ppi:
            resolution = ['-r', str(ppi)]
            
        kwargs.update({'in_file': in_file,
                       'out_file': out_file,
                       'hocr_file': None,
                       'no_image': no_image,
                       'sloppy': sloppy,
                       'resolution': resolution})
        
        stdin = hocr_file            
        output = self.execute(kwargs, return_output=True, stdin=stdin)
        if callback:
            self.execute_callback(callback, leaf, output, **kwargs)
        else:
            return output
