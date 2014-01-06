from operator import attrgetter, itemgetter
from copy import copy
import math

from lxml import etree
from PIL import Image, ImageDraw

from util import Util


class StructuralMetadata(object):

    def __init__(self):
        self.hand_side = {}
        self.active =                dict.fromkeys(range(0, self.page_count), False)
        self.pagination =            dict.fromkeys(range(0, self.page_count), None)
        self.classification =        dict.fromkeys(range(0, self.page_count), 'Normal')
        self.page_type =             dict.fromkeys(range(0, self.page_count), 'Normal')
        self.add_to_access_formats = dict.fromkeys(range(0, self.page_count), None)
        self.rotate_degree =         dict.fromkeys(range(0, self.page_count), None)
        self.skew_angle =            dict.fromkeys(range(0, self.page_count), 0.0)
        self.skew_conf =             dict.fromkeys(range(0, self.page_count), None)
        self.skew_active =           dict.fromkeys(range(0, self.page_count), None)


class Crop(StructuralMetadata):
    
    def __init__(self, name, page_count,
                 raw_image_dimensions, scandata=None,
                 import_scandata=False, scale_factor=1):
        self.name = name
        self.page_count = page_count
        self.scale_factor = scale_factor
        self.scandata = scandata
        self.meta ={}
        self.box = {}
        self.box_with_skew_padding = {}
        self.image_height = {}
        self.image_width = {}

        super(Crop, self).__init__()

        for leaf in range(0, self.page_count):
            self.box[leaf] = Box()
            self.box_with_skew_padding[leaf] = Box()

            self.image_width[leaf] = raw_image_dimensions[leaf]['height']/scale_factor
            self.image_height[leaf] = raw_image_dimensions[leaf]['width']/scale_factor
            if leaf%2==0:
                self.hand_side[leaf] = 'LEFT'
            else:
                self.hand_side[leaf] = 'RIGHT'

        if import_scandata:
            self.xml_io('import')
            self.update_pagination()

    def return_state(self, leaf):
        state = {'box': copy(self.box[leaf]),
                 'box_with_skew_padding': copy(self.box_with_skew_padding[leaf]),
                 'active': self.active[leaf],
                 'page_type': copy(self.page_type[leaf]),
                 'add_to_access_formats': copy(self.add_to_access_formats[leaf]),
                 'rotate_degree': copy(self.rotate_degree[leaf]),
                 'skew_angle': copy(self.skew_angle[leaf]),
                 'skew_conf': copy(self.skew_conf[leaf]),
                 'skew_active': copy(self.skew_active[leaf])}
        return state

    def get_box_metadata(self):
        for dimension in Box.dimensions:
            self.meta[dimension] = {'stats': None, 'stats_hist': None}
            p = []
            for leaf, box in self.box.items():
                if box.dim[dimension] is not None:
                    p.append(box.dim[dimension])
            if len(p) > 0:
                self.meta[dimension]['stats'] = Util.stats(p)
                self.meta[dimension]['stats_hist'] = Util.stats_hist(p, self.meta[dimension]['stats'])

    def set_all_active(self):
        page_data = self.scandata.tree.find('pageData')
        pages = page_data.findall('page')
        for leaf, page in enumerate(pages):
            if leaf in range(0, self.page_count):
                cropBox = page.find('cropBox')
                if cropBox is None:
                    raise LookupError('Missing essential item \'cropBox\' in scandata')
                for dimension, value in self.box[leaf].dim.items():
                    if value is not None:
                        cropBox.find(dimension).text = str(int(value))
                self.active[leaf] = True
        #self.write_to_scandata()

    def write_to_scandata(self):
        try:
            with open(self.scandata.filename, 'r+b') as f:
                self.scandata.tree.write(f, pretty_print=True)
        except Exception as e:
            Util.bail('failed to open scandata for writing')
        
    def xml_io(self, mode):
        page_data = self.scandata.tree.find('pageData')
        pages = page_data.findall('page')
        for leaf, page in enumerate(pages):
            if leaf in range(0, self.page_count):

                if mode is 'import':
                    xmlcrop = page.find(self.name)
                    if xmlcrop is None:
                        raise LookupError('Missing essential item \'' + self.name  + '\' in scandata')
                    
                    active = xmlcrop.get('active')
                    if active=='True':
                        self.active[leaf] = True
                    elif active=='False':
                        self.active[leaf] = False
    
                    for dimension, value in self.box[leaf].dim.items():
                        p = xmlcrop.find(dimension)
                        if p is not None and p.text is not None:
                            self.box[leaf].set_dimension(dimension, int(p.text))
                        else:
                            self.box[leaf].set_dimension(dimension, None)
                    pagetype = page.find('pageType')
                    if pagetype is not None:
                        self.page_type[leaf] = pagetype.text
                    ataf = page.find('addToAccessFormats')
                    if ataf is not None:
                        if ataf.text == 'true':
                            self.add_to_access_formats[leaf] = True
                        elif ataf.text == 'false':
                            self.add_to_access_formats[leaf] = False
                    rotatedegree = page.find('rotateDegree')
                    if rotatedegree is not None:
                        self.rotate_degree[leaf] = int(rotatedegree.text)
                    skewangle = page.find('skewAngle')
                    if skewangle is not None:
                        self.skew_angle[leaf] = float(skewangle.text)
                    skewconf = page.find('skewConf')
                    if skewconf is not None:
                        self.skew_conf[leaf]= float(skewconf.text)
                    skewactive = page.find('skewActive')
                    if skewactive is not None:
                        if skewactive.text == 'false':
                            self.skew_active[leaf] = False
                        elif skewactive.text == 'true':
                            self.skew_active[leaf] = True
                    origwidth = page.find('origWidth')
                    if origwidth is not None:
                        self.box[leaf].orig_width = int(origwidth.text)
                        self.image_height[leaf] = int(origwidth.text)/self.scale_factor
                        origheight = page.find('origHeight')
                    if origheight is not None:
                        self.box[leaf].orig_height = int(origheight.text)
                        self.image_width[leaf] = int(origheight.text)/self.scale_factor

                elif mode is 'export':
                    xmlcrop = page.find(self.name)
                    if xmlcrop is None:
                        xmlcrop = Crop.new_crop_element(page, self.name)
                    xmlcrop.set('active', str(self.active[leaf]))
                    for dimension, value in self.box[leaf].dim.items():
                        if value is not None:
                            xmlcrop.find(dimension).text = str(int(value))
                    pagetype = page.find('pageType')
                    if pagetype is not None:
                        if self.page_type[leaf] is not None:
                            pagetype.text = str(self.page_type[leaf])
                    ataf = page.find('addToAccessFormats')
                    if ataf is not None:
                        if self.add_to_access_formats[leaf] is not None:
                            ataf.text = str(self.add_to_access_formats[leaf])
                            ataf.text = ataf.text.lower()
                    rotatedegree = page.find('rotateDegree')
                    if rotatedegree is not None and self.rotate_degree[leaf] is not None:
                        rotatedegree.text = str(self.rotate_degree[leaf])
                    skewangle = page.find('skewAngle')
                    if skewangle is not None and self.skew_angle[leaf] is not None:
                        skewangle.text = str(self.skew_angle[leaf])
                    skewactive = page.find('skewActive')
                    if skewactive is not None and self.skew_active[leaf] is not None:
                        skewactive.text = str(self.skew_active[leaf])
                        skewactive.text = skewactive.text.lower()
                    skewconf = page.find('skewConf')
                    if skewconf is not None and self.skew_conf[leaf] is not None:
                        skewconf.text = str(self.skew_conf[leaf])
        if mode is 'export':
            self.write_to_scandata()

    def delete_assertion(self, leaf):
        bookdata = self.scandata.tree.find('bookData')
        page_num_data = bookdata.find('pageNumData')
        if page_num_data is None:
            return
        remove = None
        assertions = page_num_data.findall('assertion')
        if assertions:
            for num, element in enumerate(assertions):
                entry = element.find('leafNum')
                if entry.text == str(leaf):
                    remove = num
                    break
        if remove is not None:
            #self.pagination[leaf] = None
            assertions[remove].getparent().remove(assertions[remove])
            self.write_to_scandata()
            self.update_pagination()

    def assert_page_number(self, leaf, number):
        bookdata = self.scandata.tree.find('bookData')
        page_num_data = bookdata.find('pageNumData')
        if page_num_data is None:
            page_num_data = etree.SubElement(bookdata, 'pageNumData')
        assertions = page_num_data.findall('assertion')
        for element in assertions:
            entry = element.find('leafNum')
            if entry.text == str(leaf):
                pagenum = element.find('pageNum')
                pagenum.text = str(number)
                self.write_to_scandata()
                self.update_pagination()
                return
        insert_point = None
        for num, element in enumerate(assertions):
            entry = element.find('leafNum')
            if leaf < int(entry.text):
                insert_point = num
                break
        if insert_point is not None:
            assertion = etree.Element('assertion')
            page_num_data.insert(num, assertion)
        else:
            assertion = etree.SubElement(page_num_data, 'assertion')
        leafnum = etree.SubElement(assertion, 'leafNum')
        leafnum.text = str(leaf)
        pagenum = etree.SubElement(assertion, 'pageNum')
        pagenum.text = str(number)
        self.write_to_scandata()
        self.update_pagination()

    def update_pagination(self):
        bookdata = self.scandata.tree.find('bookData')
        page_num_data = bookdata.find('pageNumData')
        if page_num_data is None:
            return
        assertions = page_num_data.findall('assertion')
        num_asserts = len(assertions)
        ranges = {}
        for num in range(0, num_asserts):
            start_leaf = int(assertions[num].find('leafNum').text)
            start_pagenum = int(assertions[num].find('pageNum').text)
            next_num = num + 1
            if num==0:
                for leaf in range(0, start_leaf):
                    self.pagination[leaf]=None
            try:
                end_leaf = int(assertions[next_num].find('leafNum').text)
                end_pagenum = int(assertions[next_num].find('pageNum').text)
            except:
                end_leaf = self.page_count
                end_pagenum = start_pagenum + (end_leaf - start_leaf)
            ranges[num] = (start_leaf, end_leaf)
            for num, leaf in enumerate(range(start_leaf, end_leaf+1)):
                if leaf == start_leaf:
                    self.pagination[leaf] = str(start_pagenum) + '!'
                elif leaf == end_leaf:
                    self.pagination[leaf] = str(end_pagenum) + '!'
                else:
                    if (end_leaf - start_leaf) == (end_pagenum - start_pagenum):
                        self.pagination[leaf] = str(start_pagenum + num)
                    else:
                        self.pagination[leaf] = str(start_pagenum + num) + '?'
                #print leaf, self.pagination[leaf]

    @staticmethod
    def new_crop_element(root, name):
        crop_box = etree.SubElement(root, name)
        crop_box.set('active', 'False')
        for dimension in Box.dimensions:
            etree.SubElement(crop_box, dimension)
        return crop_box

    def scale_box(self, leaf, scale_factor):
        scaled = Box()
        for dimension in Box.dimensions:
            if self.box[leaf].dim[dimension] is not None:
                value = int(self.box[leaf].dim[dimension]/scale_factor)
                scaled.set_dimension(dimension, value)
        #scaled.skew_angle = self.skew_angle[leaf]
        return scaled

    def skew(self, mx, my, leaf, factor=1, deskew=False, mode='contract'):
        if (self.classification[leaf] is 'blank' or
            not self.box[leaf].is_valid()):
            return

        if deskew:
            angle = 0 - self.skew_angle[leaf] * factor
        else:
            angle = self.skew_angle[leaf] * factor

        new_lt = Crop.calculate_skew(self.box[leaf].l, self.box[leaf].t,
                                     mx, my, angle)
        new_rt = Crop.calculate_skew(self.box[leaf].r, self.box[leaf].t,
                                     mx, my, angle)
        new_lb = Crop.calculate_skew(self.box[leaf].l, self.box[leaf].b,
                                     mx, my, angle)
        new_rb = Crop.calculate_skew(self.box[leaf].r, self.box[leaf].b,
                                     mx, my, angle)

        if mode == 'contract':
            if angle > 0:
                self.box[leaf].update_dimension('l', int(new_lt['x']))
                self.box[leaf].update_dimension('t', int(new_rt['y']))
                self.box[leaf].update_dimension('r', int(new_rb['x']))
                self.box[leaf].update_dimension('b', int(new_lb['y']))
            elif angle < 0:
                self.box[leaf].update_dimension('l', int(new_lb['x']))
                self.box[leaf].update_dimension('t', int(new_lt['y']))
                self.box[leaf].update_dimension('r', int(new_rt['x']))
                self.box[leaf].update_dimension('b', int(new_rb['y']))
        if mode == 'expand':
            if angle > 0:
                self.box[leaf].update_dimension('l', int(new_lb['x']))
                self.box[leaf].update_dimension('t', int(new_rt['y']))
                self.box[leaf].update_dimension('r', int(new_rb['x']))
                self.box[leaf].update_dimension('b', int(new_rb['y']))
            elif angle < 0:
                self.box[leaf].update_dimension('l', int(new_lb['x']))
                self.box[leaf].update_dimension('t', int(new_rt['y']))
                self.box[leaf].update_dimension('r', int(new_rb['x']))
                self.box[leaf].update_dimension('b', int(new_lb['y']))

    def calculate_box_with_skew_padding(self, leaf, factor=1, deskew=False):
        self.box_with_skew_padding[leaf] = Box()
        #self.padding[leaf] = {}
        if not self.box[leaf].is_valid():
            self.box_with_skew_padding[leaf].set_dimension('l', 0)
            self.box_with_skew_padding[leaf].set_dimension('t', 0)
            self.box_with_skew_padding[leaf].set_dimension('r', self.image_width[leaf])
            self.box_with_skew_padding[leaf].set_dimension('b', self.image_height[leaf])

        if deskew:
            angle = 0 - self.skew_angle[leaf] * factor
        else:
            angle = self.skew_angle[leaf] * factor

        if angle > 0:
            XL = self.image_height[leaf] - self.box[leaf].t
            YL = self.box[leaf].l
        else:
            XL = self.box[leaf].t
            YL = self.image_width[leaf] - self.box[leaf].l

        padding_x = abs(((math.sin(math.radians(angle)) * XL)))
        padding_y = abs(((math.sin(math.radians(angle)) * YL)))
        #print leaf
        #print padding_x, padding_y
        #self.padding[leaf]['x'] = padding_x
        #self.padding[leaf]['y'] = padding_y

        self.box_with_skew_padding[leaf].set_dimension('l', self.box[leaf].l + padding_x)
        self.box_with_skew_padding[leaf].set_dimension('t', self.box[leaf].t + padding_y)
        self.box_with_skew_padding[leaf].set_dimension('r', self.box[leaf].r + padding_x)
        self.box_with_skew_padding[leaf].set_dimension('b', self.box[leaf].b + padding_y)

    def apply_box_with_skew_padding(self, leaf):
        self.box[leaf].set_dimension('l', self.box_with_skew_padding[leaf].l)
        self.box[leaf].set_dimension('t', self.box_with_skew_padding[leaf].t)
        self.box[leaf].set_dimension('r', self.box_with_skew_padding[leaf].r)
        self.box[leaf].set_dimension('b', self.box_with_skew_padding[leaf].b)

    def skew_translation(self, mx, my, leaf, factor=1, deskew=False):
        if (self.classification[leaf] is 'blank' or
            not self.box[leaf].is_valid()):
            return

        if deskew:
            angle = 0 - self.skew_angle[leaf] * factor
        else:
            angle = self.skew_angle[leaf] * factor

        new_lt = Crop.calculate_skew(self.box[leaf].l,
                                     self.box[leaf].t,
                                     mx, my, angle)
        self.box[leaf].update_dimension('x', int(new_lt['x']))
        self.box[leaf].update_dimension('y', int(new_lt['y']))

    @staticmethod
    def calculate_skew(px, py, mx, my, angle):
        x = ( ((px - mx) * math.cos(math.radians(angle)) ) -
              ((py - my) * math.sin(math.radians(angle)) ) + mx)
        y = ( ((px - mx) * math.sin(math.radians(angle)) ) +
              ((py - my) * math.cos(math.radians(angle)) ) + my)
        return {'x':x ,'y':y}


