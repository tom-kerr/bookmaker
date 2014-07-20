import os 
import time
from copy import copy
from util import Util

from events import handle_events
from environment import Environment
from .operation import Operation

class ImageCapture(Operation):
    
    components = [('gphoto2', 'Gphoto2'),
                  ('raw2thumb', 'Raw2Thumb')]
                  
    def __init__(self, ProcessHandler, book):
        self.ProcessHandler = ProcessHandler
        self.book = book
        try:
            super(ImageCapture, self).__init__(ImageCapture.components)
            self.init_components(self.book)
            self.determine_capture_style()
            self.init_devices()
        except Warning:
            raise
        except (Exception, BaseException):
            pid = self.make_pid_string('__init__')
            self.ProcessHandler.join((pid, Util.exception_info()))
            
    def determine_capture_style(self):
        self.captures = {}
        if self.book.capture_style is not None:
            self.capture_style = self.book.capture_style
        else:
            device_count = len(self.Gphoto2.devices)
            if device_count == 1:
                self.capture_style = 'Single'
            elif device_count == 2:
                self.capture_style = 'Dual'
            else:
                self.capture_style = None

    def init_devices(self):
        for device in self.Gphoto2.devices.keys():
            self.captures[device] = False

    def are_devices(self):
        if self.Gphoto2.devices:
            return True
        else:
            return False

    def get_device(self, name):
        for device, info in self.Gphoto2.devices.items():
            if info['side'] == name:
                return device
        return False
        
    def capture_from_devices(self, **kwargs):
        self.capture_time = 0
        queue = self.ProcessHandler.new_queue()
        for side, info in kwargs.items():
            kwargs[side].update({'filename': side + '.jpg'})
            queue.add(self.book, cls='ImageCapture', mth='capture', 
                      kwargs=kwargs[side])
        queue.drain(mode='async', thread=True)

    @handle_events
    def capture(self, **kwargs):
        self.Gphoto2.run(**kwargs)
        
    def on_success(self, device, *args, **kwargs):
        self.captures[device] = True
        try:
            src = kwargs.get('filename')
            raw_dst = kwargs.get('raw_dst')
            os.rename(src, raw_dst)
            leaf = kwargs.get('leaf')
            scaled_dst = kwargs.get('scaled_dst')
            rot_dir = kwargs.get('rot_dir')
            self.Raw2Thumb.run(leaf, in_file=raw_dst, 
                               out_file=scaled_dst, 
                               rot_dir=rot_dir)
        except (OSError, RuntimeError):
            pid = self.make_pid_string('on_success')
            self.ProcessHandler.join((pid, Util.exception_info()))

    def on_failure(self, **kwargs):
        pid = self.make_pid_string('on_failure')
        self.ProcessHandler.join((pid, Util.exception_info()))

    def on_exit(self, device=None, **kwargs):
        self.capture_time = 0
        if device:
            self.captures[device] = False
        else:
            for device in self.captures.keys():
                self.captures[device] = False
