import os
from environment import Environment
from component import Component
from cornerfilter import CornerFilter

class FastCornerDetection(Component):
    """
    Fast Corner Detection
    ---------------------



    """

    args = ['t', 's', 'n', 'l', 'in_file', 'out_file']
    executable = (Environment.current_path +
                  '/bin/cornerDetection/./fast_' +
                  Environment.platform + '_' + Environment.architecture)

    def __init__(self, book):
        super(FastCornerDetection, self).__init__(FastCornerDetection.args)
        self.book = book
        dirs = {'corners': self.book.root_dir + '/' + self.book.identifier + '_corners',
                'cornered_scaled': self.book.root_dir + '/' + self.book.identifier + '_cornered_scaled'}
        self.book.add_dirs(dirs)
        self.book.corner_data = {}
        self.CornerFilter = CornerFilter(book)
        

    def run(self, leaf):
        self.book.logger.message('Getting corners for leaf '+ str(leaf) + '...', 'featureDetection')
        leafnum = '%04d' % leaf
        self.in_file = (self.book.dirs['scaled'] + '/' +
                        self.book.identifier + '_scaled_' +
                        leafnum + '.jpg')
        self.out_file = (self.book.dirs['corners'] + '/' +
                         self.book.identifier + '_corners_' +
                         leafnum + '.txt')
        if not os.path.exists(self.in_file):
            raise IOError(self.in_file + ' does not exist!')

        self.t = '-t 44'
        self.s = ''
        self.n = '-n 9'
        self.l = '-l'

        if self.book.settings['respawn']:
            try:
                self.execute()
                self.book.pageCrop.skew(self.book.scaled_center_point[leaf]['x'],
                                        self.book.scaled_center_point[leaf]['y'],
                                        leaf)
                self.book.pageCropScaled.box[leaf] = self.book.pageCrop.scale_box(leaf, scale_factor = 4)
                self.CornerFilter.run(leaf)
                self.parse_corner_data(leaf)
                if self.book.settings['make_cornered_scaled']:
                    leafnum = '%04d' % leaf
                    self.l = ''
                    self.out_file = (self.book.dirs['cornered_scaled'] + '/' +
                                     self.book.identifier + '_cornered_scaled_' +
                                     leafnum + '.jpg')
                    self.execute()
            except Exception as e:
                raise e


    def parse_corner_data(self, leaf):
        leafnum = '%04d' % leaf
        window_file = (self.book.dirs['windows'] + '/' +
                       self.book.identifier + '_window_' +
                       leafnum + '.txt')
        if os.path.exists(window_file):
            D = open(window_file, "r")
            contents = D.readline()
            contents = contents.split(" ")
            if len(contents) is not 5:
                self.book.corner_data[leaf] = None
                return False
            window_width = contents[0]
            window_height = contents[1]
            corner_count = contents[2]
            x_variance = contents[3]
            y_variance = contents[4]
            self.book.corner_data[leaf] =  {'window_width': window_width,
                                            'window_height': window_height,
                                            'corner_count': corner_count,
                                            'x_variance': x_variance,
                                            'y_variance': x_variance }
        else:
            self.book.corner_data[leaf] = None




