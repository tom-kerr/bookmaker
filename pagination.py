import os
from lxml import etree
from _global import Environment, Logger
from imageprocessing import ImageProcessing
from datastructures import Rectangle

class AutoPaginate:

    log = 'pagination'
    text_data = {}
    
    def run(self, page_number_candidates):
        for leaf, zones in page_number_candidates.items():
            Logger.message('OCR pipeline: leaf ' + str(leaf))
            AutoPaginate.text_data[leaf] = {}
            for zone in zones:
                for num, cluster in zone.items():
                    Logger.message('\tcluster ' + str(num))
                    raw_text_data = OCR.pipeline(leaf, num, cluster)
                    if raw_text_data is not None:
                        output = OCR.parse(raw_text_data)
                        if output not in ('', ' '):
                            AutoPaginate.text_data[leaf][num] = output
                        else:
                            AutoPaginate.text_data[leaf][num] = None
        for leaf, candidates in AutoPaginate.text_data.items():
            for name, number in candidates.items():
                Logger.message('leaf ' + str(leaf) + ' cluster ' + str(name) +
                               ' value: ' + str(number) , AutoPaginate.log)
        self.generate_threads()

    def generate_threads(self):
        tree = {}
        for leaf, candidates in AutoPaginate.text_data.items():
            tree[leaf] = {}
            for name, number in candidates.items():
                if number is not None and int(number) in range(1,11):
                    Logger.message('\nstarting TRUNK thread for leaf '+ str(leaf) + 
                                               ' cluster ' + str(name) + 
                                               ' -- value: ' + str(number), AutoPaginate.log)
                    tree[leaf][name] = Thread(leaf, number, 'trunk')
                    tree[leaf][name].expectation = range(1, 11)
                    tree[leaf][name].search()

        best = None
        max = 0
        for leaf, threads in tree.items():
            for name, thread in threads.items():
                if thread.match_count > max:
                    max = thread.match_count
                    best = (leaf, name, max) 

        Logger.message('best thread is leaf ' + str(best[0]) 
                       + ' cluster ' + str(best[1]), AutoPaginate.log)
        for leaf, number in tree[best[0]][best[1]].sequence.items():
            Logger.message('leaf:' + str(leaf) + ' ' + str(number), AutoPaginate.log)
        
        #debuging
        self.thread_to_xml(tree[best[0]][best[1]].sequence)
        #


    def thread_to_xml(self, sequence):
        try:
            xml = etree.ElementTree()
            xml.parse(Environment.scandata_file)
        except IOError:
            Util.bail('could not open xml file ' + str(Environment.scandata_file))
        page_data = xml.find('pageData')
        pages = page_data.findall('page')
        for leaf, page in enumerate(pages):
            page_number = page.find('pageNumber')
            if leaf not in sequence or sequence[leaf] is '?':
                page_number.text = '\'?\'';
            else:
                page_number.text = str(sequence[leaf])            
        scandata = open(Environment.scandata_file, 'w')
        xml.write(scandata, pretty_print=True)
        scandata.close()
            


