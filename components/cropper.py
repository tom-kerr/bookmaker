import os

from .component import Component
from environment import Environment
from datastructures import Crop

class Cropper(Component):
    """ Rotates, deskews, and crops an image.
    """

    args = ['in_file', 'rot_dir', 'skew_angle',
            'l', 't', 'r', 'b', 'out_file']

    executable = Environment.current_path + '/bin/cropper/./cropper'

    def __init__(self, book):
        super(Cropper, self).__init__()
        self.book = book
        dirs = {'cropped': self.book.root_dir + '/' + 
                self.book.identifier + '_cropped'}
        self.book.add_dirs(dirs)

    def run(self, leaf, in_file=None, out_file=None, rot_dir=None, 
            skew_angle=None, l=None, t=None, r=None, b=None,  
            crop='standardCrop', hook=None, **kwargs):
        if not self.book.crops[crop].box[leaf].is_valid():
            return False
        leafnum = '%04d' % leaf
        if not in_file:
            in_file = self.book.raw_images[leaf]
        if not os.path.exists(in_file):
            raise OSError(in_file + ' does not exist.')
        if not out_file:
            out_file = self.book.dirs['cropped'] + '/' + \
                self.book.identifier + '_' + leafnum + '.JPG'
        if not rot_dir:
            rot_dir = -1 if leaf%2==0 else 1
        if not skew_angle:
            skew_angle = self.book.crops[crop].skew_angle[leaf]
        
        for dim in (l, t, r, b):
            if not dim:
                self.book.crops[crop].calculate_box_with_skew_padding(leaf)
                crop_box = self.book.crops[crop].box_with_skew_padding[leaf]
                l = crop_box.l
                t = crop_box.t
                r = crop_box.r
                b = crop_box.b
                break
            
        kwargs.update({'in_file': in_file,
                       'out_file': out_file, 
                       'rot_dir': rot_dir,
                       'skew_angle': skew_angle,
                       'l': l, 't': t, 
                       'r': r, 'b': b, 
                       'crop': crop})
        
        output = self.execute(kwargs, return_output=True)
        if hook:
            self.execute_hook(hook, leaf, output, **kwargs)
        else:
            return output
