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


class ProcessHandling:

    def __init__(self):
        try:
            self.cores = multiprocessing.cpu_count()
        except NotImplemented:
            self.cores = 1
        self.active_threads = {}
        self.inactive_threads = self.new_queue()
        self.processes = 0
        
        self.ThreadQueue = Queue.Queue()
        #self.process_queue = self.new_queue()
        self.item_queue = self.new_queue()
        self.errors = []
        
        self.poll = None
        self.monitor_threads = False
        self.FeatureDetection = None
        self.Cropper = None
        self.OCR = None


    def init_poll(self):
        self.poll = threading.Thread(None, self.poll_threads, 'poll_threads')
        self.poll.start()


    def already_processing(self, pid):
        if pid in self.active_threads:
            return True
        else:
            return False


    def new_queue(self):
        return OrderedDict()


    def drain_queue(self, queue, mode):        
        pids = []
        for pid, data in queue.items():
            pids.append(pid)
            func, args, logger, callback = data            
            if mode == 'sync':
                if type(args) != type(tuple()):
                    args = tuple((args,)) if args is not None else ()
                try:
                    func(*args)
                except Exception as e:
                    return
            elif mode == 'async':
                self.add_process(func, pid, args, logger, callback)
        while True:
            try:
                self.handle_thread_exceptions()
            except Exception as e:
                raise Exception(str(e))
            if Util.HALT:
                Util.halt()
            finished = 0
            active_pids = []
            for pid, thread in self.active_threads.items():
                active_pids.append(pid)
            for id in pids:
                if id not in active_pids and id not in self.item_queue:              
                    finished += 1
            if finished == len(pids):
                break
            else:
                time.sleep(1)


    def clear_errors(self, pid):
        remove = None
        for num, item in enumerate(self.errors):
            if item == pid:
                remove = num
        if remove is not None:
            del self.errors[remove]


    def add_process(self, func, pid, args, logger=None, call_back=None):
        time.sleep(0.25)
        if Util.HALT:
            Util.HALT = False
        if self.already_processing(pid):
            return False
        self.clear_errors(pid)
        if self.processes >= self.cores:
            self.wait(func, pid, args)
            return False
        else:
            if type(args) != type(tuple()):
                args = tuple((args,)) if args is not None else ()
            new_thread = threading.Thread(None, func, pid, args)
            new_thread.func = func.__name__
            new_thread.daemon = True
            new_thread.logger = logger
            new_thread.call_back = call_back
            new_thread.start_time = Util.microseconds()
            new_thread.start()
            self.active_threads[pid] = new_thread
            if new_thread.func not in ('drain_queue', 'handle_thread_exceptions', 'run_main', 
                                       'run_ocr', 'run_cropper', 'derive_formats'):
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
        destroy = []
        for pid, thread in self.active_threads.items():
            destroy.append(pid)
        for pid in destroy:
            self.destroy_thread(pid)
        self.item_queue = self.new_queue()
        #self.process_queue = self.new_queue()
        Util.HALT = True
        self.poll = None
        self.monitor_threads = False


    def destroy_thread(self, pid):
        if pid in self.active_threads:
            if self.active_threads[pid].logger:
                self.active_threads[pid].logger.message('Destroying Thread ' + str(pid), 'processing')
            if self.active_threads[pid].func not in ('drain_queue', 'run_main', 'run_ocr', 
                                                     'run_cropper', 'derive_formats'):
                self.processes -= 1            
            self.active_threads[pid]._Thread__stop()
            del self.active_threads[pid]


    def poll_threads(self):
        while True:          
            time.sleep(3.0)
            inactive = {}
            for pid, thread in self.active_threads.items():
                if not thread.is_alive():
                    thread.end_time = Util.microseconds()
                    if thread.logger:
                        thread.logger.message('Thread ' + str(pid) + ' Finished', 'processing')
                    inactive[pid] = thread                        
            for pid, thread in inactive.items():
                if thread.call_back is not None:
                    thread.call_back(thread)
                if thread.func not in ('drain_queue', 'run_main', 'run_ocr', 
                                       'run_cropper', 'derive_formats'):
                    self.processes -= 1
                    #print 'thread ' + pid + ' finished   #processes ' + str(self.processes)
                self.inactive_threads[pid] = thread
                del self.active_threads[pid]
            queue = []
            for pid, item in self.item_queue.items():
                if self.add_process(item[0], pid, item[1]):
                    queue.append(pid)
                else:
                    break
            queue.reverse()
            for pid in queue:
                del self.item_queue[pid]
            if (self.processes == 0 and 
                not [thread.func for pid, thread in self.active_threads.items() 
                     if thread.func in ('drain_queue', 'run_main', 'run_ocr', 
                                        'run_cropper', 'derive_formats')]):
                break


    def monitor_thread_exceptions(self):
        self.monitor_threads = True
        try:
            pid, message, logger = self.ThreadQueue.get_nowait()
        except Queue.Empty:
            pass
        else:
            msg = 'Exception in thread ' + pid + ':\n' + message
            if Environment.interface == 'gui':
                Common.dialog(message=msg)
            elif Environment.interface == 'command':
                print msg
            self.ThreadQueue.put((pid, message, logger))            
        if Util.HALT:
            return False
        else:
            return True


    def handle_thread_exceptions(self):
        try:
            pid, message, logger = self.ThreadQueue.get_nowait()
        except Queue.Empty:
            pass
        else:
            self.errors.append(pid)
            msg = 'Exception in thread ' + pid + ':\n' + message
            self.destroy_thread(pid)
            raise Exception(msg)

                
    def run_main(self, book):
        book.logger.message("Began Main Processing...")               
        if book.settings['respawn']:
            Environment.clean_dirs(book.dirs)
            Environment.make_scandata(book)
        self.FeatureDetection = FeatureDetection(self, book)
        queue = self.new_queue()
        queue[book.identifier + '_featuredetection'] = self.FeatureDetection.pipeline, None, book.logger, None
        try:
            self.drain_queue(queue, 'async')
            self.make_standard_crop(book)
        except Exception as e:
            Util.bail(str(e))            
        end_time = self.inactive_threads[book.identifier + '_featuredetection'].end_time
        start_time = self.inactive_threads[book.identifier + '_featuredetection'].start_time
        book.logger.message("Finished Main Processing in " + str((end_time - start_time)/60) + ' minutes')
        

    def autopaginate(self):
        pass
        #if Environment.settings['autopaginate']:
        #    autoPaginator = AutoPaginate()
        #    autoPaginator.run(book.page_number_candidates)


    def make_standard_crop(self, book):
        standardcrop = StandardCrop(book)
        standardcrop.make_standard_crop()


    def run_cropper(self, book, crop, 
                    grayscale=False, normalize=False, invert=False):
        book.logger.message("Began Cropping...")               
        queue = self.new_queue()
        self.Cropper = Cropper(self, book)
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
        try:
            self.drain_queue(queue, 'async')
        except Exception as e:
            raise Exception(str(e))
        

    def run_ocr(self, book, language):
        book.logger.message('Began OCR...')
        self.OCR = OCR(self, book)
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
        try:
            self.drain_queue(queue, 'async')
        except Exception as e:
            raise Exception(str(e))
        

    def derive_formats(self, book, formats):
        self.Derive = Derive(self, book)
        queue = self.new_queue()
        for f in formats:
            if f == 'text':
                if self.OCR is not None:
                    ocr_data = self.OCR.ocr_data
                else:
                    ocr_data = None
                queue[book.identifier + '_' + f] = (self.Derive.full_plain_text, 
                                                    ocr_data, book.logger, None)
            elif f == 'pdf':
                queue[book.identifier + '_' + f] = (self.Derive.pdf, 
                                                    None, book.logger, None)
            elif f == 'djvu':
                queue[book.identifier + '_' + f] = (self.Derive.djvu, 
                                                    None, book.logger, None)
            elif 'epub':
                pass

        try:
            self.drain_queue(queue, 'async')
        except Exception as e:
            raise Exception(str(e))
