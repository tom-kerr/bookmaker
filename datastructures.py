from operator import attrgetter, itemgetter
from copy import copy
from util import Util
from lxml import etree
import Image, ImageDraw
import math


class Crop:

    def __init__(self, name, start, end, 
                 image_width=None, image_height=None, 
                 xml_file=None):

        self.name = name
        self.start = start
        self.end = end

        self.image_height = image_height
        self.image_width = image_width
        
        self.meta ={}
        self.box = {}
        self.box_with_skew_padding = {}

        for leaf in range(start, end):
            self.box[leaf] = Box()
            self.box_with_skew_padding[leaf] = Box()
        
        self.classification = dict.fromkeys(range(start, end), 'Normal')                
        self.page_type = dict.fromkeys(range(start, end), 'Normal')        
        self.add_to_access_formats = dict.fromkeys(range(start, end), None)
        self.rotate_degree = dict.fromkeys(range(start, end), None)
        self.skew_angle = dict.fromkeys(range(start, end), 0.0)
        self.skew_conf = dict.fromkeys(range(start, end), None)
        self.skew_active = dict.fromkeys(range(start, end), None)

        if xml_file:
            self.xml_io(xml_file, 'import')


    def return_page_data_copy(self, leaf):
        page_data = {'box': copy(self.box[leaf]), 
                     'box_with_skew_padding': copy(self.box_with_skew_padding[leaf]),
                     'page_type': copy(self.page_type[leaf]),
                     'add_to_access_formats': copy(self.add_to_access_formats[leaf]),
                     'rotate_degree': copy(self.rotate_degree[leaf]),
                     'skew_angle': copy(self.skew_angle[leaf]),
                     'skew_conf': copy(self.skew_conf[leaf]),
                     'skew_active': copy(self.skew_active[leaf])}
        return page_data
                                                

    def get_box_metadata(self):
        for dimension in Box.dimensions:
            self.meta[dimension] = {'stats': None, 'stats_hist': None}
            p = []
            for leaf, box in self.box.items():
                if box.dimensions[dimension] is not None:
                    p.append(box.dimensions[dimension])
            if len(p) > 0:
                self.meta[dimension]['stats'] = Util.stats(p)
                self.meta[dimension]['stats_hist'] = Util.stats_hist(p, self.meta[dimension]['stats'])


    def xml_io(self, xml_file, mode):
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            xml = etree.parse(xml_file, parser)
        except IOError:
            Util.bail('could not open ' + xml_file)
        page_data = xml.find('pageData')
        pages = page_data.findall('page')
        for leaf, page in enumerate(pages): 
            if leaf in range(self.start, self.end):
                
                if mode is 'import':
                    xmlcrop = page.find(self.name)
                    if xmlcrop is None:
                        raise Exception('Missing essential item \'' + self.name  + '\' in scandata')
                    for dimension, value in self.box[leaf].dimensions.items():
                        p = xmlcrop.find(dimension)
                        if p is not None and p.text is not None:
                            self.box[leaf].set_dimension(dimension, int(p.text))
                        else:
                            self.box[leaf].set_dimension(dimension, None)
                    handside = page.find('handSide')
                    if handside is not None:
                        self.box[leaf].hand_side = handside.text
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
                        self.image_height = int(origwidth.text)
                        origheight = page.find('origHeight')
                    if origheight is not None:
                        self.box[leaf].orig_height = int(origheight.text)
                        self.image_width = int(origheight.text)

                elif mode is 'export':
                    xmlcrop = page.find(self.name)
                    if xmlcrop is None:
                        xmlcrop = Crop.new_xml(page, self.name)               
                    for dimension, value in self.box[leaf].dimensions.items():
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
            scandata = open(xml_file, "w")
            xml.write(scandata, pretty_print=True)
            scandata.close()


    @staticmethod
    def new_xml(root, name):
        crop_box = etree.SubElement(root, name)
        for dimension in Box.dimensions:
            etree.SubElement(crop_box, dimension)
        return crop_box


    def scale_box(self, leaf, scale_factor):
        scaled = Box()
        for dimension in Box.dimensions:
            if self.box[leaf].dimensions[dimension] is not None:
                value = int(self.box[leaf].dimensions[dimension]/scale_factor)
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
            self.box_with_skew_padding[leaf].set_dimension('r', self.image_width)
            self.box_with_skew_padding[leaf].set_dimension('b', self.image_height)

        if deskew:
            angle = 0 - self.skew_angle[leaf] * factor
        else:
            angle = self.skew_angle[leaf] * factor

        if angle > 0:
            XL = self.image_height - self.box[leaf].t
            YL = self.box[leaf].l 
        else:
            XL = self.box[leaf].t
            YL = self.image_width - self.box[leaf].l 

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
        