class ImageLayer(object):

    def draw(self, canvas, outline="blue", fill=None, annotate=True):
        img = Image.open(canvas)
        draw = ImageDraw.Draw(img)
        draw.rectangle([self.l, self.t,
                        self.r, self.b],
                       outline = str(outline), fill = fill )
        if annotate:
            if self.name is not None:
                draw.text([self.l-10, self.t-10],
                          str(self.name),
                          fill = 'black')
        del draw
        img.save(canvas)

    @staticmethod
    def new_image(filename, height, width, color):
        img = Image.new('RGB', (height, width), str(color))
        img.save(filename)


class Box(ImageLayer):

    dimensions = ('x','y','w','h',
                  'l','t','r','b')

    def __init__(self):
        self.name = None
        self.size = None
        for dim in Box.dimensions:
            setattr(self, dim, None)         
        self.dim = {d: None for d in Box.dimensions}

    def set_dimension(self, dim, value):
        if value is None:
            return
        if dim in Box.dimensions:
            if dim in ('l', 'x'):
                self.l = self.x = value
                self.dim['l'] = self.dim['x'] = value
                if dim is 'l':
                    if self.r is not None and self.w is None:
                        self.w = self.r - self.l
                        self.dim['w'] = self.w
                    elif self.r is None and self.w is not None:
                        self.r = self.x + self.w
                        self.dim['r'] = self.r
                elif dim is 'x':
                    if self.w is not None:
                        self.r = self.x + self.w
                        self.dim['r'] = self.r

            elif dim in ('t', 'y'):
                self.t = self.y = value
                self.dim['t'] = self.dim['y'] = value
                if dim is 't':
                    if self.b is not None and self.h is None:
                        self.h = self.b - self.t
                        self.dim['h'] = self.h
                    elif self.b is None and self.h is not None:
                        self.b = self.y + self.h
                        self.dim['b'] = self.b
                elif dim is 'y':
                    if self.h is not None:
                        self.b = self.y + self.h
                        self.dim['b'] = self.b

            elif dim == 'r':
                self.r = self.dim['r'] = value
                if self.l is not None and self.w is None:
                    self.w = self.r - self.l
                    self.dim['w'] = self.w
                elif self.l is None and self.w is not None:
                    self.l = self.r - self.w
                    self.dim['l'] = self.l

            elif dim == 'b':
                self.b = self.dim['b'] = value
                if self.t is not None and self.h is None:
                    self.h = self.b - self.t
                    self.dim['h'] = self.h
                elif self.t is None and self.h is not None:
                    self.t = self.b - self.h
                    self.dim['t'] = self.t

            elif dim == 'w':
                self.w = self.dim['w'] = value
                if self.l is not None:
                    self.r = self.l + self.w
                    self.dim['r'] = self.r
                elif self.x is not None:
                    self.r = self.x + self.w
                    self.dim['r'] = self.r

                #if self.l is not None and self.r is None:
                #    self.r = self.l + self.w
                #    self.dim['r'] = self.r
                #elif self.l is None and self.r is not None:
                #    self.l = self.r - self.w
                #    self.dim['l'] = self.l

            elif dim == 'h':
                self.h = self.dim['h'] = value
                if self.y is not None:
                    self.b = self.y + self.h
                    self.dim['b'] = self.b
                elif self.t is not None:
                    self.b = self.t + self.h
                    self.dim['b'] = self.b
