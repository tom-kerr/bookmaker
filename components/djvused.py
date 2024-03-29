import os

from .component import Component

class Djvused(Component):
    """ Multi Purpose DjVu Document Editor
    """

    args = ['options', 'script', 'djvu_file']
    executable = 'djvused'

    def __init__(self, book):
        super(Djvused, self).__init__()
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + \
                    self.book.identifier + '_derived'}
        self.book.add_dirs(dirs)
        
    def run(self, leaf, djvu_file=None, options=None, 
            script=None, **kwargs):
        leafnum = "%04d" % leaf
        if not djvu_file:
            djvu_file = (self.book.dirs['derived'] + '/' +
                         self.book.identifier + '_' + leafnum + '.djvu')
        if not os.path.exists(djvu_file):
            self.on_failure(exception=OSError(djvu_file + 'does not exist.'))
        
        kwargs.update({'leaf': leaf,
                       'djvu_file': djvu_file,
                       'options': options,
                       'script': script})
        
        output = self.execute(kwargs, return_output=True)
        return output