class Box:
    
    dimensions = ('x','y','w','h',
                  'l','t','r','b')
    
    def __init__(self):
        
        self.name = None

        self.size = None
               
        self.x = None
        self.y = None
        self.w = None
        self.h = None
        
        self.l = None
        self.t = None
        self.r = None
        self.b = None
    
        self.dimensions = {'x': None,
                           'y': None,
                           'w': None,
                           'h': None,
                           'l': None,
                           't': None,
                           'r': None,
                           'b': None}


    def set_dimension(self, dimension, value):
        if value is None:
            return
        if dimension in Box.dimensions:
            if dimension in ('l', 'x'):
                self.l = self.x = value
                self.dimensions['l'] = self.dimensions['x'] = value
                if dimension is 'l':
                    if self.r is not None and self.w is None:
                        self.w = self.r - self.l
                        self.dimensions['w'] = self.w
                    elif self.r is None and self.w is not None:
                        self.r = self.x + self.w
                        self.dimensions['r'] = self.r
                elif dimension is 'x':
                    if self.w is not None:
                        self.r = self.x + self.w
                        self.dimensions['r'] = self.r

            elif dimension in ('t', 'y'):
                self.t = self.y = value
                self.dimensions['t'] = self.dimensions['y'] = value
                if dimension is 't':
                    if self.b is not None and self.h is None:
                        self.h = self.b - self.t
                        self.dimensions['h'] = self.h
                    elif self.b is None and self.h is not None:
                        self.b = self.y + self.h
                        self.dimensions['b'] = self.b
                elif dimension is 'y':
                    if self.h is not None:
                        self.b = self.y + self.h
                        self.dimensions['b'] = self.b
                        
            elif dimension == 'r':
                self.r = self.dimensions['r'] = value
                if self.l is not None and self.w is None:
                    self.w = self.r - self.l
                    self.dimensions['w'] = self.w
                elif self.l is None and self.w is not None:
                    self.l = self.r - self.w
                    self.dimensions['l'] = self.l

            elif dimension == 'b':
                self.b = self.dimensions['b'] = value
                if self.t is not None and self.h is None:
                    self.h = self.b - self.t
                    self.dimensions['h'] = self.h
                elif self.t is None and self.h is not None:
                    self.t = self.b - self.h
                    self.dimensions['t'] = self.t

            elif dimension == 'w':
                self.w = self.dimensions['w'] = value
                if self.l is not None:
                    self.r = self.l + self.w
                    self.dimensions['r'] = self.r
                elif self.x is not None:
                    self.r = self.x + self.w
                    self.dimensions['r'] = self.r

                #if self.l is not None and self.r is None:
                #    self.r = self.l + self.w
                #    self.dimensions['r'] = self.r
                #elif self.l is None and self.r is not None:
                #    self.l = self.r - self.w
                #    self.dimensions['l'] = self.l

            elif dimension == 'h':
                self.h = self.dimensions['h'] = value
                if self.y is not None:
                    self.b = self.y + self.h
                    self.dimensions['b'] = self.b
                elif self.t is not None:
                    self.b = self.t + self.h
                    self.dimensions['b'] = self.b
#if self.t is not None and self.b is None:
                #    self.b = self.t + self.h
                #    self.dimensions['b'] = self.b
                #elif self.t is None and self.b is not None:
                #    self.t = self.b - self.h
                #    self.dimensions['t'] = self.t


    def update_dimension(self, dimension, value):
        if value is None:
            return
        if dimension is 'x':
            self.x = self.dimensions['x'] = self.l = self.dimensions['l'] = value
            self.r = self.dimensions['r'] = self.l + self.w
        elif dimension is 'y':
            self.y = self.dimensions['y'] = self.t = self.dimensions['t'] = value
            self.b = self.dimensions['b'] = self.t + self.h
        elif dimension is 'w':
            self.w = self.dimensions['w'] = value
            self.r = self.dimensions['r'] = self.l + self.w
        elif dimension is 'h':
            self.h = self.dimensions['h'] = value
            self.b = self.dimensions['b'] = self.t + self.h
        elif dimension is 'l':
            self.l = self.dimensions['l'] = self.x = self.dimensions['x'] = value
            self.w = self.dimensions['w'] = self.r - self.l
        elif dimension is 't':
            self.t = self.dimensions['t'] = self.y = self.dimensions['y'] = value
            self.h = self.dimensions['h'] = self.b - self.t
        elif dimension is 'r':
            self.r = self.dimensions['r'] = value
            self.w = self.dimensions['w'] = self.r - self.l
        elif dimension is 'b':
            self.b = self.dimensions['b'] = value
            self.h = self.dimensions['h'] = self.b - self.t



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
        if (self.x < 0 or self.x is None or
            self.y < 0 or self.y is None or
            self.w < 0 or self.w is None or
            self.h < 0 or self.h is None or
            self.l < 0 or self.l is None or
            self.t < 0 or self.t is None or
            self.r < 0 or self.r is None or
            self.b < 0 or self.b is None):
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

                                  
class Clusters:

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
            