#if self.t is not None and self.b is None:
                #    self.b = self.t + self.h
                #    self.dim['b'] = self.b
                #elif self.t is None and self.b is not None:
                #    self.t = self.b - self.h
                #    self.dim['t'] = self.t

    def update_dimension(self, dim, value):
        if value is None:
            return
        if dim is 'x':
            self.x = self.dim['x'] = self.l = self.dim['l'] = value
            self.r = self.dim['r'] = self.l + self.w
        elif dim is 'y':
            self.y = self.dim['y'] = self.t = self.dim['t'] = value
            self.b = self.dim['b'] = self.t + self.h
        elif dim is 'w':
            self.w = self.dim['w'] = value
            self.r = self.dim['r'] = self.l + self.w
        elif dim is 'h':
            self.h = self.dim['h'] = value
            self.b = self.dim['b'] = self.t + self.h
        elif dim is 'l':
            self.l = self.dim['l'] = self.x = self.dim['x'] = value
            self.w = self.dim['w'] = self.r - self.l
        elif dim is 't':
            self.t = self.dim['t'] = self.y = self.dim['y'] = value
            self.h = self.dim['h'] = self.b - self.t
        elif dim is 'r':
            self.r = self.dim['r'] = value
            self.w = self.dim['w'] = self.r - self.l
        elif dim is 'b':
            self.b = self.dim['b'] = value
            self.h = self.dim['h'] = self.b - self.t

    def rotate(self, rot_dir, image_width, image_height):
        l = x = self.l
        t = y = self.t
        r = self.r
        b = self.b
        w = self.w
        h = self.h

        if rot_dir == -90:
            self.update_dimension('l', y)
            self.update_dimension('t', abs(r - image_width))
            self.update_dimension('r', b)
            self.update_dimension('b', l)
            self.update_dimension('w', h)
            self.update_dimension('h', w)
        if rot_dir == 90:
            self.update_dimension('l', abs(b - image_height))
            self.update_dimension('t', l)
            self.update_dimension('r', t)
            self.update_dimension('b', r)
            self.update_dimension('w', h)
            self.update_dimension('h', w)

    def resize(self, amount):
        self.set_dimension('l', self.l - amount)
        self.set_dimension('t', self.t - amount)
        self.set_dimension('r', self.r + amount)
        self.set_dimension('b', self.b + amount)

    def is_valid(self):
        for dim in Box.dimensions:
            attr = getattr(self, dim)
            if attr is None or attr < 0:
                return False
        return True

    def is_contained_by(self, container, padding = -5):
        if (self.l < container.l + padding or
            self.t < container.t + padding or
            self.r > container.r - padding or
            self.b > container.b - padding):
            return False
        return True

    def contains_point(self, x, y):
        if ((x >= self.l and x <= self.r) and
            (y >= self.t and y <= self.b)):
            return True
        else:
            return False

    def touches(self, other_box):
        if (((self.l >= other_box.l and
              self.l <= other_box.r) and
             ((self.t >= other_box.t and
               self.t <= other_box.b) or
              (self.t <= other_box.t and
               self.b >= other_box.t))) or
            ((self.l <= other_box.l and
              self.r >= other_box.l) and
             ((self.t >= other_box.t and
               self.t <= other_box.b) or
              (self.t <= other_box.t and
               self.b >= other_box.t))) ):
            return True
        else:
            return False

    def detect_orientation(self, container):
        if self.t < container.b - container.h/2:
            if self.b > container.b - container.h/2:
                if (container.b - container.h/2) - self.t > self.b -(container.b - container.h/2):
                    return 'head'
                else:
                    return 'floor'
        return 'head'

    def center_within(self, container):
        x = (container.x +
             (container.w - self.w)/2)
        y = (container.y +
             (container.h - self.h)/2)
        if self.x is None:
            self.set_dimension('x', x)
        else:
            self.update_dimension('x', x)
        if self.y is None:
            self.set_dimension('y', y)
        else:
            self.update_dimension('y', y)

    def position_around(self, anchor, head=None, floor=None):
        x = anchor.x - (self.w - anchor.w)/2
        if head:
            y = anchor.y - head
        elif floor:
            y = anchor.b + floor - self.h
        else:
            y = anchor.y - (self.h - anchor.h)/2
        if self.x is None:
            self.set_dimension('x', x)
        else:
            self.update_dimension('x', x)
        if self.y is None:
            self.set_dimension('y', y)
        else:
            self.update_dimension('y', y)

    def fit_within(self, container):
        if self.x < container.x:
            delta = abs(self.x - container.x)
            space = container.r - self.r
            if space > delta:
                self.update_dimension('x', self.x + delta)
            else:
                self.update_dimension('x', self.x + delta)
                self.update_dimension('w', self.w - abs(delta - space))
        if self.y < container.y:
            delta = abs(self.y - container.y)
            space = container.b - self.b
            if space > delta:
                self.update_dimension('y', self.y + delta)
            else:
                self.update_dimension('y', self.y + delta)
                self.update_dimension('h', self.h - abs(delta - space))
        if self.r > container.r:
            delta = abs(self.r - container.r)
            space = self.x - container.x
            if space > delta:
                self.update_dimension('x', self.x - delta)
            else:
                self.update_dimension('x', self.x - delta)
                self.update_dimension('w', self.w - abs(delta - space))
        if self.b > container.b:
            delta = abs(self.b - container.b)
            space = self.y - container.y
            if space > delta:
                self.update_dimension('y', self.y - delta)
            else:
                self.update_dimension('y', self.y - delta)
                self.update_dimension('h', self.h - abs(delta - space))


