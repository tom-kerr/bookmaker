import os
import re

from environment import Environment
from .component import Component
from datastructures import Crop


class PageDetector(Component):
    """ Takes as input an image of a book page and outputs the
        dimensions and skew information and writes a scaled version
        of the input image.
    """
    args = ['in_file', 'rot_dir', 'scale_factor', 'scaled_out_file']
    executable = Environment.current_path + '/bin/pageDetector/./pageDetector'

    def __init__(self, book):
        self.leaf = None
        super(PageDetector, self).__init__()
        self.book = book
        dirs = {'scaled': self.book.root_dir + '/' + 
                self.book.identifier + '_scaled'}
        self.book.add_dirs(dirs)

    def run(self, leaf, in_file=None, scaled_out_file=None, 
            scale_factor=None, rot_dir=None, hook=None, **kwargs):
        leafnum = '%04d' % leaf        
        if not in_file:
            in_file = self.book.raw_images[leaf]
        if not scaled_out_file:
            scaled_out_file = (self.book.dirs['scaled'] + '/' +
                               self.book.identifier + '_scaled_' +
                               leafnum + '.jpg')
        if not scale_factor:
            scale_factor = 0.25
        if not rot_dir:
            rot_dir = -1 if leaf%2==0 else 1

        kwargs.update({'in_file': in_file,
                       'scaled_out_file': scaled_out_file,
                       'scale_factor': scale_factor,
                       'rot_dir': rot_dir})
        
        if self.book.settings['respawn']:
            if not os.path.exists(in_file):
                raise OSError(in_file + ' does not exist.')
            output = self.execute(kwargs, return_output=True)
        else:
            output = None        
        if hook:
            self.execute_hook(hook, leaf, output, **kwargs)
        else:
            return output

    def post_process(self, *args, **kwargs):        
        leaf, output = args[0], args[1]
        if not hasattr(self.book, 'pageCropScaled'):
            self.book.pageCropScaled = Crop('pageCrop', self.book.page_count,
                                            self.book.raw_image_dimensions,
                                            scale_factor=4)
        if not hasattr(self.book, 'contentCropScaled'):
            self.book.contentCropScaled = Crop('contentCrop', self.book.page_count,
                                               self.book.raw_image_dimensions,
                                               scale_factor=4)
        if self.book.settings['respawn']:
            if not hasattr(self.book, 'pageCrop'):
                self.book.pageCrop = Crop('pageCrop', self.book.page_count,
                                          self.book.raw_image_dimensions,
                                          self.book.scandata)
            if not hasattr(self.book, 'contentCrop'):
                self.book.contentCrop = Crop('contentCrop', self.book.page_count,
                                             self.book.raw_image_dimensions,
                                             self.book.scandata)
            PageDetector.parse_output(leaf, output['output'], 
                                      self.book.pageCrop, self.book.pageCropScaled,
                                      self.book.contentCrop, self.book.contentCropScaled)
        self.book.pageCropScaled.box[leaf] = \
            self.book.pageCrop.scale_box(leaf, scale_factor = 4)

    @staticmethod
    def parse_output(leaf, output, 
                     pageCrop, pageCropScaled, 
                     contentCrop, contentCropScaled):
        fields = {'PAGE_L:': '([0-9]+)',
                  'PAGE_T:': '([0-9]+)',
                  'PAGE_R:': '([0-9]+)',
                  'PAGE_B:': '([0-9]+)',
                  'SKEW_ANGLE:': '([0-9\.\-]+)',
                  'SKEW_CONF:': '([0-9\.\-]+)'
                  }
        for field, regex in fields.items():
            pattern = field + regex
            m = re.search(pattern, output)
            if m is not None:
                if field is 'PAGE_L:':
                    pageCrop.box[leaf].set_dimension('l', int(m.group(1)))
                if field is 'PAGE_T:':
                    pageCrop.box[leaf].set_dimension('t', int(m.group(1)))
                if field is 'PAGE_R:':
                    pageCrop.box[leaf].set_dimension('r', int(m.group(1)))
                if field is 'PAGE_B:':
                    pageCrop.box[leaf].set_dimension('b', int(m.group(1)))
                if field is 'SKEW_ANGLE:':
                    pageCrop.skew_angle[leaf] = float(m.group(1))
                    pageCrop.skew_active[leaf] = True
                    pageCropScaled.skew_angle[leaf] = float(m.group(1))
                    pageCropScaled.skew_active[leaf] = True
                    contentCrop.skew_angle[leaf] = float(m.group(1))
                    contentCrop.skew_active[leaf] = True
                    contentCropScaled.skew_angle[leaf] = float(m.group(1))
                    contentCropScaled.skew_active[leaf] = True
                if field is 'SKEW_CONF:':
                    pageCrop.skew_conf[leaf] = float(m.group(1))
                    pageCropScaled.skew_conf[leaf] = float(m.group(1))
                    contentCrop.skew_conf[leaf] = float(m.group(1))
                    contentCrop.skew_angle[leaf] = float(m.group(1))
                    contentCropScaled.skew_active[leaf] = True
            else:
                if field is 'PAGE_L:':
                    pageCrop.box[leaf].set_dimension('l', 0)
                if field is 'PAGE_T:':
                    pageCrop.box[leaf].set_dimension('t', 0)
                if field is 'PAGE_R:':
                    pageCrop.box[leaf].\
                        set_dimension('r', pageCrop.image_width[leaf]-1)
                if field is 'PAGE_B:':
                    pageCrop.box[leaf].\
                        set_dimension('b', pageCrop.image_height[leaf]-1)
                if field is 'SKEW_ANGLE:':
                    pageCrop.skew_angle[leaf] = 0.0
                    pageCrop.skew_active[leaf] = False
                    pageCropScaled.skew_angle[leaf] = 0.0
                    pageCropScaled.skew_active[leaf] = False
                    contentCrop.skew_angle[leaf] = 0.0
                    contentCrop.skew_active[leaf] = False
                    contentCropScaled.skew_angle[leaf] = 0.0
                    contentCropScaled.skew_active[leaf] = False
                if field is 'SKEW_CONF:':
                    pageCrop.skew_conf[leaf] = 0.0
                    pageCropScaled.skew_conf[leaf] = 0.0
                    contentCrop.skew_conf[leaf] = 0.0
                    contentCropScaled.skew_conf[leaf] = 0.0

