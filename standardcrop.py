import os
import sys
import math
from lxml import etree
from util import Util
from environment import Environment
from datastructures import Crop
#from imageprocessing import ImageProcessing

class StandardCrop:

    width_ratio_max = 0.85
    height_ratio_max = 0.85
    width_target = 1.2
    height_target = 1.2
    
    def __init__(self, book):
        self.book = book
        self.make_standard_crop()


    def make_standard_crop(self):
        self.book.standardCrop = Crop('cropBox', 0, self.book.page_count,
                                 self.book.raw_image_dimensions[0][1], 
                                 self.book.raw_image_dimensions[0][0])
        self.book.contentCropScaled.get_box_metadata()
        
        ratios = self.get_content_to_page_ratios()
        #print ratios
        self.set_crop_size(ratios);
        self.align_crops(ratios)

        #self.pipeline()
        self.book.standardCrop.xml_io(self.book.scandata_file, 'export')


    def set_crop_size(self, ratios):
        for leaf, box in self.book.standardCrop.box.items():

            if ratios['height'] < StandardCrop.height_ratio_max:
                height = self.book.contentCropScaled.meta['h']['stats']['mean'] * StandardCrop.height_target
            else:
                height = self.book.pageCropScaled.meta['h']['stats']['mean'] * .97
            
            if ratios['width'] < StandardCrop.width_ratio_max:
                width = self.book.contentCropScaled.meta['w']['stats']['mean'] * StandardCrop.width_target
            else:
                width = self.book.pageCropScaled.meta['w']['stats']['mean'] * .97

            box.set_dimension('w', int(width))
            box.set_dimension('h', int(height))
            self.book.standardCrop.skew_angle[leaf] = self.book.pageCropScaled.skew_angle[leaf]
            self.buffer =  self.book.contentCropScaled.meta['h']['stats']['mean'] * .05
        
        
    def align_crops(self, ratios):
        #print self.book.contentCropScaled.meta['h']['stats']
        #print self.book.contentCropScaled.meta['h']['stats_hist']

        for leaf, box in self.book.standardCrop.box.items():
            if not self.book.pageCropScaled.box[leaf].is_valid():
                continue

            if self.book.contentCropScaled.classification[leaf] is 'Blank':
                box.center_within(self.book.pageCropScaled.box[leaf])                
            else:
                if (self.book.contentCropScaled.box[leaf].h in 
                    self.book.contentCropScaled.meta['h']['stats_hist']['above_mean'] or
                    self.book.contentCropScaled.box[leaf].h 
                    in self.book.contentCropScaled.meta['h']['stats_hist']['below_mean']):
                    orientation = 'head'
                else:
                    orientation = self.book.contentCropScaled.box[leaf].detect_orientation(self.book.pageCropScaled.box[leaf])
                if orientation is 'head':
                    h = self.buffer
                    f = None
                elif orientation is 'floor':
                    h = None
                    f = self.buffer
                elif orientation is 'center':
                    h = None
                    f = None
                box.position_around(self.book.contentCropScaled.box[leaf], head=h, floor=f)
                #self.book.standardCrop.skew_translation(self.book.thumb_rotation_point['x'],
                #                                        self.book.thumb_rotation_point['y'],
                #                                        leaf, factor=2, deskew=True)
                
                box.fit_within(self.book.pageCropScaled.box[leaf])
                
            self.book.standardCrop.box[leaf] = self.book.standardCrop.scale_box(leaf, 0.25)


    def get_content_to_page_ratios(self):
        content_to_page_width_ratios = []
        content_to_page_height_ratios = []
        for leaf, box in self.book.contentCropScaled.box.items():
            if box.w in self.book.contentCropScaled.meta['w']['stats_hist']['above_mean']:
                ratio = float(box.w) / float(self.book.pageCropScaled.box[leaf].w)
                content_to_page_width_ratios.append(ratio) 
            if box.h in self.book.contentCropScaled.meta['h']['stats_hist']['above_mean']:
                ratio = float(box.h) / float(self.book.pageCropScaled.box[leaf].h)
                content_to_page_height_ratios.append(ratio) 
                
        average_content_to_page_width_ratio = (sum(content_to_page_width_ratios)/
                                               len(content_to_page_width_ratios))

        average_content_to_page_height_ratio = (sum(content_to_page_height_ratios)/
                                                len(content_to_page_height_ratios))
        
        return {'width': average_content_to_page_width_ratio,
                'height': average_content_to_page_height_ratio}
            
