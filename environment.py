import os
import sys
import platform
import glob
import re
import datetime
import time
import shutil
from collections import OrderedDict
import logging

import yaml
from PIL import Image
from lxml import etree

from util import Util
from datastructures import Crop


class Environment(object):
    """ Handles the creation of Book objects, including directory 
        creation/cleaning and holding state pertaining to the
        current system.
    """

    settings = OrderedDict([('respawn', True),
                            ('autopaginate', False),
                            ('make_cornered_scaled', False),
                            ('draw_clusters', False),
                            ('draw_removed_clusters', False),
                            ('draw_invalid_clusters', False),
                            ('draw_content_dimensions', False),
                            ('draw_page_number_candidates', False),
                            ('draw_noise', False),
                            ('devices', None)])
    interface = 'shell'
    proc_mode = None
    dir_mode = 0o755
    scale_factor = 4

    def __init__(self, interface):
        Environment.interface = interface
        Environment.set_current_path()
        Environment.check_system()

    @staticmethod
    def get_books(dir_list, args, stage, capture_style=None):
        books = []
        if not isinstance(dir_list, list):
            dir_list = [dir_list,]
        for root_dir in dir_list:
            root_dir = root_dir.rstrip('/')
            valid_subdirs = Environment.find_valid_subdirs(root_dir)
            if not valid_subdirs:
                raw_dir = Environment.is_sane(root_dir)
                if raw_dir:
                    raw_data = Environment.get_raw_data(root_dir, raw_dir)
                    books.append(Book(root_dir, raw_dir, raw_data, 
                                      stage, capture_style))
            else:
                for subdir in valid_subdirs:
                    raw_dir = Environment.is_sane(subdir)
                    if raw_dir:
                        raw_data = Environment.get_raw_data(subdir, raw_dir)
                        books.append(Book(subdir, raw_dir, raw_data, 
                                          stage, capture_style))
        if len(books) < 1:
            Util.bail('No valid directories found for processing...')
        return books

    @staticmethod
    def check_system():
        plat = sys.platform
        if re.search('linux', plat):
            Environment.platform = 'linux'
        if re.search('darwin', plat):
            Environment.platform = 'darwin'
        if re.search('win', plat):
            Environment.platform = 'win'
        Environment.architecture = platform.uname()[-2]

    @staticmethod
    def set_current_path():
        Environment.current_path = os.path.abspath(os.path.dirname(sys.argv[0]))
        sys.path.append(Environment.current_path)

    @staticmethod
    def find_valid_subdirs(root_dir):
        """ We accept as the root directory a directory containing 
            items (sub-directories) to be processed, and so we check
            for the presence of such items and if found initialize and 
            add them to our list of books.
        """
        valid_subdirs = []
        subdirs = os.listdir(root_dir)
        for subdir in subdirs:
            path = root_dir + '/' + subdir
            raw_dir = Environment.is_sane(path)
            if raw_dir:
                valid_subdirs.append(path)
        return valid_subdirs

                #raw_data = Environment.get_raw_data(root_dir, 
                #                                    subdir + '/' + raw_dir)
                #self.books.append(Book(root_dir, raw_dir, raw_data,
                #                       self.stage, self.capture_style))
        #if len(self.books) > 1:
        #    return True
        #else:
        #    return False

    @staticmethod
    def create_new_book_stub(location, identifier):
        root_dir = location + '/' + identifier
        raw_dir = root_dir + '/' + identifier + '_raw_'
        os.mkdir(root_dir, Environment.dir_mode)
        os.mkdir(raw_dir, Environment.dir_mode)

    @staticmethod
    def find_raw_dir(dir):
        dir_items = os.listdir(dir)
        for item in dir_items:
            if re.search("(_raw_|_RAW_|_raw$|_RAW$)", item):
                if os.path.isdir(dir + '/' + item):
                    return item

    @staticmethod
    def is_sane(root_dir):
        """ Checks that our root directory is in fact a directory,
            and that it contains a directory of raw images.
        """
        if not os.path.isdir(root_dir):
            return False
        raw_dir = Environment.find_raw_dir(root_dir)
        if raw_dir is None:
            return False
        else:
            return raw_dir

    @staticmethod
    def get_raw_data(root_dir, raw_dir):
        raw_images, raw_dimensions = \
            Environment.get_raw_images(root_dir + '/' + raw_dir)
        return {'page_count': len(raw_images),
                'images': raw_images,
                'dimensions': raw_dimensions}

    @staticmethod
    def get_raw_images(dir):
        raw_images = glob.glob(dir + '/*')
        raw_dimensions = {}
        for leaf, file in enumerate(raw_images):
            if re.search("[\.(jpg|JPG|jpeg|JPEG)]$",file) is None:
                Util.bail("non-jpg file found in "+ str(raw_dir) +
                                 ": " + str(file))
            else:
                raw_dimensions[leaf] = {}
                raw_dimensions[leaf]['width'], \
                    raw_dimensions[leaf]['height'] = Image.open(file).size
        raw_images.sort()
        return raw_images, raw_dimensions

    @staticmethod
    def make_dir(dir):
        if not os.path.isdir(dir):
            os.mkdir(dir, Environment.dir_mode)

    @staticmethod
    def clean_dir(dir):
        if os.path.isdir(dir):
            for f in os.listdir(dir):
                if os.path.isdir(dir + '/' + f):
                    shutil.rmtree(dir + '/' + f)
                else:
                    os.remove(dir + '/' + f)
                  

