
from environment import Environment
from .component import Component

class Raw2Thumb(Component):

    args = ['in_file', 'rot_dir', 'scale_factor', 'out_file']
    executable = Environment.current_path + '/bin/raw2thumb/./raw2thumb'

    def __init__(self, book):
        self.leaf = None
        super(Raw2Thumb, self).__init__()
        self.book = book
        dirs = {'scaled': self.book.root_dir + '/' + 
                self.book.identifier + '_scaled'}
        self.book.add_dirs(dirs)

    def run(self, leaf, in_file=None, out_file=None, 
            scale_factor=None, rot_dir=None, hook=None, **kwargs):
        leafnum = '%04d' % leaf        
        if in_file is None:
            in_file = self.book.raw_images[leaf]
        if out_file is None:
            out_file = (self.book.dirs['scaled'] + '/' +
                        self.book.identifier + '_scaled_' +
                        leafnum + '.jpg')
        if scale_factor is None:
            scale_factor = Environment.scale_factor
        if rot_dir is None:
            rot_dir = -1 if leaf%2==0 else 1

        kwargs.update({'in_file': in_file,
                       'out_file': out_file,
                       'scale_factor': scale_factor,
                       'rot_dir': rot_dir})

        output = self.execute(kwargs, return_output=True)
        
        if hook:
            self.execute_hook(hook, leaf, output, **kwargs)
        else:
            return output

