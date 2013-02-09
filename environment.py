import os
import sys
import glob
import re
import Image
import yaml
import datetime
import time
from collections import OrderedDict
from lxml import etree

from util import Util
from datastructures import Crop

class Environment:

    settings = OrderedDict([('respawn', True),
                            ('autopaginate', False),
                            ('make_cornered_thumbs', False),
                            ('draw_clusters', False),
                            ('draw_removed_clusters', False),
                            ('draw_invalid_clusters', False),
                            ('draw_content_dimensions', False),
                            ('draw_page_number_candidates', False),
                            ('draw_noise', False)])
    interface = 'command'
    proc_mode = None
    dir_mode = 0755
    scale_factor = 4


    def __init__(self, dir_list, args=None):
        Environment.set_current_path()
        self.books = []
        for root_dir in dir_list:
            if self.find_valid_subdirs(root_dir):
                Environment.proc_mode = 'Batch'
            else:
                Environment.proc_mode = 'Single'
                raw_data = Environment.is_sane(root_dir)
                if raw_data:
                    self.init_new_book(root_dir, raw_data)
        if len(self.books) < 1:
            Util.bail('No valid directories found for processing...')
        for book in self.books:
            book.start_time = time.time()
            book.settings = Environment.load_settings(book.root_dir, args)
            book.init_crops()
            Environment.make_dirs(book.dirs)
            book.logger = Logger()
            Environment.set_logs(book)
            Environment.log_settings(book)


    @staticmethod
    def log_settings(book):        
        book.logger.message('*****SETTINGS*****')
        for setting, value in book.settings.items():
            book.logger.message(setting + ':' + str(value))
        book.logger.message('*****SETTINGS*****\n')


    @staticmethod
    def set_current_path():
        Environment.current_path = os.path.abspath(os.path.dirname(sys.argv[0]))
        sys.path.append(Environment.current_path)


    def find_valid_subdirs(self, root_dir):
        subdirs = os.listdir(root_dir)
        for dir in subdirs:
            path = root_dir + '/' + dir
            raw_data = Environment.is_sane(path)
            if raw_data:
                self.init_new_book(path, raw_data)
        if len(self.books) > 1:
            return True
        else:
            return False


    def init_new_book(self, book_dir, raw_data):
        book = BookData(book_dir, raw_data)
        if book not in self.books:
            self.books.append(book)
        

    @staticmethod
    def find_raw_dir(dir):
        dir_items = os.listdir(dir)
        for item in dir_items:
            if re.search("(_raw_|_RAW_)", item):
                if os.path.isdir(dir + '/' + item):
                    return item
                

    @staticmethod
    def is_sane(dir):
        if not os.path.isdir(dir):
            return False
        raw_dir = Environment.find_raw_dir(dir)
        if raw_dir is None:
            return False
        else:
            raw_images, raw_dimensions = Environment.get_raw_images(dir + '/' + raw_dir)
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
                raw_dimensions[leaf] = Image.open(file).size
                if leaf > 0:
                    if (raw_dimensions[leaf][0] != raw_dimensions[leaf-1][0] or
                        raw_dimensions[leaf][1] != raw_dimensions[leaf-1][1]):
                        Util.bail('heterogenous raw image stack resolution in ' + 
                                  str(raw_dir) + ' (leaf ' + str(leaf) + ')')
        raw_images.sort()
        return raw_images, raw_dimensions


    @staticmethod
    def load_settings(path, args=None):
        settings_file = path + '/settings.yaml'
        try:
            stream = file(settings_file, 'r')
            settings = yaml.load(stream)
        except:
            Environment.write_settings(path, Environment.settings)
            return Environment.settings
        if args:
            if args.respawn:
                settings['respawn'] = True
            elif args.no_respawn:
                settings['respawn'] = False
            if args.make_cornered_thumbs is not None:
                settings['make_cornered_thumbs'] = args.make_cornered_thumbs
            if args.draw_clusters is not None:
                settings['draw_clusters'] = args.draw_clusters
            if args.draw_removed_clusters is not None:
                settings['draw_removed_clusters'] = args.draw_removed_clusters
            if args.draw_invalid_clusters is not None:
                settings['draw_invalid_clusters'] = args.draw_invalid_clusters
            if args.draw_content_dimensions is not None:
                settings['draw_content_dimensions'] = args.draw_content_dimensions
            if args.draw_page_number_candidates is not None:
                settings['draw_page_number_candidates'] = args.draw_page_number_candidates
            if args.draw_noise is not None:
                settings['draw_noise'] = args.draw_noise
            if args.save_settings:
                Environment.write_settings(path, settings)
        #default_settings = Environment.settings
        #for setting, value in settings.iteritems():
        #    if setting in default_settings:
        #        default_settings[setting] = value
        return settings


    @staticmethod
    def write_settings(path, settings):
        settings_file = path + '/settings.yaml'
        try:
            stream = file(settings_file, 'w')
            yaml.dump(settings, 
                      stream, 
                      explicit_start=True, 
                      default_flow_style=False)
        except:
            print 'Failed to save settings!'

    
    @staticmethod
    def make_dirs(dirs):
        for name, dir in dirs.items():
            if name in ('book', 'raw_image'):
                pass
            else:
                if not os.path.isdir(dir):
                    try:
                        os.mkdir(dir, Environment.dir_mode)
                    except:
                        Util.bail('failed to create ' + dir )


    @staticmethod
    def clean_dirs(dirs):
        for name, dir in dirs.items():
            if name in ('book', 'raw_image', 'log'):
                pass
            else:
                if os.path.exists(dir):
                    try:
                        for f in os.listdir(dir):
                            os.remove(dir + '/' + f)
                    except:
                        Util.bail('failed to clean ' + dir);


    @staticmethod
    def set_logs(book, mode='w'):
        for log, key in book.logs.items():
            try:
                book.logger.logs[str(log)] = open(key['file'], mode, 1)
            except IOError:
                Util.bail("could not open " + str(key['file']) + ' in mode ' + mode)
                

    @staticmethod
    def make_scandata(book):
        root = etree.Element('book')
        book_data = etree.SubElement(root,'bookData')
        book_id = etree.SubElement(book_data,'bookId')
        book_id.text = str(book.identifier)
        leaf_count = etree.SubElement(book_data,'leafCount')
        leaf_count.text = str(book.page_count)

        page_data = etree.SubElement(root, 'pageData')
        for leaf in range(0, book.page_count):
            side  = 'LEFT' if leaf%2==0 else 'RIGHT'
            page = etree.SubElement(page_data, 'page')
            page.set('leafNum', str(leaf))
            handside = etree.SubElement(page, 'handSide')
            handside.text = str(side)
            page_type = etree.SubElement(page, 'pageType')
            page_type.text = 'Normal' if leaf in range(1, book.page_count-1) else 'Delete' 
            ataf = etree.SubElement(page, 'addToAccessFormats')
            ataf.text = 'true' if leaf in range(1, book.page_count-1) else 'false' 
            rotate_degree = etree.SubElement(page, 'rotateDegree')
            rotate_degree.text = '-90' if leaf%2==0 else '90' 
            skew_angle = etree.SubElement(page, 'skewAngle')
            skew_angle.text = '0.0'
            skew_conf = etree.SubElement(page, 'skewConf')
            skew_conf.text = '0.0'
            skew_active = etree.SubElement(page, 'skewActive')
            skew_active.text = 'false'
            orig_width = etree.SubElement(page, 'origWidth')
            orig_width.text = str(book.raw_image_dimensions[leaf][0])
            orig_height = etree.SubElement(page, 'origHeight')
            orig_height.text = str(book.raw_image_dimensions[leaf][1])
            crop_box = Crop.new_xml(page, 'cropBox')
            page_number = etree.SubElement(page, 'pageNumber')
        doc = etree.ElementTree(root)
        try:
            scandata = open(book.scandata_file,"w")
            doc.write(scandata, pretty_print=True)
            scandata.close()
        except IOError:
            Util.bail('failed to make scandata for ' + book.identifier)