class Book(object):
    """ Holds the state of a particular item.


    stages: new_capture, append_capture, process, edit

    """

    def __init__(self, root_dir, raw_dir, raw_data, stage, capture_style=None):
        self.root_dir = root_dir
        self.raw_image_dir = raw_dir
        self.page_count = raw_data['page_count']
        self.raw_images = raw_data['images']
        self.raw_image_dimensions = raw_data['dimensions']
        self.capture_style = capture_style
        self.identifier = os.path.basename(self.root_dir)
        self.scandata_file = self.root_dir + '/' + self.identifier + '_scandata.xml'
        self.scaled_center_point = {}
        for leaf in range(0, self.page_count):
            self.scaled_center_point[leaf] = \
                {'x': (self.raw_image_dimensions[leaf]['height']/
                       Environment.scale_factor)/2,
                 'y': (self.raw_image_dimensions[leaf]['width']/
                       Environment.scale_factor)/2}
        self.dirs = {
            'book':          self.root_dir,
            'raw_images':    self.root_dir + '/' + self.raw_image_dir,
            'logs':          self.root_dir + '/' + self.identifier + '_logs',
            'scaled':        self.root_dir + '/' + self.identifier + '_scaled',
            }
        for name, dir in self.dirs.items():
            if not os.path.exists(dir):
                Environment.make_dir(dir)
        self.init_logger()
        self.load_settings()
        self.log_settings()
        self.scandata = Scandata()
        self.init_scandata()

        if stage == 'new_capture':
            pass
        elif stage == 'append_capture':
            self.determine_capture_style()
        elif stage == 'process':
            self.determine_capture_style()
            self.init_crops(strict=True)
        elif stage == 'edit':
            #self.init_scandata()
            self.determine_capture_style()
            self.init_crops(import_from_scandata=True, strict=True)        
        self.create_time = time.time()
        self.start_time = time.time()

    def determine_capture_style(self):
        bookData = self.scandata.tree.find('bookData')
        devices = bookData.find('devices')
        if devices is None:
            self.capture_style = None
        else:
            count = devices.get('count')
            if count == '1':
                self.capture_style = 'Single'
            elif count == '2':
                self.capture_style = 'Dual'
            else:
                self.capture_style = None

    def init_logger(self):
        self.logger = logging.getLogger(self.identifier)
        self.logger.setLevel(logging.DEBUG)

        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(name)s %(threadName)s %(levelname)s --> %(message)s\n')
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        fh = logging.FileHandler(self.dirs['logs'] + '/' + self.identifier + '.log', 'w')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(threadName)s %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        debug = logging.FileHandler(self.dirs['logs'] + '/' + self.identifier + '.debug.log', 'w')
        debug.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(threadName)s %(levelname)s %(message)s')
        debug.setFormatter(formatter)
        self.logger.addHandler(debug)

    def load_settings(self, args=None):
        path = self.root_dir
        settings_file = path + '/settings.yaml'
        try:
            stream = open(settings_file, 'r')
            settings = yaml.load(stream)
        except (OSError, IOError, yaml.parser.ParserError) as e:
            self.logger.warning('Failed to load settings.yaml; ' + 
                                str(e)+'; initializing with defaults.')
            settings = Environment.settings
            self.write_settings(settings)
        finally:
            if args:
                if args.respawn:
                    settings['respawn'] = True
                elif args.no_respawn:
                    settings['respawn'] = False
                if args.make_cornered_scaled is not None:
                    settings['make_cornered_scaled'] = args.make_cornered_scaled
                if args.draw_clusters is not None:
                    settings['draw_clusters'] = args.draw_clusters
                if args.draw_removed_clusters is not None:
                    settings['draw_removed_clusters'] = args.draw_removed_clusters
                if args.draw_invalid_clusters is not None:
                    settings['draw_invalid_clusters'] = args.draw_invalid_clusters
                if args.draw_content_dimensions is not None:
                    settings['draw_content_dimensions'] = \
                        args.draw_content_dimensions
                if args.draw_page_number_candidates is not None:
                    settings['draw_page_number_candidates'] = \
                        args.draw_page_number_candidates
                if args.draw_noise is not None:
                    settings['draw_noise'] = args.draw_noise
                settings['devices'] = None
                if args.save_settings:
                    self.write_settings(settings)
            self.settings = settings

    def write_settings(self, settings):
        path = self.root_dir
        settings_file = path + '/settings.yaml'
        try:
            with open(settings_file, 'w') as stream:
                yaml.dump(settings,
                          stream,
                          explicit_start=True,
                          default_flow_style=False)
        except (OSError, IOError) as e:
            self.logger.warning('Failed to save settings! ', str(e))
        
    def log_settings(self):
        self.logger.debug('*****SETTINGS*****')
        for setting, value in self.settings.items():
            self.logger.debug(setting + ':' + str(value))
        self.logger.debug('*****SETTINGS*****')

    def init_scandata(self):
        if self.capture_style is None:
            capture_style = 'Dual'
        if os.path.exists(self.scandata_file) and \
                os.stat(self.scandata_file)[6] > 0:
            try:
                self.scandata.new_from_file(self.scandata_file)
            except etree.ParseError:
                if self.settings['respawn']:
                    #if the scandata is corrupt, but we're looking to start over
                    #anyhow, we'll create a fresh xml doc.
                    self.scandata.new(self.identifier,
                                      self.page_count,
                                      self.raw_image_dimensions,
                                      self.scandata_file,
                                      capture_style)
                else:
                    raise
        else:
            self.scandata.new(self.identifier,
                              self.page_count,
                              self.raw_image_dimensions,
                              self.scandata_file,
                              capture_style)

    def init_crops(self, import_from_scandata=None, strict=True):
        if import_from_scandata is None:
            import_from_scandata = False if self.settings['respawn'] else True
        self.crops = {}
        for crop in ('cropBox', 'pageCrop', 'standardCrop', 'contentCrop'):
            cropObj = Crop(crop, self.page_count,
                           self.raw_image_dimensions,
                           self.scandata, import_from_scandata, strict)
            setattr(self, crop, cropObj)
            self.crops[crop] = getattr(self, crop)
                
    def add_dirs(self, dirs):
        for name, dir in dirs.items():
            if not os.path.isdir(dir):
                Environment.make_dir(dir)
            self.dirs[name] = dir

    def clean_dirs(self):
        for name, dir in self.dirs.items():
            if name in ('book', 'raw_images', 'logs'):
                pass
            else:
                Environment.clean_dir(dir)


