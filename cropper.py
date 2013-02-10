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
            raw_pnm = self.book.dirs['cropped'] + '/' + str(start) + '_raw.pnm'
            cmd = 'jpegtopnm'
            args = {'in_file': raw,
                    'out_file': raw_pnm}
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdout')

            raw_pnm_flipped = self.book.dirs['cropped'] + '/' + str(start) + '_flipped.pnm'            
            cmd = 'pnmflip'
            args = {'in_file': raw_pnm,
                    'out_file': raw_pnm_flipped,
                    'rotation': 90 if leaf%2==0 else 270 }
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdout')
            
            raw_pnm_flipped_skewed = self.book.dirs['cropped'] + '/' + str(start) + '_skewed.pnm'            
            cmd = 'pnmrotate'
            args = {'in_file': raw_pnm_flipped,
                    'out_file': raw_pnm_flipped_skewed,
                    'rotation': (0 - self.book.crops[crop].skew_angle[leaf]) }
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdout')

            
            if grayscale:
                grayscale = self.book.dirs['cropped'] + '/' + str(start) + '_grayscale.pnm'            
                cmd = 'ppmtopgm'
                args = {'in_file': raw_pnm_flipped_skewed,
                        'out_file': grayscale }
                self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdout')
            else:
                grayscale = False

            if normalize:
                normalized = self.book.dirs['cropped'] + '/' + str(start) + '_normalized.pnm'            
                if os.path.exists(self.book.dirs['cropped'] + '/' + str(start) + '_grayscale.pnm'):
                    in_file = self.book.dirs['cropped'] + '/' + str(start) + '_grayscale.pnm'
                else:
                    in_file = raw_pnm_flipped_skewed
                cmd = 'pnmnorm'
                args = {'in_file': in_file,
                        'out_file': normalized }
                self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdout')
            else:
                normalized = False

            if invert:                
                inverted = self.book.dirs['cropped'] + '/' + str(start) + '_inverted.pnm'   
                if os.path.exists(self.book.dirs['cropped'] + '/' + str(start) + '_normalized.pnm'):
                    in_file = self.book.dirs['cropped'] + '/' + str(start) + '_normalized.pnm'
                elif os.path.exists(self.book.dirs['cropped'] + '/' + str(start) + '_grayscale.pnm'):
                    in_file = self.book.dirs['cropped'] + '/' + str(start) + '_grayscale.pnm'
                else:
                    in_file = raw_pnm_flipped_skewed
                cmd = 'pnminvert'
                args = {'in_file': in_file,
                        'out_file': inverted }
                self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdout')
            else:
                inverted = False

            cropped = self.book.dirs['cropped'] + '/' + self.book.identifier + '_' + leafnum + '.pnm'
            if os.path.exists(self.book.dirs['cropped'] + '/' + str(start) + '_inverted.pnm'):
                in_file = inverted = self.book.dirs['cropped'] + '/' + str(start) + '_inverted.pnm'
            elif os.path.exists(self.book.dirs['cropped'] + '/' + str(start) + '_normalized.pnm'):
                in_file = self.book.dirs['cropped'] + '/' + str(start) + '_normalized.pnm'
            elif os.path.exists(self.book.dirs['cropped'] + '/' + str(start) + '_grayscale.pnm'):
                in_file = self.book.dirs['cropped'] + '/' + str(start) + '_grayscale.pnm'
            else:
                in_file = raw_pnm_flipped_skewed

            self.book.crops[crop].calculate_box_with_skew_padding(leaf)
            crp = self.book.crops[crop].box_with_skew_padding[leaf]            
            cmd = 'pamcut'
            args = {'l': int(crp.l),
                    't': int(crp.t),
                    'r': int(crp.r),
                    'b': int(crp.b),
                    'in_file': in_file,
                    'out_file': cropped}
            self.ImageOps.execute(leaf, cmd, args, self.book.logger, log='derivation', redirect='stdout')
            self.ImageOps.complete(leaf, 'finished cropping')
            for f in [f for f in (raw_pnm, raw_pnm_flipped, 
                                  raw_pnm_flipped_skewed, 
                                  grayscale, normalized, inverted) if f not in (None, False)]:
                try:    
                    os.remove(f)
                except:
                    pass

            leaf_exec_time = self.ImageOps.return_total_leaf_exec_time(leaf)
            self.book.logger.message('Finished cropping leaf ' + str(leaf) + ' in ' + str(leaf_exec_time) + ' seconds', 'derivation')