class BookData:

    def __init__(self, dir, raw_data):
        self.root_dir = dir
        self.identifier = os.path.basename(self.root_dir)
        self.raw_image_dir = Environment.find_raw_dir(dir)
        self.page_count = raw_data['page_count']
        self.raw_images = raw_data['images']
        self.raw_image_dimensions = raw_data['dimensions']
        self.scandata_file = self.root_dir + '/' + self.identifier + '_scandata.xml'
        self.thumb_rotation_point = {'x': (self.raw_image_dimensions[0][1]/Environment.scale_factor)/2,
                                     'y': (self.raw_image_dimensions[0][0]/Environment.scale_factor)/2}
        self.dirs = {
            'book':         self.root_dir,
            'raw_image':    self.raw_image_dir,
            'log':          self.root_dir + '/' + self.identifier + '_logs',
            'thumb':        self.root_dir + '/' + self.identifier + '_thumbs',
            'corner':       self.root_dir + '/' + self.identifier + '_corners',
            'corner_thumb': self.root_dir + '/' + self.identifier + '_corners_thumbs',
            'cluster':      self.root_dir + '/' + self.identifier + '_clusters',
            'window':       self.root_dir + '/' + self.identifier + '_windows',
            'noise':        self.root_dir + '/' + self.identifier + '_noise',
            'pagination':   self.root_dir + '/' + self.identifier + '_pagination',
            'cropped':      self.root_dir + '/' + self.identifier + '_cropped',
            'ocr':          self.root_dir + '/' + self.identifier + '_ocr',
            'derived':      self.root_dir + '/' + self.identifier + '_derived'
            }

        self.logs = {
            'global': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_0_global_log.txt'
                },
            'processing': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_1_processing_log.txt'
                },
            'featureDetection': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_2_featureDetection_log.txt'
                },
            'pageDetection': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_3_pageDetection_log.txt'
                },
            'fastCornerDetection': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_4_fastCornerDetection_log.txt'
                },
            'clusterAnalysis': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_5_clusterAnalysis_log.txt'
                },
            'noiseAnalysis': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_6_noiseAnalysis_log.txt'
                },
            'pagination': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_7_pagination_log.txt'
                },
            'derivation': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_8_derivation_log.txt'
                },
            'ocr': {
                'file': str(self.dirs['log']) + '/' + self.identifier + '_9_ocr_log.txt'
                } 
            }



    def init_crops(self):
        xml_file = self.scandata_file if self.settings['respawn'] is False else None        
        self.pageCrop = Crop('pageCrop', 0, self.page_count, 
                             self.raw_image_dimensions[0][1], 
                             self.raw_image_dimensions[0][0], 
                             xml_file)
        self.cropBox = Crop('cropBox', 0, self.page_count,
                            self.raw_image_dimensions[0][1],
                            self.raw_image_dimensions[0][0],
                            xml_file)
        self.contentCrop = Crop('contentCrop', 0, self.page_count,
                                self.raw_image_dimensions[0][1],
                                self.raw_image_dimensions[0][0])
        self.crops = {'pageCrop': self.pageCrop,
                      'cropBox': self.cropBox,
                      'contentCrop': self.contentCrop}


    def import_crops(self):
        self.pageCrop = Crop('pageCrop', 0, self.page_count, 
                             self.raw_image_dimensions[0][1], 
                             self.raw_image_dimensions[0][0], 
                             self.scandata_file)
        self.cropBox = Crop('cropBox', 0, self.page_count,
                            self.raw_image_dimensions[0][1],
                            self.raw_image_dimensions[0][0],
                            self.scandata_file)
        self.contentCrop = Crop('contentCrop', 0, self.page_count,
                                self.raw_image_dimensions[0][1],
                                self.raw_image_dimensions[0][0],
                                self.scandata_file)
        self.crops = {'pageCrop': self.pageCrop,
                      'cropBox': self.cropBox,
                      'contentCrop': self.contentCrop}


class Logger:

    def __init__(self):
        self.logs = {}

    def message(self, message, log='global'):
        if message is None:
            return        
        timestamp = datetime.datetime.now()
        if type(log) == type(()):
            for l in log:
                self.logs[l].write(str(timestamp) + ':  '+ message + "\n")
        else:
            self.logs[log].write(str(timestamp) + ':  '+ message + "\n")