class Thread:

    def __init__(self, leaf, number, type):
        self.start = leaf
        self.current = leaf
        self.type = type
        self.char_limit = len(str(Environment.page_count))
        self.sequence = {}
        self.sequence[leaf] = number
        self.expectation = int(number) + 1
        self.match_count = 0
        self.failures = 0
        self.input_number(leaf, number)

               
    def input_number(self, leaf, number):
        self.sequence[leaf] = number
        self.current = leaf


    def exact_match(self, number):
        if isinstance(self.expectation, list):
            if int(number) in self.expectation:
                Logger.message('found initial match:' + str(number) +
                               ' found in:' + str(self.expectation), AutoPaginate.log)
                self.expectation = int(number)
                return True
            else:
                return None
        if int(number) is self.expectation:
            Logger.message('found exact match of '+ str(self.expectation) + ': ' + 
                           str(number), AutoPaginate.log)
            return True
        else:
            return False


    def partial_match(self, number):
        if isinstance(self.expectation, list):
            return None
        if len(str(number)) > self.char_limit:
            if str(self.expectation) in str(number):
                Logger.message('found subset (A) match of '+ str(self.expectation) + ':' + 
                               str(number), AutoPaginate.log)
                return True
            else:
                return False
        
        if len(str(number)) > len(str(self.expectation)):
            if str(self.expectation) in str(number):
                Logger.message('found subset (B) match of '+ str(self.expectation) + ':' + 
                               str(number), AutoPaginate.log)
                return True
        if len(str(self.expectation)) > len(str(number)):
            if str(number) in str(self.expectation):
                Logger.message('found subset (C) match of '+ str(self.expectation) + ':' + 
                               str(number), AutoPaginate.log)
                return True
        count = 0
        for char in str(number):
            if char in str(self.expectation):
                count += 1
        if float(count)/float(len(str(self.expectation))) > 0.3:
            Logger.message('found partial match of ' + str(self.expectation) + ' :' + 
                           str(number), AutoPaginate.log)
            return True            
        return False
 
       
    def update(self, match):
        if self.type is 'trunk':
            if match is None:
                return 'continue'
            elif match:            
                self.expectation += 1
                self.match_count += 1
                return 'continue'
            elif not match:
                self.expectation += 1
                self.failures += 1
                return 'branch'

        elif self.type is 'branch':
            if match:            
                self.expectation += 1
                self.match_count += 1
            elif not match:
                self.failures += 1
            if self.failures > 2:
                return 'fail'
            elif self.match_count > 2:
                return 'merge'
            else:
                return 'continue'


    def find_a_match(self, leaf, candidates):
        for name, number in candidates.items():
            if number is not None:
                #Logger.message('\t\t\ttrying leaf ' + str(leaf) + 
                #               ' cluster ' + str(name) + 
                #               ' -- value: ' + str(number) + 
                #               ' ...expecting: ' + str(self.expectation), AutoPaginate.log)  

                if self.exact_match(number):
                    self.input_number(leaf, number)
                    return self.update(True)
                else:
                    if self.type is 'trunk':
                        if self.partial_match(number):
                            self.input_number(leaf, self.expectation)
                            continue
        
        if self.sequence[leaf] is not '?':
            return self.update(True)
        
        if isinstance(self.expectation, list):
            return self.update(None)
        else:
            return self.update(False)
        
       
    def search(self):
        for leaf, candidates in AutoPaginate.text_data.items(): 
            if leaf > self.current:
                self.sequence[leaf] = '?'
                Logger.message('\t\tsearching leaf ' + str(leaf) + '...', AutoPaginate.log)
                if candidates is None:
                    continue
                else:
                    result = self.find_a_match(leaf, candidates)
        
                    if self.type is 'trunk':
                        if result is 'continue':
                            continue
                        elif result is 'branch':
                            self.branch(leaf, candidates)
                            continue
                    
                    if self.type is 'branch':
                        if result is 'continue':
                            continue
                        if result in ('merge', 'fail'):
                            return result


    def branch(self, leaf, candidates):
        branch = {}
        for name, number in candidates.items():
            if number is None or len(str(number)) > self.char_limit:
                continue
            else:
                Logger.message('\nstarting BRANCH thread at leaf '+ str(leaf) + 
                               ' cluster ' + str(name) + 
                               ' -- value: ' + str(number), AutoPaginate.log)
                branch[name] = Thread(leaf, number, 'branch')
                result = branch[name].search()
                if result is 'continue':
                    continue
                elif result is 'fail':
                    Logger.message('branch was a failure...', AutoPaginate.log)
                    self.sequence[leaf] = '?'
                    return
                elif result is 'merge':
                    Logger.message('merging branch at leaf ' + str(leaf) + 
                                   ' cluster '+ str(name)+ ' with leaf '+str(self.start)+
                                   ' trunk...\n', AutoPaginate.log)
                    for leaf in range(branch[name].start, branch[name].current+1):
                        number = branch[name].sequence[leaf]
                        #Logger.message('adding data for leaf ' + str(leaf) +
                        #              ' value:' + str(number) , AutoPaginate.log)
                        self.input_number(leaf, number)
                        if number is '?':
                            self.expectation = number
                        else:
                            self.expectation = int(number)
                    #Logger.message('updated current leaf to ' + str(leaf), AutoPaginate.log)
                    self.update(True)
                    self.current = leaf
                    return
        self.sequence[leaf] = '?'
        return
        

