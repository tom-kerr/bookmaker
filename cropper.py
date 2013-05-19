import os
import sys
import math
from lxml import etree
from util import Util
from environment import Environment
from datastructures import Crop
from imageops import ImageOps

class Cropper:


    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        self.ImageOps = ImageOps()


    def pipeline(self, start, end, crop, grayscale, normalize, invert):
        self.book.logger.message('Entering Cropper pipeline...','global')
        for leaf in range(start, end):
            self.book.logger.message('...leaf ' + str(leaf) + ' of ' + str(self.book.page_count) + '...',
                                     ('global','derivation'))
            leafnum = '%04d' % leaf
            rot_dir = -1 if leaf%2==0 else 1

            if not self.book.crops[crop].box[leaf].is_valid():
                self.ImageOps.complete(leaf, 'skipped cropping')
                continue

            raw = self.book.raw_images[leaf]
            out_file = self.book.dirs['cropped'] + '/' + self.book.identifier + '_' + leafnum + '.JPG'

            self.book.crops[crop].calculate_box_with_skew_padding(leaf)
            crp = self.book.crops[crop].box_with_skew_padding[leaf]
            
            cmd = 'cropper'
            args = {'in_file': raw,
                    'rot_dir': rot_dir,
                    'skew_angle': self.book.crops[crop].skew_angle[leaf],
                    'l': crp.l,
                    'r': crp.r,
                    't': crp.t,
                    'b': crp.b,
                    'out_file': out_file}

            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation')
            self.ImageOps.complete(leaf, 'finished cropping')

            leaf_exec_time = self.ImageOps.return_total_leaf_exec_time(leaf)
            self.book.logger.message('Finished cropping leaf ' + str(leaf) + ' in ' + str(leaf_exec_time) + ' seconds', 'derivation')
