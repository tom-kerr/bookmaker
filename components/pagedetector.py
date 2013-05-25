import os
import re
from environment import Environment
from component import Component

class PageDetector(Component):
    """
    Page Detector
    -------------

    Takes as input an image of a book page and outputs the
    dimensions and skew information.


    """

    args = ['in_file', 'rotation_direction', 'out_file']
    executable = Environment.current_path + '/bin/pageDetector/./pageDetector'


    def __init__(self, book):
        super(PageDetector, self).__init__(PageDetector.args)
        self.book = book


    def run(self, leaf):
        self.book.logger.message('Finding page for leaf ' + str(leaf) + '...', 'featureDetection')
        leafnum = '%04d' % leaf
        if self.book.settings['respawn']:
            self.in_file = self.book.raw_images[leaf]
            if not os.path.exists(self.in_file):
                raise IOError(in_file + ' does not exist!')
            self.out_file = (self.book.dirs['thumb'] + '/' +
                             self.book.identifier + '_thumb_' +
                             leafnum + '.jpg')

            self.rotation_direction = -1 if leaf%2==0 else 1
            try:
                output = self.execute(return_output=True)
            except Exception as e:
                raise e
            else:
                self.parse_output(leaf, output['output'])
        self.book.pageCropScaled.box[leaf] = self.book.pageCrop.scale_box(leaf, scale_factor = 4)


    def parse_output(self, leaf, output):
        fields = {'PAGE_L:': '([0-9]+)',
                  'PAGE_T:': '([0-9]+)',
                  'PAGE_R:': '([0-9]+)',
                  'PAGE_B:': '([0-9]+)',
                  'SKEW_ANGLE:': '([0-9\.\-]+)',
                  'SKEW_CONF:': '([0-9\.\-]+)'
                  }
        for field, regex in fields.iteritems():
            pattern = field + regex
            m = re.search(pattern, output)
            if m is not None:
                if field is 'PAGE_L:':
                    self.book.pageCrop.box[leaf].set_dimension('l', int(m.group(1)))
                if field is 'PAGE_T:':
                    self.book.pageCrop.box[leaf].set_dimension('t', int(m.group(1)))
                if field is 'PAGE_R:':
                    self.book.pageCrop.box[leaf].set_dimension('r', int(m.group(1)))
                if field is 'PAGE_B:':
                    self.book.pageCrop.box[leaf].set_dimension('b', int(m.group(1)))
                if field is 'SKEW_ANGLE:':
                    self.book.pageCrop.skew_angle[leaf] = float(m.group(1))
                    self.book.pageCrop.skew_active[leaf] = True
                    self.book.pageCropScaled.skew_angle[leaf] = float(m.group(1))
                    self.book.pageCropScaled.skew_active[leaf] = True
                    self.book.contentCrop.skew_angle[leaf] = float(m.group(1))
                    self.book.contentCrop.skew_active[leaf] = True
                    self.book.contentCropScaled.skew_angle[leaf] = float(m.group(1))
                    self.book.contentCropScaled.skew_active[leaf] = True
                if field is 'SKEW_CONF:':
                    self.book.pageCrop.skew_conf[leaf] = float(m.group(1))
                    self.book.pageCropScaled.skew_conf[leaf] = float(m.group(1))
                    self.book.contentCrop.skew_conf[leaf] = float(m.group(1))
                    self.book.contentCrop.skew_angle[leaf] = float(m.group(1))
                    self.book.contentCropScaled.skew_active[leaf] = True
            else:
                if field is 'PAGE_L:':
                    self.book.pageCrop.box[leaf].set_dimension('l', 0)
                if field is 'PAGE_T:':
                    self.book.pageCrop.box[leaf].set_dimension('t', 0)
                if field is 'PAGE_R:':
                    self.book.pageCrop.box[leaf].set_dimension('r', self.book.pageCrop.image_width-1)
                if field is 'PAGE_B:':
                    self.book.pageCrop.box[leaf].set_dimension('b', self.book.pageCrop.image_height-1)
                if field is 'SKEW_ANGLE:':
                    self.book.pageCrop.skew_angle[leaf] = 0.0
                    self.book.pageCrop.skew_active[leaf] = False
                    self.book.pageCropScaled.skew_angle[leaf] = 0.0
                    self.book.pageCropScaled.skew_active[leaf] = False
                    self.book.contentCrop.skew_angle[leaf] = 0.0
                    self.book.contentCrop.skew_active[leaf] = False
                    self.book.contentCropScaled.skew_angle[leaf] = 0.0
                    self.book.contentCropScaled.skew_active[leaf] = False
                if field is 'SKEW_CONF:':
                    self.book.pageCrop.skew_conf[leaf] = 0.0
                    self.book.pageCropScaled.skew_conf[leaf] = 0.0
                    self.book.contentCrop.skew_conf[leaf] = 0.0
                    self.book.contentCropScaled.skew_conf[leaf] = 0.0

