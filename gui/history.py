from copy import copy

class History:

    def __init__(self, book):
        #self.master = {}
        self.total_changes = 0
        self.state = {}
        for leaf in range(0, book.page_count):
            self.state[leaf] = {}
            self.state[leaf]['current'] = 0
            self.state[leaf]['history'] = {}
            self.state[leaf]['history'][0] = {leaf: {'cropBox': book.cropBox.return_page_data_copy(leaf),
                                                     'pageCrop': book.pageCrop.return_page_data_copy(leaf),
                                                     'contentCrop': book.contentCrop.return_page_data_copy(leaf)}}

    
    def record_change(self, data):
        #print 'recording changes'
        for side in data:
            if side:
                leaf = side['leaf']
                next_state = self.state[leaf]['current'] + 1 
                self.state[leaf]['history'][next_state] = copy(side['affected'])
                self.state[leaf]['current'] = next_state
                #self.master[self.total_changes] = {leaf: copy(side['affected'])}
                self.total_changes += 1


    def has_history(self, leaf):
        if leaf in self.state:
            if len(self.state[leaf]['history']) > 1 and self.state[leaf]['current'] > 0:
                return True
            else:
                return False