class OCR:

    char_map = [ ['O','o','.','*','('],
                 ['i','I','l','|','[','{','(',')','}',']','/','\\'],
                 ['z','Z'],
                 ['8','B','\xc3'],
                 ['a','A','L'],
                 [],
                 ['G','('],
                 [],
                 ['3','B','\xc3','E'],
                 ['s','S'],
                 [],
                 ['H'] ]

    @staticmethod
    def pipeline(leaf, num, cluster, log='pagination'):
        leafnum = '%04d' % leaf        
        
        if Environment.respawn:
        #-------------
        #CONVERT TO PNM
        #--------------
            in_file = Environment.raw_images[leaf]
            out_file = (Environment.dirs['pagination'] + '/' + 
                        Environment.identifier + '_' + str(leafnum) + '.pnm')
            cmd = 'jpegtopnm'
            args = {'in_file': in_file,
                    'out_file': out_file}
            if not os.path.exists(out_file):
                ImageProcessing.imgops(leaf, cmd, args, log, redirect=True)
                
            crop = Rectangle()
            
            if leaf%2==0:
                rotation = 90
                crop.set_dimension('l', Environment.raw_image_dimensions[0][0] - cluster.b*4)
                crop.set_dimension('t', cluster.l*4)
                crop.set_dimension('r', Environment.raw_image_dimensions[0][0] - cluster.t*4)
                crop.set_dimension('b', cluster.r*4)
            else:
                rotation = 270
                crop.set_dimension('l', cluster.t*4)
                crop.set_dimension('t', Environment.raw_image_dimensions[0][1] - cluster.r*4)
                crop.set_dimension('r', cluster.b*4)
                crop.set_dimension('b', Environment.raw_image_dimensions[0][1] - cluster.l*4)
                
            crop.resize(35)

        #-------------
        #CUT OUT SECTION
        #--------------
            in_file = (Environment.dirs['pagination'] + '/' + 
                       Environment.identifier + '_' + 
                       str(leafnum) + '.pnm')
            out_file = (Environment.dirs['pagination'] + '/' + 
                        Environment.identifier + '_' + 
                        str(leafnum) + '_' + str(num) + '.pnm')
            cmd = 'pamcut'
            args = {'l':crop.l,'t':crop.t,'r':crop.r,'b':crop.b,
                    'in_file': in_file,
                    'out_file': out_file}
            ImageProcessing.imgops(leaf, cmd, args, log, redirect=True)

            #won't need the original pnm anymore, so we delete it to save space
            if os.path.exists(in_file):
                os.remove(in_file)
            
        #-------------
        #ROTATE SECTION
        #--------------
            in_file = (Environment.dirs['pagination'] + '/' + 
                       Environment.identifier + '_' + 
                       str(leafnum) + '_' + str(num) + '.pnm')
            out_file = (Environment.dirs['pagination'] + '/' + 
                        Environment.identifier + '_rotated_' + 
                        str(leafnum) + '_' + str(num) + '.pnm')
            cmd = 'pnmflip'
            args = {'in_file': in_file,
                    'out_file': out_file,
                    'rotation': rotation}
            ImageProcessing.imgops(leaf, cmd, args, log, redirect=True)
            
        #-------------
        #OCR SECTION
        #--------------
            in_file = (Environment.dirs['pagination'] + '/' + 
                       Environment.identifier + '_rotated_' + 
                       str(leafnum) + '_' + str(num) + '.pnm')
            out_base = (Environment.dirs['pagination'] + '/' + 
                        Environment.identifier + '_' + 
                        str(leafnum) + '_' + str(num) + '_RAWTEXTDATA')
            cmd = 'tesseract'
            args = {'in_file': in_file,
                    'out_base': out_base,
                    'language': 'eng',
                    'psm': 6}
            ImageProcessing.imgops(leaf, cmd, args, log, return_output=True)
                        
        #-------------
        #GET RAW TEXT DATA
        #--------------
        raw_text_file = (Environment.dirs['pagination'] + '/' + 
                         Environment.identifier + '_' + 
                         str(leafnum) + '_' + str(num) + '_RAWTEXTDATA.txt')
        try:
            f = open(raw_text_file, 'r')
            text = f.readlines()
        except:
            text = None                    
        return text


    @staticmethod
    def parse(raw_text_data):
        formatted_text = ''
        for line in raw_text_data:
            line = line.strip()
            if line:
                formatted_text += line
        parsed_text = ''
        for char in formatted_text:
            output = OCR.lex(char)                        
            if output:
                parsed_text += str(output)
        return parsed_text


    @staticmethod
    def lex(char):
        for num, char_set in enumerate(OCR.char_map):
            if str(char) is str(num):
                return num
            else:
                for item in char_set:
                    if str(char) is str(item):
                        return num
        return False