class Clusters(object):

    def __init__(self, leaf):
        self.leaf = leaf
        self.cluster = {}
        self.position = 0

    def new_cluster(self, position=None):
        if position is None:
            position = self.position
        self.cluster[position] = Box()
        self.cluster[position].name = str(position)
        self.position = len(self.cluster)

    def search(self, container, size_limit=None):
        results = {}
        for num, cluster in self.cluster.items():
            if cluster is not None:
                if ((cluster.is_contained_by(container, padding=0) or
                     cluster.touches(container)) and
                    (cluster.size < size_limit or size_limit is None)):
                    results[num] = cluster
        if len(results) < 1:
            return False
        else:
            return results

    def find_by_orientation(self, container):
        self.top_left = None
        self.top_right = None
        self.top_center = None
        self.bottom_left = None
        self.bottom_right = None
        self.bottom_center = None

        L = container.l + (0.1*container.w)
        R = container.r - (0.1*container.w)
        T = container.t + (0.1*container.h)
        B = container.b - (0.1*container.h)

        tmp = []
        for num, cluster in self.cluster.items():
            if cluster is not None:
                if (((cluster.x < L or cluster.x > R) or
                    (cluster.y < T or cluster.y > B)) and
                    (cluster.size < 100)):
                    tmp.append( (num, cluster.x, cluster.y) )

        x = sorted(tmp, key=itemgetter(1))
        y = sorted(tmp, key=itemgetter(2))

        x_inverse = sorted(tmp, key=itemgetter(1), reverse=True)
        y_inverse = sorted(tmp, key=itemgetter(2), reverse=True)

        orientations = ['top_left','top_right','top_center',
                        'bottom_left','bottom_right','bottom_center']

        for o, orientation in enumerate(orientations):
            ranks = {}
            if orientation is 'top_left':
                for key, cluster in enumerate(x):
                    ranks[cluster[0]] = key
                for key, cluster in enumerate(y):
                    ranks[cluster[0]] += math.pow(key, key)
                ranks = sorted(ranks.items(), key=itemgetter(1))
                self.top_left = ranks[0][0] if len(ranks) > 0 else None

            elif orientation is 'top_right':
                for key, cluster in enumerate(x_inverse):
                    ranks[cluster[0]] = key
                for key, cluster in enumerate(y):
                    ranks[cluster[0]] += math.pow(key, key)
                ranks = sorted(ranks.items(), key=itemgetter(1))
                self.top_right = ranks[0][0] if len(ranks) > 0 else None

            elif orientation is 'bottom_left':
                for key, cluster in enumerate(x):
                    ranks[cluster[0]] = key
                for key, cluster in enumerate(y_inverse):
                    ranks[cluster[0]] += math.pow(key, key)
                ranks = sorted(ranks.items(), key=itemgetter(1))
                self.bottom_left = ranks[0][0] if len(ranks) > 0 else None

            elif orientation is 'bottom_right':
                for key, cluster in enumerate(x_inverse):
                    ranks[cluster[0]] = key
                for key, cluster in enumerate(y_inverse):
                    ranks[cluster[0]] += math.pow(key, key)
                ranks = sorted(ranks.items(), key=itemgetter(1))
                self.bottom_right = ranks[0][0] if len(ranks) > 0 else None
                """
                if len(ranks) > 4:
                    top_ranks = ranks[1:3]
                    best = self.cluster[ranks[0][0]].x
                    self.bottom_right = ranks[0][0]
                    for r, rank in enumerate(top_ranks):
                        if self.cluster[rank[0]].x > best:
                            self.bottom_right = rank[0]
                            """
            elif (orientation is 'top_center' and
                  self.top_left is not None and
                  self.top_center is not None):

                for key, cluster in enumerate(x):
                    ranks[cluster[0]] = key
                for key, cluster in enumerate(y):
                    ranks[cluster[0]] += math.pow(key, key)
                ranks = sorted(ranks.items(), key=itemgetter(1))
                i = 0
                while(True):
                    L = self.cluster[self.top_left].l
                    R = self.cluster[self.top_right].r
                    if (self.cluster[ranks[i][0]].l > L and
                        self.cluster[ranks[i][0]].l < R):
                        self.top_center = ranks[i][0]
                        break
                    else:
                        i+=1
                    if i >= len(ranks):
                        self.top_center = None
                        break

            elif (orientation is 'bottom_center' and
                  self.bottom_left is not None and
                  self.bottom_center is not None):

                for key, cluster in enumerate(x):
                    ranks[cluster[0]] = key
                for key, cluster in enumerate(y_inverse):
                    ranks[cluster[0]] += math.pow(key, key)
                ranks = sorted(ranks.items(), key=itemgetter(1))
                i = 0
                while(True):
                    L = self.cluster[self.bottom_left].l
                    R = self.cluster[self.bottom_right].r
                    if (self.cluster[ranks[i][0]].l > L and
                        self.cluster[ranks[i][0]].l < R):
                        self.bottom_center = ranks[i][0]
                        break
                    else:
                        i+=1
                    if i >= len(ranks):
                        self.bottom_center = None
                        break

        if self.top_left is not None:
            self.cluster[self.top_left].draw(self.thumb, outline='pink', fill='pink')
        if self.top_right is not None:
            self.cluster[self.top_right].draw(self.thumb, outline='red', fill='red')
        if self.top_center is not None:
            self.cluster[self.top_center].draw(self.thumb, outline='cyan', fill='cyan')

        if self.bottom_left is not None:
            self.cluster[self.bottom_left].draw(self.thumb, outline='pink', fill='pink')
        if self.bottom_right is not None:
            self.cluster[self.bottom_right].draw(self.thumb, outline='red', fill='red')
        if self.bottom_center is not None:
            self.cluster[self.bottom_center].draw(self.thumb, outline='cyan', fill='cyan')

        return {'top_left':self.top_left,
                'top_center':self.top_center,
                'top_right':self.top_right,
                'bottom_left':self.bottom_left,
                'bottom_center':self.bottom_center,
                'bottom_right':self.bottom_right}

