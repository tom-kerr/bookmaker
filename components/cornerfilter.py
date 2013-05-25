import os
from environment import Environment
from component import Component

class CornerFilter(Component):
    """
    Corner Filter
    -------------

    Removes corners detected outside of a given area
    and writes them back to the input file.

    """

    args = ['in_file', 'out_file',
            'l', 't', 't', 'b',
            'thumb_width', 'thumb_height']
    executable = Environment.current_path + '/bin/cornerFilter/cornerFilter'


    def __init__(self, book):
        super(CornerFilter, self).__init__(CornerFilter.args)
        self.book = book


    def run(self, leaf):
        crop_filter = self.book.pageCropScaled.box[leaf]
        if not crop_filter.is_valid():
            return
        self.book.logger.message('Filtering corners for leaf ' + str(leaf) + '...', 'featureDetection')
        leafnum = '%04d' % leaf
        self.in_file = (self.book.dirs['corner'] + '/' +
                        self.book.identifier + '_corners_' +
                        leafnum + '.txt')
        if not os.path.exists(self.in_file):
            raise IOError(self.in_file + ' does not exist!')
        self.out_file = (self.book.dirs['window'] + '/' +
                         self.book.identifier + '_window_' +
                         leafnum + '.txt')
        crop_filter.resize(-10)
        self.l = crop_filter.l
        self.t = crop_filter.t
        self.r = crop_filter.r
        self.b = crop_filter.b
        self.thumb_width = self.book.raw_image_dimensions[0]['height']/4
        self.thumb_height = self.book.raw_image_dimensions[0]['width']/4
        try:
            self.execute()
            crop_filter.resize(10)
        except Exception as e:
            raise e
