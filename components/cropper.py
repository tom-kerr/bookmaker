import os
from component import Component
from environment import Environment
from datastructures import Crop

class Cropper(Component):
    """
    Rotates, deskews, and crops an image.

    """

    args = ['in_file', 'rot_dir', 'skew_angle',
            'l', 't', 'r', 'b', 'out_file']

    executable = Environment.current_path + '/bin/cropper/./cropper'

    def __init__(self, book):
        super(Cropper, self).__init__(Cropper.args)
        self.book = book
        dirs = {'cropped': self.book.root_dir + '/' + self.book.identifier + '_cropped'}
        self.book.add_dirs(dirs)


    def run(self, leaf, crop):
        if not self.book.crops[crop].box[leaf].is_valid():
            return False
        self.book.logger.message('Cropping leaf ' + str(leaf))
        leafnum = '%04d' % leaf
        self.in_file = self.book.raw_images[leaf]
        if not os.path.exists(self.in_file):
            raise IOError(self.in_file + ' does not exist.')
        self.out_file = self.book.dirs['cropped'] + '/' + self.book.identifier + '_' + leafnum + '.JPG'
        self.rot_dir = -1 if leaf%2==0 else 1
        self.skew_angle = self.book.crops[crop].skew_angle[leaf]
        self.book.crops[crop].calculate_box_with_skew_padding(leaf)
        crop_box = self.book.crops[crop].box_with_skew_padding[leaf]
        self.l = crop_box.l
        self.t = crop_box.t
        self.r = crop_box.r
        self.b = crop_box.b
        try:
            self.execute()
        except Exception as e:
            raise e
        else:
            self.book.logger.message('Finished cropping leaf ' + str(leaf) )