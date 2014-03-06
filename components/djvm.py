import os
import re
import glob

from .component import Component


class Djvm(Component):
    """ Manipulate bundled multi-page DjVu Documents.
    """

    args = ['options', 'out_file', 'in_files']
    executable = 'djvm'

    def __init__(self, book):
        super(Djvm, self).__init__()
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + 
                self.book.identifier + '_derived'}
        self.book.add_dirs(dirs)

    def run(self, in_files=None, out_file=None, 
            options=None, hook=None, **kwargs):
        if not in_files:
            in_files = sorted([f for f in 
                        glob.glob(self.book.dirs['derived'] + '/*.djvu') 
                        if re.search('[0-9]+.djvu$', f)])
        if not out_file:
            out_file = self.book.dirs['derived'] + '/' + \
                self.book.identifier + '.djvu '
        for f in in_files:
            if not os.path.exists(f):
                raise OSError(f + ' does not exist.')

        kwargs.update({'options': options,
                       'out_file': out_file,
                       'in_files': in_files})

        output = self.execute(kwargs, return_output=True)
        if hook:
            self.execute_hook(hook, leaf, output, **kwargs)
        else:
            return output

    def remove_in_files(self, files=None):
        if not files:
            files = [f for f in 
                     glob.glob(self.book.dirs['derived'] + '/*.djvu') 
                     if re.search('[0-9]+.djvu$', f)]
        for f in files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError as e:
                self.book.logger.warning('Failed to remove ' + f + ';' + str(e))
