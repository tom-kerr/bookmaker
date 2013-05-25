import os
from environment import Environment
from component import Component
from cornerfilter import CornerFilter

class FastCornerDetection(Component):
    """
    Fast Corner Detection
    ---------------------



    """

    args = ['in_file', 'out_file', 't', 's', 'n', 'l']
    executable = (Environment.current_path +
                  '/bin/cornerDetection/./fast_' +
                  Environment.platform + '_' + Environment.architecture)

    def __init__(self, book):
        super(FastCornerDetection, self).__init__(FastCornerDetection.args)
        self.book = book
        self.book.corner_data = {}
        self.CornerFilter = CornerFilter(book)


    def run(self, leaf):
        self.book.logger.message('Getting corners for leaf '+ str(leaf) + '...', 'featureDetection')
        leafnum = '%04d'%leaf
        self.in_file = (self.book.dirs['thumb'] + '/' +
                        self.book.identifier + '_thumb_' +
                        leafnum + '.jpg')
        if not os.path.exists(self.in_file):
            raise IOError(self.in_file + ' does not exist!')

        self.out_file = (self.book.dirs['corner'] + '/' +
                         self.book.identifier + '_corners_' +
                         leafnum + '.txt')
        self.t = '-t 44'
        self.s = ''
        self.n = '-n 9'
        self.l = '-l'

        if self.book.settings['respawn']:
            try:
                self.execute()
                self.book.pageCrop.skew(self.book.thumb_rotation_point['x'],
                                        self.book.thumb_rotation_point['y'],
                                        leaf)
                self.book.pageCropScaled.box[leaf] = self.book.pageCrop.scale_box(leaf, scale_factor = 4)
                self.CornerFilter.run(leaf)
                self.parse_corner_data(leaf)
                if self.book.settings['make_cornered_thumbs']:
                    self.l = ''
                    self.out_file = (self.book.dirs['corner_thumb'] + '/' +
                                     self.book.identifier + '_thumb_' +
                                     leafnum + '.jpg')
                    self.execute()
            except Exception as e:
                print str(e)
                raise e


    def parse_corner_data(self, leaf):
        leafnum = '%04d' % leaf
        window_file = (self.book.dirs['window'] + '/' +
                       self.book.identifier + '_window_' +
                       leafnum + '.txt')
        if os.path.exists(window_file):
            D = open(window_file, "r")
            contents = D.readline()
            contents = contents.split(" ")
            if len(contents) is not 5:
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




