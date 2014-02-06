import os
from environment import Environment
from .component import Component

class CornerFilter(Component):
    """ Removes corners detected outside of a given area
        and writes them back to the input file.
    """

    args = ['in_file', 'out_file',
            'l', 't', 'r', 'b',
            'thumb_width', 'thumb_height']
    executable = Environment.current_path + '/bin/cornerFilter/cornerFilter'

    def __init__(self, book):
        super(CornerFilter, self).__init__()
        self.book = book

    def run(self, leaf, in_file=None, out_file=None, 
            thumb_width=None, thumb_height=None, 
            l=None, t=None, r=None, b=None, callback=None, **kwargs):
        crop_filter = self.book.pageCropScaled.box[leaf]
        if not crop_filter.is_valid():
            return
        leafnum = '%04d' % leaf
        if not in_file:
            in_file = (self.book.dirs['corners'] + '/' +
                       self.book.identifier + '_corners_' +
                       leafnum + '.txt')
        if not os.path.exists(in_file):
            raise OSError(in_file + ' does not exist!')
        if not out_file:
            out_file = (self.book.dirs['windows'] + '/' +
                        self.book.identifier + '_window_' +
                        leafnum + '.txt')

        crop_filter.resize(-10)

        if not l:
            l = crop_filter.l
        if not t:
            t = crop_filter.t
        if not r:
            r = crop_filter.r
        if not b:
            b = crop_filter.b

        if not thumb_width:
            thumb_width = self.book.pageCropScaled.image_width[leaf]
        if not thumb_height:
            thumb_height = self.book.pageCropScaled.image_height[leaf]

        kwargs.update({'in_file': in_file,
                       'out_file': out_file,
                       'thumb_width': thumb_width,
                       'thumb_height': thumb_height,
                       'l': l, 't': t,
                       'r': r, 'b': b})
        try:
            output = self.execute(kwargs, return_output=True)
        finally:
            crop_filter.resize(10)
        if callback:
            self.execute_callback(callback, leaf, output, **kwargs)
        else:
            return output
