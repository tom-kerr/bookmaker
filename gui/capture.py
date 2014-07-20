import os

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GObject

from util import Util
from gui.common import CommonActions as CA
from components.raw2thumb import Raw2Thumb


class CaptureGui(object):
    """ Image Capture Interface
    """
    def __init__(self, window, book, ProcessHandler, ImageCapture):
        self.window = window
        self.book = book
        self.ProcessHandler = ProcessHandler
        self.ImageCapture = ImageCapture
        self.Raw2Thumb = Raw2Thumb(self.book)
        self.init_main_box()
        self.init_capture_box()
        self.init_info()
        self.init_device_controls()
        self.init_previewer()
        self.init_nav_controls()
        self.init_capture_controls()
        self.window.show()
        
    def init_main_box(self):
        kwargs = {'visible': True,
                  'orientation': Gtk.Orientation.HORIZONTAL}
        self.main_box = Gtk.Box(**kwargs)
        self.main_box.set_size_request(width=int(self.window.width),
                                       height=int(self.window.height))
        self.window.add(self.main_box)
        self.main_box.show()

    def init_capture_box(self):
        kwargs = {'visible': True,
                  'orientation': Gtk.Orientation.VERTICAL}
        self.capture_box = Gtk.Box(**kwargs)
        self.capture_box.set_size_request(width=int(self.window.width*(2/3)),
                                          height = int(self.window.height))
        self.main_box.add(self.capture_box)
        self.capture_box.show()

    def init_previewer(self):
        kwargs = {'visible': True,
                  'orientation': Gtk.Orientation.HORIZONTAL}
        self.preview = Gtk.Box(**kwargs)
        self.preview_images = [None, None]
        self.draw_preview()
        self.preview.set_halign(Gtk.Align.CENTER)
        self.preview.set_valign(Gtk.Align.CENTER)
        self.capture_box.pack_start(self.preview, True, False, 0)

    def draw_preview(self):
        if self.ImageCapture.capture_style == 'Single':
            queue = [self.left_leaf,]
        elif self.ImageCapture.capture_style == 'Dual':
            queue = [self.left_leaf, self.right_leaf]
        for index, leaf in enumerate(queue):
            leafnum = "%04d" % leaf
            image_file = self.book.dirs['scaled'] + '/' + \
                self.book.identifier + '_scaled_' + leafnum + '.jpg'
            if not os.path.exists(image_file):
                self.make_scaled_image(leaf, image_file)
            img = self.get_scaled_image(image_file)
            self.preview_images[index] = img
            self.preview.add(img)
        self.preview.show_all()

    def update_preview(self):
        for img in self.preview_images:
            if img is not None:
                self.preview.remove(img)
        self.draw_preview()

    def make_scaled_image(self, leaf, image_file):        
        if self.ImageCapture.capture_style == 'Single':
            leaf = int(leaf/2 -2)
            rot_dir = 0
        elif self.ImageCapture.capture_style == 'Dual':
            if leaf%2==0:
                rot_dir = -1
            else:
                rot_dir = 1
        raw = self.book.raw_images[leaf]
        self.Raw2Thumb.run(l, in_file=raw, 
                           out_file=image_file, 
                           rot_dir=rot_dir)
        
    def get_scaled_image(self, image_file):        
        pb = GdkPixbuf.Pixbuf.new_from_file(image_file)        
        w, h = pb.get_width(), pb.get_height()
        w_scale_factor = float(w) / float(2*self.window.width/3)
        h_scale_factor = float(h) / float(2*self.window.height/3)
        scale_factor = w_scale_factor if w_scale_factor > h_scale_factor else h_scale_factor
        sw, sh = int(w/scale_factor), int(h/scale_factor),
        pb_scaled = pb.scale_simple(sw, sh, GdkPixbuf.InterpType.BILINEAR)
        return Gtk.Image.new_from_pixbuf(pb_scaled)
    
    def init_nav_controls(self):
        kwargs = {'visible': True,
                  'orientation': Gtk.Orientation.HORIZONTAL}
        self.nav_controls = Gtk.Box(**kwargs)
        self.nav_controls.set_size_request(100, 25)
        kwargs = {'visible': True,
                  'label': 'Prev Spread'}
        self.prev = Gtk.Button(**kwargs)
        self.prev.connect('clicked', self.nav_prev_spread)
        kwargs = {'visible': True,
                  'label': 'Next Spread'}
        self.next = Gtk.Button(**kwargs)
        self.next.connect('clicked', self.nav_next_spread)
        self.nav_controls.add(self.prev)
        self.nav_controls.add(self.next)        
        self.nav_controls.set_halign(Gtk.Align.CENTER)
        self.nav_controls.set_valign(Gtk.Align.END)
        self.capture_box.pack_start(self.nav_controls, True, False, 0) 

    def nav_prev_spread(self, widget=None):
        left = self.left_leaf
        right = self.right_leaf
        if left - 2 >= 0:
            for img in self.preview_images:
                if img is not None:
                    self.preview.remove(img)
            self.left_leaf -= 2
            self.right_leaf -= 2
            self.draw_preview()
            self.update_info()
            self.update_capture_controls()

    def nav_next_spread(self, widget=None):
        left = self.left_leaf
        right = self.right_leaf
        if self.ImageCapture.capture_style == 'Single':
            limit = self.book.page_count*2-1
        elif self.ImageCapture.capture_style == 'Dual':
            limit = self.book.page_count-1
        if right + 2 <= limit:
            for img in self.preview_images:
                if img is not None:
                    self.preview.remove(img)
            self.left_leaf += 2
            self.right_leaf += 2
            self.draw_preview()
            self.update_info()
            self.update_capture_controls()

    def init_capture_controls(self):
        kwargs = {'visible': True,
                  'orientation': Gtk.Orientation.HORIZONTAL}
        self.capture_controls = Gtk.Box(**kwargs)
        self.capture_controls.set_size_request(-1, 75)
        kwargs = {'visible': True,
                  'label': 'Shoot Spread'}
        self.shoot = Gtk.Button(**kwargs)
        self.shoot.set_size_request(200, -1)
        self.shoot.connect('clicked', self.handle_shoot)
        kwargs = {'visible': False,
                  'label': 'Insert Spread'}
        self.insert = Gtk.Button(**kwargs)
        self.insert.set_size_request(200, -1)
        self.insert.connect('clicked', self.handle_insert)
        kwargs = {'visible': True,
                  'label': 'Re-Shoot Spread'}
        self.reshoot = Gtk.Button(**kwargs)
        self.reshoot.set_size_request(200, -1)
        self.reshoot.connect('clicked', self.handle_reshoot)
        self.capture_controls.add(self.shoot)
        self.capture_controls.add(self.insert)
        self.capture_controls.add(self.reshoot)        
        self.capture_controls.set_halign(Gtk.Align.CENTER)
        self.capture_controls.set_valign(Gtk.Align.END)
        self.capture_box.pack_start(self.capture_controls, True, False, 0) 

    def update_capture_controls(self):
        if self.ImageCapture.capture_style == 'Single':
            limit = self.book.page_count*2 - 2
        elif self.ImageCapture.capture_style == 'Dual':
            limit = self.book.page_count
        if self.left_leaf < limit:
            self.shoot.hide()
            self.insert.show()
        else:
            self.shoot.show()
            self.insert.hide()

    def init_device_controls(self):
        kwargs = {'visible': True,
                  'orientation': Gtk.Orientation.VERTICAL}
        self.device_controls = Gtk.Box(**kwargs)
        self.device_controls.set_halign(Gtk.Align.CENTER)
        self.device_controls.set_valign(Gtk.Align.CENTER)
        if not self.ImageCapture.are_devices():
            none_label = Gtk.Label('No Devices Detected.')
            self.device_controls.add(none_label)
        else:
            self.device_models = {}
            self.device_treeviews = {}
            self.device_entries = {}
            self.device_toggles = {'center': [],
                                   'left': [],
                                   'right': []}
            self.build_device_controls()
        kwargs = {'label': 'Update Devices'}
        self.update_dev_button = Gtk.Button(**kwargs)
        self.update_dev_button.connect('clicked', self.update_devices)
        self.device_controls.pack_end(self.update_dev_button, True, False, 0)
        self.main_box.pack_end(self.device_controls, True, False, 0)
        self.device_controls.show_all()

    def build_device_controls(self):        
        if self.ImageCapture.capture_style == 'Single':
            l = [str, bool]
        elif self.ImageCapture.capture_style == 'Dual':
            l = [str, bool, bool]
        
        for device, info in self.ImageCapture.Gphoto2.devices.items():
            self.device_models[device] = Gtk.ListStore(*l)
            self.device_treeviews[device] = Gtk.TreeView(self.device_models[device])
            self.device_treeviews[device].set_size_request(-1, 100)
            self.device_controls.pack_start(self.device_treeviews[device], False, False, 0)        

            entry = []
            col = Gtk.TreeViewColumn(device)
            cell = Gtk.CellRendererText()
            col.pack_start(cell, False)
            col.set_attributes(cell, text=0)
            self.device_treeviews[device].append_column(col)
            
            entry_string = ''
            for k, v in info.items():
                if k == 'side': continue
                entry_string += k + ': ' + v + ' \n'
            entry.append(entry_string)
            
            if self.ImageCapture.capture_style == 'Single':
                col = Gtk.TreeViewColumn('Center')
                kwargs = {'activatable': True,
                          'radio': True}
                crt = Gtk.CellRendererToggle(**kwargs)
                setattr(crt, 'side', 'center')
                setattr(crt, 'device', device)
                crt.connect('toggled', self.toggle_device)
                self.device_toggles['center'].append(crt)
                col.pack_start(crt, False)
                self.device_treeviews[device].append_column(col)
                if info['Serial Number'] in self.book.settings['devices'].keys():
                    side = self.book.settings['devices'][info['Serial Number']]
                    if side == 'center':
                        crt.set_active(True)
                        self.ImageCapture.Gphoto2.devices[device]['side'] = side
                else:
                    self.ImageCapture.Gphoto2.devices[device]['side'] = None
                kwargs = {'visible': True}
                tb = Gtk.ToggleButton(**kwargs)
                entry.append(tb)
                 
            elif self.ImageCapture.capture_style == 'Dual':
                col = Gtk.TreeViewColumn('Left')
                kwargs = {'activatable': True,
                          'radio': True}
                left_crt = Gtk.CellRendererToggle(**kwargs)
                setattr(left_crt, 'side', 'left')
                setattr(left_crt, 'device', device)
                left_crt.connect('toggled', self.toggle_device)
                self.device_toggles['left'].append(left_crt)
                col.pack_start(left_crt, False)
                self.device_treeviews[device].append_column(col)
                
                col = Gtk.TreeViewColumn('Right')
                kwargs = {'activatable': True,
                          'radio': True}
                right_crt = Gtk.CellRendererToggle(**kwargs)
                setattr(right_crt, 'side', 'right')
                setattr(right_crt, 'device', device)
                right_crt.connect('toggled', self.toggle_device)
                self.device_toggles['right'].append(right_crt)
                col.pack_start(right_crt, False)
                self.device_treeviews[device].append_column(col)
                
                kwargs = {'visible': True}
                left_tb = Gtk.ToggleButton(**kwargs)
                kwargs = {'visible': True}
                right_tb = Gtk.ToggleButton(**kwargs)
                
                if info['Serial Number'] in self.book.settings['devices'].keys():
                    side = self.book.settings['devices'][info['Serial Number']]
                    self.ImageCapture.Gphoto2.devices[device]['side'] = side
                    if side == 'left':
                        left_crt.set_active(True)
                        
                    elif side == 'right':
                        right_crt.set_active(True)                    
                else:
                    self.ImageCapture.Gphoto2.devices[device]['side'] = None
                entry.append(left_tb)
                entry.append(right_tb)            
            self.device_entries[device] = self.device_models[device].append(entry)

    def update_devices(self, widget):
        self.ImageCapture.Gphoto2.find_devices()
        self.ImageCapture.init_devices()        
        self.main_box.remove(self.device_controls)
        self.device_controls.destroy()
        self.init_device_controls()
        self.device_controls.show_all()

    def toggle_device(self, widget, event):
        side = widget.side
        device = widget.device
        if not widget.get_active():
            for crt in self.device_toggles[side]:
                if crt.get_active():
                    crt.set_active(False)
            if side != 'center':
                if side == 'left':
                    oppos = 'right'
                elif side == 'right':
                    oppos = 'left'
                for crt in self.device_toggles[oppos]:
                    if crt.device == device:
                        crt.set_active(False)
            widget.set_active(True)
            self.ImageCapture.Gphoto2.devices[device]['side'] = side
        else:
            widget.set_active(False)
            self.ImageCapture.Gphoto2.devices[device]['side'] = None
            
    def init_info(self):
        kwargs = {'visible': True}
        self.info = Gtk.Box(**kwargs)
        self.info_model = Gtk.ListStore(str, int)
        self.info_treeview = Gtk.TreeView(self.info_model)
        col = Gtk.TreeViewColumn('Identifier')
        self.info_treeview.append_column(col)
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=0)
        
        if self.ImageCapture.capture_style == 'Single':
            col = Gtk.TreeViewColumn('Spread Count')
        elif self.ImageCapture.capture_style == 'Dual':
            col = Gtk.TreeViewColumn('Page Count')
        self.info_treeview.append_column(col)
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=1)
        
        if self.ImageCapture.capture_style == 'Single':
            self.left_leaf = self.book.page_count * 2 - 2
            self.right_leaf = self.book.page_count * 2 - 1
        elif self.ImageCapture.capture_style == 'Dual':
            self.left_leaf = self.book.page_count - 2
            self.right_leaf = self.book.page_count - 1
            
        entry = [self.book.identifier, self.book.page_count,]
        self.entry = self.info_model.append(entry)
        #self.update_info()
        self.info.set_halign(Gtk.Align.CENTER)
        self.info.set_valign(Gtk.Align.START)
        self.info.add(self.info_treeview)
        self.capture_box.pack_start(self.info, True, False, 0)
        self.info.show_all()

    def update_info(self):
        path = self.info_model.get_path(self.entry)
        self.info_model[path][0] = self.book.identifier
        self.info_model[path][1] = self.book.page_count
        
    def devices_are_ready(self):
        if not self.ImageCapture.are_devices() or \
                not self.ImageCapture.capture_style:
            CA.dialog(message='Cannot capture: No devices found.')
            return False
        elif self.book.capture_style is not None and \
                self.ImageCapture.capture_style != self.book.capture_style:
            CA.dialog(message='Cannot capture: Detected capture style ('+
                      self.ImageCapture.capture_style+') does not match scandata ('+
                      self.book.capture_style+')')
            return False
        else:
            if self.ImageCapture.capture_style == 'Single':
                for device in self.device_toggles['center']:
                    if device.get_active():
                        return True
                CA.dialog(message='Cannot capture: No device selected.')
                return False
            elif self.ImageCapture.capture_style == 'Dual':
                l, r = False
                for ldevice, rdevice in zip(self.device_toggles['left'], 
                                            self.device_toggles['right']):
                    if ldevice.get_active():
                        l = True
                    if rdevice.get_active():
                        r = True
                    if l and r:
                        return True
                if False in (l, r):
                    missing = [side for k, side in {l:'left', r:'right'}.items() if not k ].join(', ')
                    CA.dialog(message='Cannot capture: Please select a '+missing+' device.')
                    return False

    def handle_shoot(self, widget, reshoot=False):
        if self.devices_are_ready():
            self.shoot.set_sensitive(False)
            self.reshoot.set_sensitive(False)
            if self.ImageCapture.capture_style == 'Single':
                if reshoot:
                    leaf = self.left_leaf
                    self.ImageCapture.success_hooks.append(self.reshoot_success)
                    self.ImageCapture.failure_hooks.append(self.reshoot_failure)
                else:
                    leaf = self.left_leaf + 2
                    self.ImageCapture.success_hooks.append(self.shoot_success)
                    self.ImageCapture.failure_hooks.append(self.shoot_failure)
                leafnum = "%04d" % leaf
                dst = {'center': {'raw_dst': self.book.dirs['raw_images'] + '/' + \
                                      self.book.identifier + '_raw_' + leafnum + '.JPG',
                                  'scaled_dst': self.book.dirs['scaled'] + '/' + \
                                      self.book.identifier + '_scaled_' + leafnum + '.jpg',
                                  'leaf': leaf,
                                  'device': self.ImageCapture.get_device('center'),
                                  'rot_dir': 0}}
            elif self.ImageCapture.capture_style == 'Dual':
                if reshoot:
                    left_leaf = self.left_leaf
                    right_leaf = self.right_leaf
                    self.ImageCapture.success_hooks.append(self.reshoot_success)
                    self.ImageCapture.failure_hooks.append(self.reshoot_failure)
                else:
                    left_leaf = self.left_leaf + 2
                    right_leaf = self.right_leaf + 2
                    self.ImageCapture.success_hooks.append(self.shoot_success)
                    self.ImageCapture.failure_hooks.append(self.shoot_failure)
                left_leafnum = "%04d" % left_leaf
                right_leafnum = "%04d" % right_leaf
                dst = {'left': {'raw_dst': self.book.dirs['raw_images'] + '/' + \
                                    self.book.identifier + '_raw_' + left_leafnum + '.JPG',
                                'scaled_dst': self.book.dirs['scaled'] + '/' + \
                                      self.book.identifier + '_scaled_' + left_leafnum + '.jpg',
                                'leaf': left_leaf,
                                'device': self.ImageCapture.get_device('left'),
                                'rot_dir': -1},
                       'right': {'raw_dst': self.book.dirs['raw_images'] + '/' + \
                                     self.book.identifier + '_raw_' + right_leafnum + '.JPG',
                                 'scaled_dst': self.book.dirs['scaled'] + '/' + \
                                     self.book.identifier + '_scaled_' + right_leafnum + '.jpg',
                                 'leaf': right_leaf,
                                 'device': self.ImageCapture.get_device('right'),
                                 'rot_dir': 1}}
            self.ImageCapture.capture_from_devices(**dst)
            
    def shoot_success(self, *args, **kwargs):
        self.book.page_count += 1
        self.nav_next_spread()
        self.shoot.set_sensitive(True)
        self.reshoot.set_sensitive(True)
        
    def shoot_failure(self, *args, **kwargs):
        self.shoot.set_sensitive(True)
        self.reshoot.set_sensitive(True)
                
    def reshoot_success(self, *args, **kwargs):
        self.update_preview()
        self.shoot.set_sensitive(True)
        self.reshoot.set_sensitive(True)

    def reshoot_failure(self, *args, **kwargs):
        self.shoot.set_sensitive(True)
        self.reshoot.set_sensitive(True)

    def handle_reshoot(self, widget):
        reshoot = CA.dialog(message='Are you sure you want to '+
                            'reshoot the current spread?',
                            Buttons={Gtk.STOCK_YES: Gtk.ResponseType.YES,
                                     Gtk.STOCK_NO: Gtk.ResponseType.NO})
        if reshoot:
            self.handle_shoot(widget, reshoot=True)

    def handle_insert(self, widget):
        pass
