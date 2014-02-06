import os
from environment import Environment
from .component import Component
from .cornerfilter import CornerFilter

class FastCornerDetection(Component):
    """ Fast Corner Detection
    """

    args = ['t', 's', 'n', 'l', 'in_file', 'out_file']
    executable = (Environment.current_path +
                  '/bin/cornerDetection/./fast_' +
                  Environment.platform + '_' + Environment.architecture)

    def __init__(self, book):
        super(FastCornerDetection, self).__init__()
        self.book = book
        dirs = {'corners': self.book.root_dir + '/' + \
                    self.book.identifier + '_corners',
                'cornered_scaled': self.book.root_dir + '/' + \
                    self.book.identifier + '_cornered_scaled'}
        self.book.add_dirs(dirs)
        self.book.corner_data = {}
        self.CornerFilter = CornerFilter(book)
        
    def run(self, leaf, in_file=None, out_file=None, 
            t='-t 44', s='', n='-n 9', l='-l', callback=None, **kwargs):
        leafnum = '%04d' % leaf
        if not in_file:
            in_file = (self.book.dirs['scaled'] + '/' +
                       self.book.identifier + '_scaled_' +
                       leafnum + '.jpg')
        if not out_file:
            out_file = (self.book.dirs['corners'] + '/' +
                        self.book.identifier + '_corners_' +
                        leafnum + '.txt')
        if not os.path.exists(in_file):
            raise OSError(in_file + ' does not exist.')
        
        kwargs.update({'in_file': in_file, 
                       'out_file': out_file, 
                       't': t, 's': s, 
                       'n': n, 'l': l})

        if self.book.settings['respawn']:
            output = self.execute(kwargs, return_output=True)
            if self.book.settings['make_cornered_scaled']:
                kwargs.update({'l': '', 'out_file': 
                               (self.book.dirs['cornered_scaled'] + '/' +
                                self.book.identifier + '_cornered_scaled_' +
                                leafnum + '.jpg')})
                self.execute(kwargs)
        else:
            output = None
        if callback:
            self.execute_callback(callback, leaf, output, **kwargs)
        else:
            return output
        
    def post_process(self, *args, **kwargs):
        leaf = args[0]
        leafnum = '%04d' % leaf
        window_file = (self.book.dirs['windows'] + '/' +
                       self.book.identifier + '_window_' +
                       leafnum + '.txt')
        if self.book.settings['respawn']:
            self.book.pageCrop.skew(self.book.scaled_center_point[leaf]['x'],
                                    self.book.scaled_center_point[leaf]['y'],
                                    leaf)
            self.book.pageCropScaled.box[leaf] = \
                self.book.pageCrop.scale_box(leaf, scale_factor = 4)
            self.CornerFilter.run(leaf)
            self.book.corner_data[leaf] = self.parse_corner_data(window_file)
        else:
            self.book.corner_data[leaf] = self.parse_corner_data(window_file)

    @staticmethod
    def parse_corner_data(window_file):
        corner_data = {}
        if os.path.exists(window_file):
            with open(window_file, "r") as D:
                contents = D.readline()
                contents = contents.split(" ")
                if len(contents) == 5:
                    window_width = contents[0]
                    window_height = contents[1]
                    corner_count = contents[2]
                    x_variance = contents[3]
                    y_variance = contents[4]
                    corner_data = {'window_width': window_width,
                                   'window_height': window_height,
                                   'corner_count': corner_count,
                                   'x_variance': x_variance,
                                   'y_variance': x_variance }
        return corner_data




