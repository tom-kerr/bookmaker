import os

from component import Component

class Djvm(Component):
    """
    Manipulate bundled multi-page DjVu Documents.

    """

    args = ['options', 'out_file', 'in_files']
    executable = 'djvm'

    def __init__(self, book):
        super(Djvm, self).__init__(Djvm.args)
        self.book = book
        dirs = {'derived': self.book.root_dir + '/' + self.book.identifier + '_derived'}
        self.book.add_dirs(dirs)


    def run(self):
        for f in self.in_files:
            if not os.path.exists(f):
                raise IOError('Cannot find ' + f)
        try:
            self.execute()
        except Exception as e:
            raise e

    def remove_in_files(self):
        for f in self.in_files:
            try:
                os.remove(f)
            except Exception as e:
                raise e