
import re

from .component import Component
from util import Util


class Gphoto2(Component):
    """ Handles capturing images from USB-connected devices.
    """
    args = [['--auto-detect', 'autodetect'],
            ['--capture-image-and-download', 'capture'], 
            ['--list-all-config', 'list_config'],
            ['--port', 'port'],
            ['--filename', 'filename'],
            ['--force-overwrite', 'force_overwrite'],
            ['--no-keep', 'no_keep']]
    executable = 'gphoto2'
    devices = {}
    attr_fields = ['Label', 'Camera Model', 'Camera Manufacturer', 
                   'Serial Number', 'Device Version']
    
    def __init__(self, book):
        super(Gphoto2, self).__init__()
        self.book = book
        self.find_devices()
            
    def find_devices(self):
        kwargs = {}
        kwargs['autodetect'] = ''
        kwargs['capture'] = None
        kwargs['list_config'] = None
        kwargs['port'] = None
        kwargs['filename'] = None
        kwargs['force_overwrite'] = None
        kwargs['no_keep'] = None
        result = self.execute(kwargs, return_output=True)    
        devices = re.findall('usb:[0-9,]+', result['output'])
        if not devices:
            Gphoto2.devices = {}
        else:
            for device in devices:
                kwargs['autodetect'] = None
                kwargs['capture'] = None
                kwargs['list_config'] = ''
                kwargs['port'] = device
                kwargs['filename'] = None
                kwargs['force_overwrite'] = None
                kwargs['no_keep'] = None
                result = self.execute(kwargs, return_output=True)
                Gphoto2.devices[device] = {}
                for field in Gphoto2.attr_fields:
                    info = re.findall('Label: '+field+'\nType: .+\nCurrent: .+', result['output'])
                    if info:
                        labels = info[0].split('\n')
                        for i in range(0, len(labels), 3):
                            Gphoto2.devices[device][labels[i].lstrip('Label: ')] = \
                                labels[i+2].lstrip('Current: ')
            remove = []
            for device in Gphoto2.devices.keys():
                if device not in devices:
                    remove.append(device)
            for device in remove:
                del Gphoto2.devices[device]                                   
        
    def run(self, **kwargs):
        device = kwargs['device']
        kwargs['autodetect'] = None
        kwargs['capture'] = ''
        kwargs['list_config'] = None
        kwargs['port'] = device
        kwargs['force_overwrite'] = ''
        kwargs['no_keep'] = ''
        kwargs['device'] = device
        output = self.execute(kwargs, return_output=True)
        return output

    def on_failure(**kwargs):
        device = kwargs['device']
        output = kwargs['output']
        raise OSError('Failed to capture from device ' + 
                      device + ':\n\n' + str(output))

