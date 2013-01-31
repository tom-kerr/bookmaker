import os, sys, time
from collections import OrderedDict
from datetime import date
import multiprocessing, threading
import Queue

from util import Util
from environment import Environment
from featuredetection import FeatureDetection
#from pagination import AutoPaginate
from standardcrop import StandardCrop
from cropper import Cropper
from ocr import OCR
from derive import Derive
from gui.common import Common


class ProcessHandler:

    ThreadQueue = Queue.Queue()

    def __init__(self):
        try:
            self.cores = multiprocessing.cpu_count()
        except NotImplemented:
            self.cores = 1
        self.threads = []
        self.processes = 0
        self.process_queue = OrderedDict()
        self.item_queue = {}
        self.poll = None

        self.FeatureDetection = None
        self.Cropper = None
        self.OCR = None


    def init_poll(self):
        self.poll = threading.Thread(None, self.poll_threads, 'poll_threads')
        self.poll.start()


    def already_processing(self, proc_id):
        for thread in self.threads:
            if thread.name == proc_id:
                return True
        return False


    def queue_process(self, func, args, logger):
        self.process_queue[func] = args


    def run_queue(self):
        for func, args in self.process_queue.items():
            func(args[0], args[1])


    def add_process(self, func, proc_id, bookarg, logger=None):
        if Util.HALT:
            Util.HALT = False
        if self.already_processing(proc_id):
            return False
        if self.processes == self.cores:
            self.wait(func, proc_id, bookarg)
            return False
        else:
            #args = (self,).__add__((bookarg,),) if bookarg is not None else (self,)
            args = (self,) + tuple((bookarg,)) if bookarg is not None else (self,)
            new_thread = threading.Thread(None, func, proc_id, (args))
            new_thread.daemon = True
            new_thread.logger = logger
            new_thread.start()
            self.threads.append(new_thread)
            self.processes += 1
            if not self.poll:
                self.init_poll()
            if logger:
                new_thread.logger.message('New Thread Started -->   ' +
                                          'Identifier: ' + str(proc_id) + 
                                          '   Task: ' + str(func), 'processing')
            return True


    def wait(self, func, proc_id, args):
        if not proc_id in self.item_queue:
            self.item_queue[proc_id] = (func, args)


    def finish(self):
        for thread in self.threads:
            if thread.is_alive():
                thread.logger.message('Stopping Thread ' + str(thread.name), 'processing')
                Util.HALT = True
        self.poll = None


    def destroy_thread(self, proc_id):
        remove = None
        for num, thread in enumerate(self.threads):
            if proc_id == thread.name:
                remove = num
                thread.logger.message('Destroying Thread ' + str(thread.name), 'processing')
        if remove is not None:
            del self.threads[remove]
            self.processes -= 1


    def poll_threads(self):
        while True:          
            inactive_threads = []
            for t_num, thread in enumerate(self.threads):
                if not thread.is_alive():
                    inactive_threads.append(t_num)
                else:
                    pass
            inactive_threads.reverse()
            for t_num in inactive_threads:
                del self.threads[t_num]
            self.processes = len(self.threads)
            queue = []
            for proc_id, item in self.item_queue.items():
                if self.add_process(item[0], proc_id, item[1]):
                    queue.append(proc_id)
                else:
                    break
            queue.reverse()
            for proc_id in queue:
                del self.item_queue[proc_id]
            if self.processes == 0:
                self.finish()
                break
            time.sleep(3.0)
                

    def run_main(self, ProcessHandler, book):
        book.logger.message("Began Main Processing...")               
        book.starttime = Util.microseconds()
        if book.settings['respawn']:
            Environment.clean_dirs(book.dirs)
            Environment.make_scandata(book)
        self.FeatureDetection = FeatureDetection(book)
        self.FeatureDetection.pipeline()
    
        #if Environment.settings['autopaginate']:
        #    autoPaginator = AutoPaginate()
        #    autoPaginator.run(book.page_number_candidates)
                
        standardcrop = StandardCrop(book)
        end_time = Util.microseconds()
        book.logger.message("Finished Main Processing in " + str((end_time - book.start_time)/60) + ' minutes')


    def run_cropper(self, book, crop, grayscale=False, normalize=False, invert=False):
        book.logger.message("Began Cropping...")               
        self.Cropper = Cropper(book)
        chunk = (book.page_count-2)/self.cores
        for core in range(0, self.cores):
            start = (core * chunk) + 1
            if core == self.cores - 1:
                end = book.page_count-1
            else:
                end = (start + chunk)
            self.add_process(self.Cropper.pipeline, 
                             book.identifier + '_' + str(start) + '_cropper', 
                             (start, end, crop, grayscale, normalize, invert),
                             book.logger)    
        

    def run_ocr(self, book, language):
        self.OCR = OCR(book)
        chunk = (book.page_count-2)/self.cores
        for core in range(0, self.cores):
            start = (core * chunk) + 1
            if core == self.cores - 1:
                end = book.page_count-1
            else:
                end = (start + chunk)
            self.add_process(self.OCR.tesseract_hocr_pipeline, 
                             book.identifier + '_' + str(start) + '_ocr', 
                             (start, end, language),
                             book.logger)    


    def derive_formats(self, book, formats):
        self.Derive = Derive(book)
        for f in formats:
            print f
            if f == 'text':
                if self.OCR is not None:
                    ocr_data = self.OCR.ocr_data
                else:
                    ocr_data = None
                self.add_process(self.Derive.full_plain_text,
                                 book.identifier + '_' + f, (ocr_data,),
                                 book.logger)
            elif f == 'pdf':
                self.add_process(self.Derive.pdf, 
                                 book.identifier + '_' + f, None,
                                 book.logger)
            elif f == 'djvu':
                self.add_process(self.Derive.djvu,
                                 book.identifier + '_' + f, (),
                                 book.logger)
                                 
            elif 'epub':
                pass
