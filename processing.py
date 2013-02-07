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
        self.threads = {}
        self.processes = 0
        self.process_queue = self.new_queue()
        self.item_queue = self.new_queue()
        self.poll = None

        self.FeatureDetection = None
        self.Cropper = None
        self.OCR = None


    def init_poll(self):
        self.poll = threading.Thread(None, self.poll_threads, 'poll_threads')
        self.poll.start()


    def already_processing(self, pid):
        if pid in self.threads:
            return True
        else:
            return False


    def new_queue(self):
        return OrderedDict()


    def queue_process(self, func, pid, args, logger=None, call_back=None):
        self.process_queue[func] = pid, args, logger, call_back


    def drain_queue(self, ProcessHandler, queue, mode):        
        pids = []
        for pid, data in queue.items():
            pids.append(pid)
            func, args, logger, callback = data            
            if mode == 'sync':
                if type(args) == type(tuple()):
                    args = (self,) + args if args is not None else (self,)
                else:
                    args = (self, args) if args is not None else (self,)
                func(*args)
            elif mode == 'async':
                self.add_process(func, pid, args, logger, callback)
        while True:
            finished = 0
            pids = []
            for pid, thread in self.threads.items():
                pids.append(pid)
            for id in pids:
                if id not in pids and id not in self.item_queue:              
                    finished += 1
            if finished == len(pids):
                break
            else:
                time.sleep(1)


    def add_process(self, func, pid, args, logger=None, call_back=None):
        time.sleep(1.0)
        if Util.HALT:
            Util.HALT = False
        if self.already_processing(pid):
            return False
        if self.processes >= self.cores:
            self.wait(func, pid, args)
            return False
        else:
            if type(args) == type(tuple()):
                args = (self,) + args if args is not None else (self,)
            else:
                args = (self, args) if args is not None else (self,)
            
            new_thread = threading.Thread(None, func, pid, (args))
            new_thread.func = func.__name__
            new_thread.daemon = True
            new_thread.logger = logger
            new_thread.call_back = call_back
            new_thread.start_time = Util.microseconds()
            new_thread.start()
            self.threads[pid] = new_thread
            if new_thread.func is not 'drain_queue':
                self.processes += 1
                #print 'added ' + str(pid) + ' #processes:' + str(self.processes)
            if not self.poll:
                self.init_poll()
            if logger:
                new_thread.logger.message('New Thread Started -->   ' +
                                          'Identifier: ' + str(pid) + 
                                          '   Task: ' + str(func), 'processing')
            return True


    def wait(self, func, pid, args):
        #print pid + ' waiting...'
        if not pid in self.item_queue:
            self.item_queue[pid] = (func, args)


    def finish(self):
        for pid, thread in self.threads.items():
            if thread.is_alive():
                thread.logger.message('Stopping Thread ' + str(pid), 'processing')
                Util.HALT = True
        self.poll = None


    def destroy_thread(self, pid):
        if pid in self.threads:
            thread.logger.message('Destroying Thread ' + str(pid), 'processing')
            del self.threads[pid]
            self.processes -= 1
            

    def poll_threads(self):
        while True:          
            time.sleep(3.0)
            inactive_threads = []
            for pid, thread in self.threads.items():
                if not thread.is_alive():
                    thread.end_time = Util.microseconds()
                    thread.logger.message('Thread ' + str(pid) + ' Finished', 'processing')
                    inactive_threads.append(pid)
                else:
                    pass
            inactive_threads.reverse()
            for pid in inactive_threads:
                if self.threads[pid].call_back is not None:
                    self.threads[pid].call_back(self.threads[pid])
                if self.threads[pid].func is not 'drain_queue':
                    self.processes -= 1
                    #print 'thread ' + self.threads[t_num].name + ' finished   #processes ' + str(self.processes)
                del self.threads[pid]
            queue = []
            for pid, item in self.item_queue.items():
                if self.add_process(item[0], pid, item[1]):
                    queue.append(pid)
                else:
                    break
            queue.reverse()
            for pid in queue:
                del self.item_queue[pid]
            if self.processes == 0:
                #self.finish()
                break
                #pass
            

    def check_thread_exceptions(self):
        try:
            pid, message, logger = ProcessHandler.ThreadQueue.get()
        except Queue.Empty:
            return None
        else:
            if Environment.interface == 'gui':
                Common.dialog(message=message)
            elif Environment.interface == 'command':
                self.finish()
                #Util.bail(message)
            self.destroy_thread(pid)

                
    def run_main(self, ProcessHandler, book):
        book.logger.message("Began Main Processing...")               
        #book.start_time = Util.microseconds()
        if book.settings['respawn']:
            Environment.clean_dirs(book.dirs)
            Environment.make_scandata(book)
        self.FeatureDetection = FeatureDetection(self, book)
        queue = self.new_queue()
        queue[book.identifier + '_featuredetection'] = self.FeatureDetection.pipeline, None, book.logger, None
        self.drain_queue(ProcessHandler, queue, 'async')
    
        self.make_standard_crop(ProcessHandler, book)
        #end_time = Util.microseconds()
        #start_time = ProcessHandler
        book.logger.message("Finished Main Processing in " + str((end_time - book.start_time)/60) + ' minutes')
        

    def autopaginate(self):
        pass
        #if Environment.settings['autopaginate']:
        #    autoPaginator = AutoPaginate()
        #    autoPaginator.run(book.page_number_candidates)


    def make_standard_crop(self, ProcessHandler, book):
        standardcrop = StandardCrop(book)
        standardcrop.make_standard_crop()


    def run_cropper(self, ProcessHandler, book, crop, 
                    grayscale=False, normalize=False, invert=False):
        book.logger.message("Began Cropping...")               
        queue = self.new_queue()
        self.Cropper = Cropper(book)
        chunk = (book.page_count-2)/self.cores
        for core in range(0, self.cores):
            start = (core * chunk) + 1
            if core == self.cores - 1:
                end = book.page_count-1
            else:
                end = (start + chunk)
            queue[book.identifier + '_' + str(start) + '_cropper'] = (self.Cropper.pipeline, 
                                                                      (start, end, crop, grayscale, normalize, invert),
                                                                      book.logger, None)
            #self.queue_process(self.Cropper.pipeline, 
            #                   book.identifier + '_' + str(start) + '_cropper', 
            #                   (start, end, crop, grayscale, normalize, invert),
            #                   book.logger)    
        self.drain_queue(ProcessHandler, queue, 'async')
            #self.add_process(self.Cropper.pipeline, 
            #                 book.identifier + '_' + str(start) + '_cropper', 
            #                 (start, end, crop, grayscale, normalize, invert),
            #                 book.logger)    
        

    def run_ocr(self, ProcessHandler, book, language):
        self.OCR = OCR(book)
        queue = self.new_queue()
        chunk = (book.page_count-2)/self.cores
        for core in range(0, self.cores):
            start = (core * chunk) + 1
            if core == self.cores - 1:
                end = book.page_count-1
            else:
                end = (start + chunk)

            queue[book.identifier + '_' + str(start) + '_ocr'] = (self.OCR.tesseract_hocr_pipeline, 
                                                                  (start, end, language),
                                                                  book.logger, None)   
            #self.add_process(self.OCR.tesseract_hocr_pipeline, 
            #                 book.identifier + '_' + str(start) + '_ocr', 
            #                 (start, end, language),
            #                 book.logger)    
        self.drain_queue(ProcessHandler, queue, 'async')


    def derive_formats(self, ProcessHandler, book, formats):
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
