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
            'l', 't', 'r', 'b',
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
        self.in_file = (self.book.dirs['corners'] + '/' +
                        self.book.identifier + '_corners_' +
                        leafnum + '.txt')
        if not os.path.exists(self.in_file):
            raise IOError(self.in_file + ' does not exist!')
        self.out_file = (self.book.dirs['windows'] + '/' +
                         self.book.identifier + '_window_' +
                         leafnum + '.txt')
        crop_filter.resize(-10)
        self.l = crop_filter.l
        self.t = crop_filter.t
        self.r = crop_filter.r
        self.b = crop_filter.b
        self.thumb_width = self.book.pageCropScaled.image_width[leaf]
        self.thumb_height = self.book.pageCropScaled.image_height[leaf]
        try:
            self.execute()
            crop_filter.resize(10)
        except Exception as e:
            raise e