class Scandata(object):
    """ XML storage medium for structural metadata, identical 
        to the Internet Archive's "scandata". 
    """

    def __init__(self):
        self.filename = None
        self.tree = None
        self.locked = False
                        
    def new_from_file(self, filename):
        self.filename = filename
        with open(self.filename, 'r+') as f:
            parser = etree.XMLParser(remove_blank_text=True)
            self.tree = etree.parse(f, parser)
        
    def new(self, identifier, page_count, raw_image_dimensions, 
            filename, capture_style):
        self.filename = filename
        root = etree.Element('book')
        book_data = etree.SubElement(root,'bookData')
        book_id = etree.SubElement(book_data,'bookId')
        book_id.text = str(identifier)
        leaf_count = etree.SubElement(book_data,'leafCount')
        leaf_count.text = str(page_count)
        devices = etree.SubElement(book_data,'devices')
        if capture_style == 'Single':
            devices.set('count', '1')
        elif capture_style == 'Dual':
            devices.set('count', '2')
        page_data = etree.SubElement(root, 'pageData')
        for leaf in range(0, page_count):
            side  = 'LEFT' if leaf%2==0 else 'RIGHT'
            page = etree.SubElement(page_data, 'page')
            page.set('leafNum', str(leaf))
            handside = etree.SubElement(page, 'handSide')
            handside.text = str(side)
            page_type = etree.SubElement(page, 'pageType')
            page_type.text = 'Normal' if leaf in range(1, page_count-1) else 'Delete'
            ataf = etree.SubElement(page, 'addToAccessFormats')
            ataf.text = 'true' if leaf in range(1, page_count-1) else 'false'
            rotate_degree = etree.SubElement(page, 'rotateDegree')
            if capture_style == 'Dual':
                rotate_degree.text = '-90' if leaf%2==0 else '90'
            elif capture_style == 'Single':
                rotate_degree.text = '0'
            skew_angle = etree.SubElement(page, 'skewAngle')
            skew_angle.text = '0.0'
            skew_conf = etree.SubElement(page, 'skewConf')
            skew_conf.text = '0.0'
            skew_active = etree.SubElement(page, 'skewActive')
            skew_active.text = 'False'
            orig_width = etree.SubElement(page, 'origWidth')
            orig_width.text = str(raw_image_dimensions[leaf]['width'])
            orig_height = etree.SubElement(page, 'origHeight')
            orig_height.text = str(raw_image_dimensions[leaf]['height'])
            crop_box = Crop.new_crop_element(page, 'cropBox')
            page_number = etree.SubElement(page, 'pageNumber')
        self.tree = etree.ElementTree(root)
        self.write_to_file()

    def write_to_file(self):
        while True:
            if self.locked:
                time.sleep(0.5)
            self.locked = True
            if os.path.exists(self.filename):
                mode = 'r+b'
            else:
                mode = 'w+b'
            try:
                with open(self.filename, mode) as f:
                    self.tree.write(f, pretty_print=True)
            except (OSError, IOError) as e:
                raise Exception ('Failed to write to scandata! \n' + str(e))
            else:
                break
            finally:
                self.locked = False
                

