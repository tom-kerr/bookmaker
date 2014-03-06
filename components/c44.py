import os

from .component import Component

class C44(Component):
    """ Creates DjVu
    """

    args = ['slice', 'size', 'bpp', 'percent', 'dpi',
            'gamma', 'decibel', 'dbfrac', 'crcb',
            'crcbdelay', 'mask', 'in_file', 'out_file']

    executable = 'c44'

    def __init__(self, book):
        super(C44, self).__init__()
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + 
                self.book.identifier + '_derived',
                'cropped': self.book.root_dir + '/' + 
                self.book.identifier + '_cropped',}
        self.book.add_dirs(dirs)
        
    def run(self, leaf, in_file=None, out_file=None, slices=None, size=None, 
            bpp=None, percent=None, dpi=None, gamma=None, decibel=None, 
            dbfrac=None, crcb=None, crcbnorm=None, crcbhalf=None, 
            crcbfull=None, crcbnone=None, crcbdelay=None, mask=None,
            hook=None, **kwargs):
        leafnum = "%04d" % leaf
        if not in_file:
            in_file = (self.book.dirs['cropped'] + '/' +
                       self.book.identifier + '_' + leafnum + '.JPG')
        if not os.path.exists(in_file):
            raise OSError('Cannot find ' + in_file)

        if not out_file:
            out_file =(self.book.dirs['derived'] + '/' +
                       self.book.identifier + '_' + leafnum + '.djvu')
        if slices:
            slices = ['-slice', str(slices)]
        if size:
            size = ['-size', str(size)]
        if bpp:
            bpp = ['-bpp', str(bpp)]
        if percent:
            percent = ['-percent', str(percent)]
        if dpi:
            dpi = ['-dpi', str(dpi)]
        if gamma:
            gamma = ['-gamma', str(gamma)]
        if decibel:
            decibel = ['-decibel', str(decibel)]
        if dbfrac:
            dbfrac = ['-dbfrac', str(dbfrac)]
        if crcbnorm:
            crcb = '-crcbnormal'
        elif crcbhalf:
            crcb = '-crcbhalf'
        elif crcbfull:
            crcb = '-crcbfull'
        elif crcbnone:
            crcb = '-crcbnone'
        if crcbnorm or crcbhalf:
            if crcbdelay:
                crcbdelay = ['-crcbdelay', str(crcbdelay)]
        if mask:
            mask = ['-mask', str(mask)]

        kwargs.update({'in_file': in_file,
                       'out_file': out_file,
                       'slice': slices,
                       'size': size,
                       'bpp': bpp,
                       'percent': percent,
                       'dpi': dpi,
                       'gamma': gamma,
                       'decibel': decibel,
                       'dbfrac': dbfrac,
                       'crcb': crcb,
                       'crcbdelay': crcbdelay,
                       'mask': mask})

        output = self.execute(kwargs, return_output=True)
        if hook:
            self.execute_hook(hook, leaf, output, **kwargs)
        else:
            return output

