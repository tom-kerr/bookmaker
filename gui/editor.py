import sys, os, re, math, time
from copy import copy, deepcopy
from io import StringIO, BytesIO

from PIL import Image

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf
import cairo

from environment import Environment
from util import Util
from datastructures import Crop, Box
from processing import ProcessHandling
from components.tesseract import Tesseract
from .history import History
from .metadata import Metadata
from .common import CommonActions as ca
#from bibs.bibs import Bibs


class Editor(object):

    def __init__(self, window, book):
        self.window = window
        self.window.connect('key-press-event', self.key_press)
        self.window.connect('delete-event', self.quit)
        self.init_data(book)
        Environment.set_current_path()
        self.window.set_title('Editing ' + self.book.identifier)
        self.init_image_window()
        self.init_meta_window()
        self.init_export_window()
        self.init_notebook()
        self.window.add(self.notebook)
        self.window.show()
        
    def quit(self, widget, data):
        if (self.ImageEditor.save_needed['l'][0] or 
            self.ImageEditor.save_needed['r'][0] or
            (self.ExportHandler.ProcessHandler.processes != 0)):
            if ca.dialog(None, Gtk.MessageType.QUESTION,
                         'There are unsaved changes/running processes, '+
                         'are you sure you want to quit?',
                             {Gtk.STOCK_OK: Gtk.ResponseType.OK,
                              Gtk.STOCK_CANCEL: Gtk.ResponseType.CANCEL}):
                try:
                    self.ExportHandler.ProcessHandler.finish()
                except Exception as e:
                    ca.dialog(None, Gtk.MessageType.ERROR,
                              'Failed to stop processes! \nException: ' + 
                              str(e),
                              {Gtk.STOCK_OK: Gtk.ResponseType.OK})
                    return True
                else:
                    return False
            else:
                return True

    def init_data(self, book):
        self.book = book
        for leaf in range(0, self.book.page_count):
            for crop in ('cropBox', 'pageCrop', 'standardCrop', 'contentCrop'):
                if self.book.crops[crop].box[leaf].is_valid():
                    self.book.crops[crop].calculate_box_with_skew_padding(leaf)
        self.book.cropBox.update_pagination()

    def key_press(self, widget, data):
        key = data.keyval
        func, args = None, None
        if key is 44:
            func = self.ImageEditor.walk_stack
            args = (None, 'prev')
        elif key is 46:
            func = self.ImageEditor.walk_stack
            args = (None, 'next')
        elif key is 115:
            func = self.ImageEditor.save_changes
        elif key is 120:
            func = self.ImageEditor.undo_changes
        elif key is 122:
            func = self.ImageEditor.toggle_zoom
        elif key is 99:
            func = self.ImageEditor.copy_crop
        elif key is 118:
            func = self.ImageEditor.paste_crop
        elif key is 102:
            func = self.ImageEditor.fit_crop
        elif (Gdk.ModifierType.MOD1_MASK & data.state) and key in (65361, 65363):
            if key == 65361:
                args = (-90)
            elif key == 65363:
                args = (90)
            func = self.ImageEditor.rotate_selected
        elif key is 97:
            func = self.ImageEditor.assert_pagination
        if func:
            try:
                if args:
                    func(*args)
                else:
                    func()
            except Exception as e:
                self.book.logger.error(str(e))
                ca.dialog(message=str(e))
    
    def init_meta_window(self):
        self.MetaEditor = MetaEditor(self)

    def init_image_window(self):
        self.ImageEditor = ImageEditor(self, self.book)

    def init_export_window(self):
        self.ExportHandler = ExportHandler(self)

    def init_notebook(self):
        kwargs = {'tab_pos': Gtk.PositionType.RIGHT,
                  'show_border': False,
                  'visible': True}
        self.notebook = Gtk.Notebook(**kwargs)
        self.notebook.set_size_request(self.window.width, self.window.height)
        label = Gtk.Label(label="Image Editor", angle=270.0)
        w, h = 25, self.window.height/3
        label.set_size_request(w, h)
        self.notebook.append_page(self.ImageEditor.main_layout, label)
        label = Gtk.Label(label="Metadata", angle=270.0)
        label.set_size_request(w, h)
        self.notebook.append_page(self.MetaEditor.main_layout, label)
        label = Gtk.Label(label="Export", angle=270.0)
        label.set_size_request(w, h)
        self.notebook.append_page(self.ExportHandler.main_layout, label)
                                  
                                          
class ImageEditor(object):

    vspace = 250
    hspace = 175

    def __init__(self, editor, book):
        self.editor = editor
        self.book = book

        self.init_main_layout()
        self.init_history()

        self.left_canvas = Box()
        self.left_canvas.image = None
        self.left_event_box = Box()
        self.left_zones = None

        self.right_canvas = Box()
        self.right_canvas.image = None
        self.right_event_box = Box()
        self.right_zones = None

        self.current_spread = 0
        self.selected = None
        self.released = None

        self.left_delete_overlay = None
        self.right_delete_overlay = None

        #self.left_background_overlay = None
        #self.right_background_overlay = None

        self.selection_overlay = None

        self.zoom_box = Box()
        self.zoom_box.set_dimension('w', ImageEditor.vspace-40)
        self.zoom_box.set_dimension('h', ImageEditor.hspace-15)
        self.zoom_box.image = None
        self.loading_zoom = False

        self.cursor = None
        self.cursor_pos = {'x':None,
                           'y':None}

        self.crop_copy = None
        self.active_zone = None
        self.active_crop = dict.fromkeys(range(0, self.book.page_count), None)
        self.show_crop = {'cropBox': True,
                          'pageCrop':True,
                          'standardCrop':True,
                          'contentCrop':False}

        self.show_background = True

        self.draw_spread(self.current_spread)
        self.build_controls()
        self.main_layout.show()

    def init_main_layout(self):
        kwargs = {'height': self.editor.window.height,
                  'width': self.editor.window.height,
                  'visible': True}
        self.main_layout = Gtk.Layout(**kwargs)
        gray = Gdk.Color.parse('black')[1]
        self.main_layout.modify_bg(Gtk.StateType.NORMAL, gray)
        self.main_layout.set_events(Gdk.EventMask.BUTTON_PRESS_MASK
                                    | Gdk.EventMask.POINTER_MOTION_MASK
                                    | Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.main_layout.connect('button-press-event', self.clicked)
        self.main_layout.connect('motion-notify-event', self.motion_capture)
        self.main_layout.connect('button-release-event', self.release)
        self.main_layout.connect('leave-notify-event', self.left)

    def init_history(self):
        self.history = History(self.book)
        self.save_needed = {'l': (False, None),
                            'r': (False, None)}

    def build_controls(self):
        self.build_vertical_controls()
        self.build_horizontal_controls()
        x, y = int(self.editor.window.width - ImageEditor.vspace), 0
        self.main_layout.put(self.vertical_controls_layout, x, y)
        x, y = 0, int(self.editor.window.height - ImageEditor.hspace)
        self.main_layout.put(self.horizontal_controls_layout, x, y)               

    def build_vertical_controls(self):
        kwargs = {'visible': True}
        self.vertical_controls_layout = Gtk.Layout(**kwargs)
        gray = Gdk.Color.parse('light gray')[1]
        self.vertical_controls_layout.modify_bg(Gtk.StateType.NORMAL, gray)
        w = ImageEditor.vspace
        h = int(self.editor.window.height - ImageEditor.hspace)        
        self.vertical_controls_layout.set_size_request(w, h)
        self.build_display_controls()
        x, y = 0, int(self.editor.window.height - ImageEditor.hspace) - h
        self.vertical_controls_layout.put(self.frame, x, y)

    def build_display_controls(self):
        kwargs = {'visible': True}
        self.display_controls_eventbox = Gtk.EventBox(**kwargs)
        w, h = ImageEditor.vspace-25, 260
        self.display_controls_eventbox.set_size_request(w, h)
        
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.display_controls = Gtk.Box(**kwargs)
        w, h = ImageEditor.vspace-25, 260
        self.display_controls.set_size_request(w, h)
        self.display_controls_eventbox.add(self.display_controls)

        #self.init_nav_controls()

        self.init_draw_options()

        kwargs = {'label': 'Drawing',
                  'shadow_type': Gtk.ShadowType.ETCHED_IN,
                  'label_xalign': 0.7,
                  'label_yalign': 0.5,
                  'visible': True}
        self.draw_options_frame = Gtk.Frame(**kwargs)
        self.draw_options_frame.set_size_request(w/2,-1)
        self.draw_options_frame.add(self.draw_options)

        self.init_active_crop_options()

        kwargs = {'label': 'Active Crop',
                  'shadow_type': Gtk.ShadowType.ETCHED_IN,
                  'label_xalign': 0.7,
                  'label_yalign': 0.5,
                  'visible': True}
        self.active_crop_frame = Gtk.Frame(**kwargs)
        self.active_crop_frame.add(self.active_crop_options)

        self.display_controls.pack_start(self.draw_options_frame, False, False, 10)
        self.display_controls.pack_start(self.active_crop_frame, False, False, 10)

        kwargs = {'label': 'Display Controls',
                  'label_xalign': 0.5,
                  'label_yalign': 0.5,
                  'shadow_type': Gtk.ShadowType.ETCHED_OUT,
                  'visible': True}
        self.frame = Gtk.Frame(**kwargs)
        self.frame.add(self.display_controls_eventbox)

    def init_nav_controls(self):
        self.step_seek = Gtk.HButtonBox()
        self.prev_button = Gtk.Button(label='Previous Spread')
        self.prev_button.connect('clicked', self.walk_stack, 'prev')
        self.next_button = Gtk.Button(label='Next Spread')
        self.next_button.connect('clicked', self.walk_stack, 'next')
        self.step_seek.add(self.prev_button)
        self.step_seek.add(self.next_button)
        self.step_seek.hide()

    def toggle_active_crop(self, widget):
        buttons={'Apply to all pages?': 0,
                 'Apply to all pages going forward?': 1,
                 Gtk.STOCK_CANCEL: Gtk.ResponseType.NO}
        if self.selected is None:
            buttons['Apply to this spread only?'] = 2
        else:
            buttons['Apply to this leaf only?'] = 3
        response = ca.dialog(message='Do you want to...', Buttons=buttons)
        if response is False:
            return
        selection = widget.crop
        if selection is not None:
            if response == 0:
                affected = range(0, self.book.page_count)
            elif response == 1:
                start = self.selected if self.selected is not None else self.current_spread*2
                affected = range(start, self.book.page_count)
            elif response == 2:
                left = self.current_spread*2
                right = left + 1
                affected = range(left, right+1)
            elif response == 3:
                affected = [self.selected]

            for leaf in affected:
                self.book.cropBox.box[leaf].update_dimension('x', self.book.crops[selection].box[leaf].x)
                self.book.cropBox.box[leaf].update_dimension('y', self.book.crops[selection].box[leaf].y)
                self.book.cropBox.box[leaf].update_dimension('w', self.book.crops[selection].box[leaf].w)
                self.book.cropBox.box[leaf].update_dimension('h', self.book.crops[selection].box[leaf].h)

                self.book.cropBox.box_with_skew_padding[leaf].update_dimension(
                    'x', self.book.crops[selection].box_with_skew_padding[leaf].x)
                self.book.cropBox.box_with_skew_padding[leaf].update_dimension(
                    'y', self.book.crops[selection].box_with_skew_padding[leaf].y)
                self.book.cropBox.box_with_skew_padding[leaf].update_dimension(
                    'w', self.book.crops[selection].box_with_skew_padding[leaf].w)
                self.book.cropBox.box_with_skew_padding[leaf].update_dimension(
                    'h', self.book.crops[selection].box_with_skew_padding[leaf].h)
                self.active_crop[leaf] = selection
                for crop in ('pageCrop', 'standardCrop', 'contentCrop'):
                    active = True if crop == selection else False
                    self.book.crops[crop].active[leaf] = active
            save_point = self.selected if self.selected else self.current_spread*2
            self.set_save_needed(save_point, affected)
            self.save_changes()
            for leaf in affected[1:]:
                self.set_save_needed(leaf)
                self.save_changes(update_scandata=False)
                self.set_save_needed(leaf)
                self.save_changes(update_scandata=False)
            self.update_scandata()
            self.update_state()

    def init_draw_options(self):
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.draw_options = Gtk.Box(**kwargs)
        w, h = ImageEditor.vspace - 50, -1
        self.draw_options.set_size_request(w, h)
                                           
        #self.toggle_bg = ca.new_widget('CheckButton',
        #                                   {'label': 'background',
        #                                    'can_set_focus': False,
        #                                    'set_active': self.show_background,
        #                                    'show': True})
        #self.toggle_bg.connect('clicked', self.toggle_background)

        kwargs = {'label': 'contentCrop',
                  'can_focus': False,
                  'active': self.show_crop['contentCrop'],
                  'visible': True}
        self.toggle_content_crop = Gtk.CheckButton(**kwargs)
        self.toggle_content_crop.connect('clicked', self.toggle_crop, 'contentCrop')

        kwargs = {'label': 'standardCrop',
                  'can_focus': False,
                  'active': self.show_crop['standardCrop'],
                  'visible': True}
        self.toggle_standard_crop = Gtk.CheckButton(**kwargs)
        self.toggle_standard_crop.connect('clicked', self.toggle_crop, 'standardCrop')

        kwargs = {'label': 'pageCrop',
                  'can_focus': False,
                  'active': self.show_crop['pageCrop'],
                  'visible': True}
        self.toggle_page_crop = Gtk.CheckButton(**kwargs)
        self.toggle_page_crop.connect('clicked', self.toggle_crop, 'pageCrop')

        self.crop_toggles = {'pageCrop': self.toggle_page_crop,
                             'standardCrop': self.toggle_standard_crop,
                             'contentCrop': self.toggle_content_crop}

        #self.draw_options.pack_start(self.toggle_bg, True, True, 0)
        self.draw_options.pack_start(self.toggle_page_crop, True, True, 0)
        self.draw_options.pack_start(self.toggle_standard_crop, True, True, 0)
        self.draw_options.pack_start(self.toggle_content_crop, True, True, 0)


    def init_active_crop_options(self):
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.active_crop_options = Gtk.Box(**kwargs)
        w, h = ImageEditor.vspace - 50, -1
        self.active_crop_options.set_size_request(w, h)
                                                  
        kwargs = {'label': 'Page Crop',
                  'visible': True}
        self.pageCrop_selector = Gtk.Button(**kwargs)
        self.pageCrop_selector.crop = 'pageCrop'

        kwargs = {'label': 'Standard Crop',
                  'visible': True}
        self.standardCrop_selector = Gtk.Button(**kwargs)
        self.standardCrop_selector.crop = 'standardCrop'

        kwargs = {'label': 'Content Crop',
                  'visible': True}
        self.contentCrop_selector = Gtk.Button(**kwargs)
        self.contentCrop_selector.crop = 'contentCrop'

        self.pageCrop_selector.connect('clicked', self.toggle_active_crop)
        self.standardCrop_selector.connect('clicked', self.toggle_active_crop)
        self.contentCrop_selector.connect('clicked', self.toggle_active_crop)

        self.active_crop_options.pack_start(self.pageCrop_selector, False, True, 0)
        self.active_crop_options.pack_start(self.standardCrop_selector, False, True, 0)
        self.active_crop_options.pack_start(self.contentCrop_selector, False, True, 0)

    def build_horizontal_controls(self):       
        kwargs = {'visible': True}
        self.horizontal_controls_layout = Gtk.Layout(**kwargs)
        gray = Gdk.Color.parse('light gray')[1]
        self.horizontal_controls_layout.modify_bg(Gtk.StateType.NORMAL, gray)
        w, h = self.editor.window.width, ImageEditor.hspace+50
        self.horizontal_controls_layout.set_size_request(w, h)
        
        kwargs = {'visible': True}
        self.horizontal_controls = Gtk.Layout(**kwargs)
        w, h = self.editor.window.width, ImageEditor.hspace
        self.horizontal_controls.set_size_request(w, h)
                                                                                  
        self.init_spread_slider()
        self.init_skew_slider()
        self.init_skew_toggle()
        self.init_meta_widgets()
        self.init_save_undo_buttons()
        self.init_copy_buttons()
        self.init_capture_buttons()

        self.horizontal_controls.put(self.spread_slider, 0, 0)        
        self.horizontal_controls.put(self.skew_toggle, 0, 30)

        self.skew_toggle_x_left = self.left_canvas.w/2 - self.skew_toggle.get_size_request()[0]/2
        self.skew_toggle_x_right = self.left_canvas.w + \
            (self.right_canvas.w/2 - self.skew_toggle.get_size_request()[0]/2)
        
        x = self.left_canvas.w/2 - (self.left_page_type_menu.width/2)
        y = 40
        self.horizontal_controls.put(self.left_page_type_menu, x, y)
        w,h = self.left_page_type_menu.get_size_request()
        
        self.horizontal_controls.put(self.skew_slider, x, 60)
        
        x = self.left_canvas.w + (self.right_canvas.w/2 - (self.right_page_type_menu.width/2))
        self.horizontal_controls.put(self.right_page_type_menu, x, y)

        x = self.left_canvas.w - self.left_page_type_menu.width/2
        self.horizontal_controls.put(self.copy_from_button, x, 40)
        self.horizontal_controls.put(self.apply_forward_button, x, 65)

        x = self.left_canvas.w - (self.reshoot_spread_button.get_size_request()[0]/2)
        self.horizontal_controls.put(self.reshoot_spread_button, x, 100)
        self.horizontal_controls.put(self.insert_spread_button, x, 125)
        
        self.horizontal_controls.put(self.save_button, 0, 60)
        self.horizontal_controls.put(self.undo_button, 0, 90)
        self.horizontal_controls_layout.put(self.horizontal_controls, 0, 0)

    def init_capture_buttons(self):
        kwargs = {'label': 'reshoot spread',
                  'sensitive': False,
                  'visible': True}
        self.reshoot_spread_button = Gtk.Button(**kwargs)
        w, h = 125, -1
        self.reshoot_spread_button.set_size_request(w, h )
                                                        
        kwargs = {'label':'insert spread',
                  'sensitive': False,
                  'visible': True}
        self.insert_spread_button = Gtk.Button(**kwargs)
        w, h = 125, -1
        self.insert_spread_button.set_size_request(w, h)
        
    def init_copy_buttons(self):
        kwargs = {'visible': False}
        self.copy_from_button = Gtk.Button(**kwargs)
        w, h = 150, -1
        self.copy_from_button.set_size_request(w, h)
        self.copy_from_button.connect('button-press-event', self.copy_crop_from_opposite)

        kwargs = {'visible': False,
                  'sensitive': True}
        self.apply_forward_button = Gtk.Button(**kwargs)
        w, h = 150, -1
        self.apply_forward_button.set_size_request(w, h)
        self.apply_forward_button.connect('button-press-event', self.apply_crop_forward)

    def init_save_undo_buttons(self):
        kwargs = {'label': 'save',
                  'sensitive': False,
                  'visible': True}
        self.save_button = Gtk.Button(**kwargs)
        self.save_button.connect('button-press-event', self.save_changes)

        kwargs = {'label':'undo',
                  'sensitive': False,
                  'visible': True}
        self.undo_button = Gtk.Button(**kwargs)
        self.undo_button.connect('button-press-event', self.undo_changes)

    def init_meta_widgets(self):
        self.left_page_type_menu = Gtk.ComboBoxText()
        self.left_page_type_menu.show()
        self.right_page_type_menu = Gtk.ComboBoxText()
        self.right_page_type_menu.show()
        Gtk.rc_parse_string("""style "menulist" { GtkComboBox::appears-as-list = 1 } class "GtkComboBox" style "menulist" """)
        self.init_page_type_menu()

    def init_page_type_menu(self):
        self.left_page_type_menu.set_size_request(150, -1)
        self.left_page_type_menu.width = 150
        self.left_page_type_menu.side = 'left'
        for num, struct in Metadata.book_structure.items():
            self.left_page_type_menu.insert_text(int(num), str(struct))
        self.right_page_type_menu.set_size_request(150, -1)
        self.right_page_type_menu.width = 150
        self.right_page_type_menu.side = 'right'
        for num, struct in Metadata.book_structure.items():
            self.right_page_type_menu.insert_text(int(num), str(struct))
        self.update_meta_widgets()
        self.left_page_type_menu.connect('changed', self.set_page_type)
        self.right_page_type_menu.connect('changed', self.set_page_type)
            
    def init_skew_slider(self):
        kwargs = {'lower': -4.00,
                  'upper': 4.00,
                  'step_increment': 0.1,
                  'value': 0.0}
        adj = Gtk.Adjustment(**kwargs)

        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'adjustment': adj,
                  'digits': 2,
                  'value_pos': Gtk.PositionType.BOTTOM,
                  'visible': False}
        self.skew_slider = Gtk.Scale(**kwargs)
        w, h = 190, -1
        self.skew_slider.set_size_request(w, h)
        self.skew_slider.connect('value-changed', self.adjust_skew)

    def init_skew_toggle(self):
        kwargs = {'label': '',
                  'visible': False}
        self.skew_toggle = Gtk.Button(**kwargs)
        w, h = 100, -1
        self.skew_toggle.set_size_request(w, h)
        self.skew_toggle.connect('button-press-event', self.toggle_skew)

    def init_spread_slider(self):
        kwargs = {'lower': 0,
                  'upper': self.book.page_count-1,
                  'step_increment': 2,
                  'value': 2,}
                  #'update_policy': Gtk.UPDATE_DISCONTINUOUS,}
        adj = Gtk.Adjustment(**kwargs)

        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'adjustment': adj,
                  'digits': 0,
                  'value_pos': Gtk.PositionType.BOTTOM,
                  'can_focus': False,
                  'visible': True}
        self.spread_slider = Gtk.Scale(**kwargs)
        w, h = self.editor.window.width-ImageEditor.vspace, -1
        self.spread_slider.set_size_request(w, h)
        self.spread_slider.set_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.spread_slider.connect('button-release-event', self.select_spread)

    def init_zoom(self, leaf):
        if leaf is None:
            return
        raw = Image.open(self.book.raw_images[leaf])
        raw_width, raw_height = raw.size[0], raw.size[1]
        rot_const = ca.get_rotation_constant(self.book.cropBox.rotate_degree[leaf])
        rotated = self.get_rotated(raw, leaf,
                                   rot_const + (0-self.book.cropBox.skew_angle[leaf]),
                                   output='pixbuf')
        #raw = GdkPixbuf.Pixbuf.new_from_file(self.book.raw_images[leaf])
        #raw_width, raw_height = raw.get_width(), raw.get_height()
        #self.zoom_raw = GdkPixbuf.Pixbuf(GdkPixbuf.Colorspace.RGB,
        #                               1,
        #                               8,
        #                               raw_width,
        #                               raw_height)

        #rot_const = ca.get_rotation_constant(self.book.cropBox.rotate_degree[leaf])
        #rotated = self.zoom_raw.rotate_simple(rot_const)

        self.zoom_raw = self.render_image(rotated, raw_height, raw_width, 
                                          leaf, 1, 1, output='pixbuf')

        area = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                                    1, 8,
                                    self.zoom_box.w,
                                    self.zoom_box.h)

        self.zoom_raw.copy_area(0,0, self.zoom_box.w, self.zoom_box.h, area, 0,0)
        self.zoom_box.image = Gtk.Image.new_from_pixbuf(area)
        self.zoom_box.image.show()
        self.horizontal_controls.put(self.zoom_box.image,
                                     self.editor.window.width-ImageEditor.vspace,0)

    def toggle_zoom(self):
        if self.zoom_box.image is None:
            self.loading_zoom = True
            self.set_cursor(cursor_style=Gdk.CursorType.WATCH)
            self.init_zoom(self.selected)
            self.loading_zoom = False
            self.set_cursor(cursor_style=None)
        else:
            self.destroy_zoom()

    def destroy_zoom(self):
        if self.zoom_box.image is not None:
            self.zoom_box.image.destroy()
            self.zoom_box.image = None

    def update_zoom(self, x, y):
        if self.selected is None:
            return
        if self.selected%2==0:
            scale_factor = self.left_scale_factor
        else:
            scale_factor = self.right_scale_factor
        area = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                                    1, 8,
                                    self.zoom_box.w,
                                    self.zoom_box.h)
        x = (x * scale_factor)*4
        y = (y * scale_factor)*4

        if self.selected%2!=0:
            x -= (self.left_canvas.w * scale_factor) * 4

        if x - self.zoom_box.w/2 < 0:
            x = self.zoom_box.w/2
        if y - self.zoom_box.h/2  < 0:
            y = self.zoom_box.h/2

        if x + self.zoom_box.w/2 > self.zoom_raw.get_width():
            x = self.zoom_raw.get_width() - 1 - self.zoom_box.w/2
        if y + self.zoom_box.h/2 > self.zoom_raw.get_height():
            y = self.zoom_raw.get_height() - 1 - self.zoom_box.h/2

        center_x = int(x - self.zoom_box.w/2)
        center_y = int(y - self.zoom_box.h/2)

        self.zoom_raw.copy_area(center_x, center_y, self.zoom_box.w, self.zoom_box.h, area, 0,0)
        self.zoom_box.image.destroy()
        self.zoom_box.image = Gtk.Image.new_from_pixbuf(area)
        self.zoom_box.image.show()
        self.horizontal_controls.put(self.zoom_box.image,
                                     self.editor.window.width-ImageEditor.vspace,0)

    def update_meta_widgets(self):
        left = self.current_spread * 2
        right = left + 1
        for leaf in (left, right):
            for key, struct in Metadata.book_structure.items():
                if struct == self.book.cropBox.page_type[leaf]:
                    if leaf%2==0:
                        self.left_page_type_menu.set_active(key)
                    else:
                        self.right_page_type_menu.set_active(key)
                    break

    def update_horizontal_control_widgets(self):
        if self.selected is None:
            self.skew_slider.hide()
            self.skew_toggle.hide()
            self.copy_from_button.hide()
            self.apply_forward_button.hide()
            return

        leaf = self.selected

        self.skew_slider.set_value(self.book.cropBox.skew_angle[leaf])
        self.skew_slider.show()
        self.set_skew_toggle()

        if self.history.has_history(self.selected):
            self.undo_button.set_sensitive(True)
        else:
            self.undo_button.set_sensitive(False)

        if leaf%2==0:
            side = 'verso'
            facing_side = 'recto'
        else:
            side = 'recto'
            facing_side = 'verso'
        self.copy_from_button.set_label('copy crop from ' + facing_side)
        self.copy_from_button.show()
        self.apply_forward_button.set_label('apply ' + side + ' forward')
        self.apply_forward_button.show()

    def set_page_type(self, widget):
        if widget.side == 'left':
            leaf = self.current_spread * 2
        elif widget.side == 'right':
            leaf = (self.current_spread * 2) + 1
        selection = widget.get_active()
        page_type = Metadata.book_structure[selection]
        self.book.cropBox.page_type[leaf] = page_type
        if page_type in ('Delete', 'ColorCard', 'Tissue'):
            self.book.cropBox.add_to_access_formats[leaf] = False
        else:
            self.book.cropBox.add_to_access_formats[leaf] = True
        self.update_canvas(leaf)
        self.update_scandata()

    def assert_pagination(self):
        if self.selected is None:
            return
        response = ca.dialog(message='Enter page number:',
                             Buttons={Gtk.STOCK_OK: Gtk.ResponseType.APPLY,
                                      Gtk.STOCK_CANCEL: Gtk.ResponseType.CANCEL,
                                      'Delete': Gtk.ResponseType.DELETE_EVENT},
                             get_input=True)
        if not response:
            return
        elif response is Gtk.ResponseType.DELETE_EVENT.real:
            self.book.cropBox.delete_assertion(self.selected)
            self.draw_spread(self.current_spread)
            return
        rawinput = re.search('[0-9]+', response)
        if rawinput:
            number = rawinput.group(0)
            self.book.cropBox.assert_page_number(self.selected, number)
            self.draw_spread(self.current_spread)

    def copy_crop(self):
        if self.selected is None:
            return
        self.crop_copy = copy(self.book.cropBox.box[self.selected])
        self.released = True

    def paste_crop(self):
        if self.selected is None:
            return
        if self.crop_copy is not None:
            for dimension, value in self.crop_copy.dim.items():
                self.book.cropBox.box[self.selected].update_dimension(dimension, value)
                self.book.cropBox.box_with_skew_padding[self.selected].update_dimension(dimension, value)
            self.set_save_needed(self.selected)
            self.update_canvas(self.selected)
            self.released = True

    def fit_crop(self):
        if self.selected is None:
            return
        if self.book.contentCrop.box[self.selected].is_valid():
            content = self.book.contentCrop.box[self.selected]
            self.book.cropBox.box[self.selected].position_around(content)
            if self.book.pageCrop.box[self.selected].is_valid():
                container = self.book.pageCrop.box[self.selected]
                self.book.cropBox.box[self.selected].fit_within(container)
        else:
            if self.book.pageCrop.box[self.selected].is_valid():
                container = self.book.pageCrop.box[self.selected]
                self.book.cropBox.box[self.selected].center_within(container)

        if self.book.contentCrop.box_with_skew_padding[self.selected].is_valid():
            content = self.book.contentCrop.box_with_skew_padding[self.selected]
            self.book.cropBox.box_with_skew_padding[self.selected].position_around(content)
            if self.book.pageCrop.box_with_skew_padding[self.selected].is_valid():
                container = self.book.pageCrop.box_with_skew_padding[self.selected]
                self.book.cropBox.box_with_skew_padding[self.selected].fit_within(container)
        else:
            if self.book.pageCrop.box_with_skew_padding[self.selected].is_valid():
                container = self.book.pageCrop.box_with_skew_padding[self.selected]
                self.book.cropBox.box_with_skew_padding[self.selected].center_within(container)
        self.released = True
        self.update_canvas(self.selected)

    def copy_crop_from_opposite(self, widget, data):
        if self.selected%2==0:
            opposite = self.selected + 1
        else:
            opposite = self.selected - 1
        new_width = self.book.cropBox.box[opposite].dim['w']
        new_height = self.book.cropBox.box[opposite].dim['h']
        self.book.cropBox.box[self.selected].update_dimension('w', new_width)
        self.book.cropBox.box[self.selected].update_dimension('h', new_height)
        self.book.cropBox.box_with_skew_padding[self.selected].update_dimension('w', new_width)
        self.book.cropBox.box_with_skew_padding[self.selected].update_dimension('h', new_height)
        self.released = True
        self.update_canvas(self.selected)
        self.update_scandata()
        self.set_save_needed(self.selected)

    def apply_crop_forward(self, widget, data):
        if not self.selected:
            return
        new_box = {}
        new_box_with_skew_padding = {}
        affected = []
        for leaf, box in self.book.cropBox.box.items():
            if (leaf > self.selected and
                self.book.cropBox.hand_side[leaf] ==
                self.book.cropBox.hand_side[self.selected]):
                new_box[leaf] = copy(self.book.cropBox.box[self.selected])
                new_box_with_skew_padding[leaf] = copy(self.book.cropBox.box_with_skew_padding[self.selected])
                affected.append(leaf)
            else:
                new_box[leaf] = copy(box)
                new_box_with_skew_padding[leaf] = copy(self.book.cropBox.box_with_skew_padding[leaf])
        self.book.cropBox.box = copy(new_box)
        self.book.cropBox.box_with_skew_padding = copy(new_box_with_skew_padding)
        self.update_canvas(self.selected)
        self.update_scandata()
        self.set_save_needed(self.selected, affected)

    def adjust_skew(self, widget):
        new_skew_value = widget.get_value()
        if new_skew_value != self.book.cropBox.skew_angle[self.selected]:
            self.book.cropBox.skew_angle[self.selected] = widget.get_value()
            if self.book.cropBox.box[self.selected].is_valid():
                self.book.cropBox.calculate_box_with_skew_padding(self.selected)
                self.update_canvas(self.selected)
            self.set_save_needed(self.selected)
            #self.draw_select()

    def set_skew_toggle(self):
        if self.selected is None:
            return
        if self.book.cropBox.skew_active[self.selected]:
            self.skew_toggle.set_label('disable skew')
            self.skew_slider.set_sensitive(True)
        else:
            self.skew_toggle.set_label('enable skew')
            self.skew_slider.set_sensitive(False)
        self.skew_toggle.show()

    def toggle_background(self, widget):
        if self.show_background:
            self.show_background = False
        else:
            self.show_background = True
        self.draw_spread(self.current_spread)
        #self.draw_select()

    def toggle_skew_button_move(self, leaf):
        w,h = self.skew_toggle.get_size_request()
        if leaf%2==0:
            x = self.skew_toggle_x_left
            rect = self.left_page_type_menu.get_allocation()
        else:
            x = self.skew_toggle_x_right
            rect = self.right_page_type_menu.get_allocation()
        self.horizontal_controls.move(self.skew_toggle, x, 90)
        self.horizontal_controls.move(self.skew_slider, rect.x, 120)

    def toggle_skew(self, widget, data):
        if self.book.cropBox.skew_active[self.selected]:
            self.book.cropBox.skew_active[self.selected] = False
            self.skew_toggle.set_label('enable skew')
            self.skew_slider.set_sensitive(False)
        else:
            self.book.cropBox.skew_active[self.selected] = True
            self.skew_toggle.set_label('disable skew')
            self.skew_slider.set_sensitive(True)
        self.set_save_needed(self.selected)
        self.update_canvas(self.selected)
        #self.draw_select()

    def toggle_crop(self, widget, crop):
        if self.show_crop[crop]:
            self.show_crop[crop] = False
        else:
            self.show_crop[crop] = True
        self.draw_spread(self.current_spread)

    def select_spread(self, widget, event):
        leaf = int(widget.get_value())
        new_spread = int(math.floor(leaf/2))
        if new_spread != self.current_spread:
            self.current_spread = new_spread
            self.update_state()

    def walk_stack(self, widget, direction):
        self.save_changes()
        if direction == 'next':
            if self.current_spread < self.book.page_count/2 - 1:
                self.current_spread += 1
            else:
                return
        elif direction == 'prev':
            if self.current_spread > 0:
                self.current_spread -=1
            else:
                return
        self.update_state()

    def update_state(self):
        try:
            self.selected = None
            self.update_horizontal_control_widgets()
            self.update_meta_widgets()
            self.remove_overlays()
            left_leaf = self.current_spread * 2
            self.spread_slider.set_value(left_leaf)
            self.destroy_zoom()
            self.save_changes()
            self.draw_spread(self.current_spread)
        except Exception as e:
            string = 'Failed to update state!\n', str(e)
            self.book.logger.error(string)
            ca.dialog(message=string)
        
    def clicked(self, widget, data):
        self.drag_root = {'x':data.x_root, 'y': data.y_root}
        if self.left_canvas.contains_point(self.cursor_pos['x'], self.cursor_pos['y']):
            leaf = self.left_event_box.leaf
        elif self.right_canvas.contains_point(self.cursor_pos['x'], self.cursor_pos['y']):
            leaf = self.right_event_box.leaf
        else:
            return

        if not self.book.cropBox.add_to_access_formats[leaf]:
            return

        for side in (self.left_zones, self.right_zones):
            if side is not None:
                for zone, rect in side.items():
                    if rect.contains_point(self.cursor_pos['x'], self.cursor_pos['y']):
                        self.active_zone = zone
                        break

        if leaf is not self.selected:
            self.destroy_zoom()
            #self.draw_select()
            self.save_changes()

        #if self.selection_overlay is None:
        #    self.draw_select()

        self.selected = leaf
        self.toggle_skew_button_move(leaf)
        self.update_horizontal_control_widgets()

        if (self.left_event_box.contains_point(self.cursor_pos['x'], self.cursor_pos['y']) or
            self.right_event_box.contains_point(self.cursor_pos['x']-self.left_canvas.w, self.cursor_pos['y'])):
            self.selector()
            if self.active_zone == None:
                self.active_zone = 'all'

    def selector(self):
        self.released = not self.released
        if self.released:
            self.active_zone = None
            self.editor.window.get_window().set_cursor(None)
            self.cursor = None

    def release(self, widget, data):
        #print 'released'
        self.released = True
        self.active_zone = None
        self.editor.window.get_window().set_cursor(None)
        self.cursor = None

    def entered(self, widget, data):
        pass
        #print "entered " + str(widget.crop) + ' on leaf ' + str(widget.leaf)
        #self.inside = widget.crop
        #widget.grab_focus()
        #self.drag_pos = None
        #widget.selected = True

    def left(self, widget, data):
        #print "left " + str(widget.crop) + 'on leaf ' + str(widget.leaf)
        self.active_zone = None
        self.editor.window.get_window().set_cursor(None)
        self.cursor = None
        #pass
        #return False

    def motion_capture(self, widget, data):
        #print data.x, data.y
        if self.zoom_box.image is not None:
            self.update_zoom(data.x, data.y)

        x, y = data.x_root, data.y_root
        self.cursor_pos['x'] = data.x
        self.cursor_pos['y'] = data.y

        if self.selected is None or self.released:
            self.set_cursor(data.x, data.y)
            return

        if self.selected%2==0:
            canvas = self.left_canvas
            event_box = self.left_event_box
        else:
            canvas = self.right_canvas
            event_box = self.right_event_box

        x_delta, y_delta = self.calc_deltas(canvas, event_box, x, y)
        if x_delta == 0 and y_delta == 0:
            return

        self.drag_root['x'] = x
        self.drag_root['y'] = y

        if self.active_zone == 'all':
            self.move_crop(x_delta, y_delta)
            self.main_layout.move(event_box.image,
                                   int(self.book.cropBox.box_with_skew_padding[self.selected].x/4),
                                   int(self.book.cropBox.box_with_skew_padding[self.selected].y/4))
        else:
            self.adjust_crop_size(x_delta, y_delta)
        self.set_save_needed(self.selected)
        self.update_canvas(self.selected)

    def calc_deltas(self, canvas, event_box, x_pos, y_pos):
        x_delta = int(x_pos - self.drag_root['x'])
        y_delta = int(y_pos - self.drag_root['y'])

        if event_box.x + x_delta < 0:
            x_delta = 0 - event_box.x
        if event_box.y + y_delta < 0:
            y_delta = 0 - event_box.x

        if event_box.x + event_box.w + x_delta > canvas.w:
            x_delta =  canvas.w - 1 - (event_box.x + event_box.w)
        if event_box.y + event_box.h + y_delta > canvas.h:
            y_delta = canvas.h - 1 - (event_box.y + event_box.h)

        return x_delta, y_delta

    def set_cursor(self, x=None, y=None, cursor_style=None):
        if cursor_style:
            display = Gdk.Display.get_default()
            self.cursor = Gdk.Cursor.new_for_display(display, cursor_style)
            self.editor.window.get_window().set_cursor(self.cursor)
            display.flush()
            return
        if not x:
            x = self.cursor_pos['x']
        if not y:
            y = self.cursor_pos['y']
        for side in (self.left_zones, self.right_zones):
            if side is not None:
                for zone, rect in side.items():
                    if rect.contains_point(x, y):
                        if zone == 'top_left':
                            self.cursor = Gdk.Cursor.new(Gdk.CursorType.TOP_LEFT_CORNER)
                            self.editor.window.get_window().set_cursor(self.cursor)
                            return
                        elif zone == 'top_right':
                            self.cursor = Gdk.Cursor.new(Gdk.CursorType.TOP_RIGHT_CORNER)
                            self.editor.window.get_window().set_cursor(self.cursor)
                            return
                        elif zone == 'bottom_left':
                            self.cursor = Gdk.Cursor.new(Gdk.CursorType.BOTTOM_LEFT_CORNER)
                            self.editor.window.get_window().set_cursor(self.cursor)
                            return
                        elif zone == 'bottom_right':
                            self.cursor = Gdk.Cursor.new(Gdk.CursorType.BOTTOM_RIGHT_CORNER)
                            self.editor.window.get_window().set_cursor(self.cursor)
                            return        
        if not self.loading_zoom:
            self.cursor = None
            self.editor.window.get_window().set_cursor(self.cursor)

    def move_crop(self, x_delta, y_delta):
        self.destroy_zoom()
        self.adjust_crop_position(x_delta, y_delta)

    def adjust_crop_size(self, x_delta, y_delta):
        self.destroy_zoom()
        leaf = self.selected
        scale_factor = 7
        if self.active_zone == 'top_left':
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('x', self.book.cropBox.box_with_skew_padding[leaf].x + 
                 (x_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('y', self.book.cropBox.box_with_skew_padding[leaf].y + 
                 (y_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('w', self.book.cropBox.box_with_skew_padding[leaf].w - 
                 (x_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('h', self.book.cropBox.box_with_skew_padding[leaf].h - 
                 (y_delta * scale_factor))

            self.book.cropBox.box[leaf].set_dimension\
                ('x', self.book.cropBox.box[leaf].x + (x_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('y', self.book.cropBox.box[leaf].y + (y_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('w', self.book.cropBox.box[leaf].w - (x_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('h', self.book.cropBox.box[leaf].h - (y_delta * scale_factor))

        if self.active_zone == 'top_right':
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('y', self.book.cropBox.box_with_skew_padding[leaf].y +
                 (y_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('w', self.book.cropBox.box_with_skew_padding[leaf].w +
                 (x_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('h', self.book.cropBox.box_with_skew_padding[leaf].h -
                 (y_delta * scale_factor))

            self.book.cropBox.box[leaf].set_dimension\
                ('y', self.book.cropBox.box[leaf].y + (y_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('w', self.book.cropBox.box[leaf].w + (x_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('h', self.book.cropBox.box[leaf].h - (y_delta * scale_factor))

        if self.active_zone == 'bottom_left':
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('x', self.book.cropBox.box_with_skew_padding[leaf].x +
                 (x_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('w', self.book.cropBox.box_with_skew_padding[leaf].w -
                 (x_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('h', self.book.cropBox.box_with_skew_padding[leaf].h +
                 (y_delta * scale_factor))

            self.book.cropBox.box[leaf].set_dimension\
                ('x', self.book.cropBox.box[leaf].x + (x_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('w', self.book.cropBox.box[leaf].w - (x_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('h', self.book.cropBox.box[leaf].h + (y_delta * scale_factor))

        if self.active_zone == 'bottom_right':
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('w', self.book.cropBox.box_with_skew_padding[leaf].w +
                 (x_delta * scale_factor))
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
                ('h', self.book.cropBox.box_with_skew_padding[leaf].h +
                 (y_delta * scale_factor))

            self.book.cropBox.box[leaf].set_dimension\
                ('w', self.book.cropBox.box[leaf].w + (x_delta * scale_factor))
            self.book.cropBox.box[leaf].set_dimension\
                ('h', self.book.cropBox.box[leaf].h + (y_delta * scale_factor))

    def adjust_crop_position(self, x_delta, y_delta):
        leaf = self.selected
        self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
            ('x', self.book.cropBox.box_with_skew_padding[leaf].x + 
             (x_delta * 4))
        self.book.cropBox.box_with_skew_padding[leaf].set_dimension\
            ('y', self.book.cropBox.box_with_skew_padding[leaf].y + 
             (y_delta * 4))

        self.book.cropBox.box[leaf].set_dimension\
            ('x', self.book.cropBox.box[leaf].x + (x_delta * 4))
        self.book.cropBox.box[leaf].set_dimension\
            ('y', self.book.cropBox.box[leaf].y + (y_delta * 4))

        if self.book.cropBox.box_with_skew_padding[leaf].x < 0:
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension('x', 0)
        if self.book.cropBox.box_with_skew_padding[leaf].y < 0:
            self.book.cropBox.box_with_skew_padding[leaf].set_dimension('y', 0)

        if self.book.cropBox.box[leaf].x < 0:
            self.book.cropBox.box[leaf].set_dimension('x', 0)
        if self.book.cropBox.box[leaf].y < 0:
            self.book.cropBox.box[leaf].set_dimension('y', 0)

    def get_crop_event_box(self, image, leaf):
        event_box = Box()
        event_box.image = Gtk.EventBox()
        event_box.image.set_above_child(True)
        if image is not None:
            event_box.image.add(image)

            if leaf%2==0:
                scale_factor = self.left_scale_factor
            else:
                scale_factor = self.right_scale_factor

            if self.book.cropBox.box_with_skew_padding[leaf].is_valid():
                event_box.set_dimension\
                    ('x', int((self.book.cropBox.box_with_skew_padding[leaf].x/4)/
                              scale_factor))
                event_box.set_dimension\
                    ('y', int((self.book.cropBox.box_with_skew_padding[leaf].y/4)/
                              scale_factor))
                event_box.set_dimension\
                    ('w', int((self.book.cropBox.box_with_skew_padding[leaf].w/4)/
                              scale_factor))
                event_box.set_dimension\
                    ('h', int((self.book.cropBox.box_with_skew_padding[leaf].h/4)/
                              scale_factor))
            else:
                event_box.set_dimension\
                    ('x', int((self.book.cropBox.box[leaf].x/4)/scale_factor))
                event_box.set_dimension\
                    ('y', int((self.book.cropBox.box[leaf].y/4)/scale_factor))
                event_box.set_dimension\
                    ('w', int((self.book.cropBox.box[leaf].w/4)/scale_factor))
                event_box.set_dimension\
                    ('h', int((self.book.cropBox.box[leaf].h/4)/scale_factor))
            event_box.image.set_size_request(event_box.w, event_box.h)
        event_box.leaf = leaf
        return event_box

    def get_zones(self, x, y, w, h):
        zones = {}
        zones['top_left'] = Box()
        zones['top_left'].set_dimension('x', x)
        zones['top_left'].set_dimension('y', y)
        zones['top_left'].set_dimension('w', 50)
        zones['top_left'].set_dimension('h', 50)

        zones['top_right'] = Box()
        zones['top_right'].set_dimension('x', x + (w - 50))
        zones['top_right'].set_dimension('y', y)
        zones['top_right'].set_dimension('w', 50)
        zones['top_right'].set_dimension('h', 50)

        zones['bottom_left'] = Box()
        zones['bottom_left'].set_dimension('x', x)
        zones['bottom_left'].set_dimension('y', y + (h - 50))
        zones['bottom_left'].set_dimension('w', 50)
        zones['bottom_left'].set_dimension('h', 50)

        zones['bottom_right'] = Box()
        zones['bottom_right'].set_dimension('x', x + (w - 50))
        zones['bottom_right'].set_dimension('y', y + (h - 50))
        zones['bottom_right'].set_dimension('w', 50)
        zones['bottom_right'].set_dimension('h', 50)
        return zones

    def render_image(self, image, width, height, 
                     leaf, scale_factor, scale=4, output='image'):        
        attrs = Gdk.WindowAttr()
        attrs.width = width
        attrs.height = height
        attrs.window_type = Gdk.WindowType.CHILD
        types = Gdk.WindowAttributesType.X | Gdk.WindowAttributesType.Y
        window = Gdk.Window(self.editor.window.get_window(), attrs, types)
        surface = Gdk.cairo_surface_create_from_pixbuf(image, 1, window)
        ctx = cairo.Context(surface)                
        for crop in ('pageCrop', 'standardCrop', 'contentCrop', 'cropBox'):
            if (not self.book.crops[crop].box[leaf].is_valid() or
                (crop !='cropBox' and self.book.crops[crop].active[leaf]) or
                not self.show_crop[crop]):
                continue
            if crop == 'cropBox':
                ctx.set_source_rgba(0, 0, 255, 0.9)
            elif crop == 'standardCrop':
                ctx.set_source_rgba(255, 0, 255, 0.9)
            elif crop == 'pageCrop':
                ctx.set_source_rgba(255, 0, 0, 0.9)
            elif crop == 'contentCrop':
                ctx.set_source_rgba(0, 255, 0, 0.9)
            x = int((self.book.crops[crop].box_with_skew_padding[leaf].x/scale)/scale_factor)
            y = int((self.book.crops[crop].box_with_skew_padding[leaf].y/scale)/scale_factor)
            w = int((self.book.crops[crop].box_with_skew_padding[leaf].w/scale)/scale_factor)
            h = int((self.book.crops[crop].box_with_skew_padding[leaf].h/scale)/scale_factor)
            ctx.rectangle(x, y, w, h)
            ctx.stroke()    
        s = ctx.get_target()        
        s.flush()
        p = Gdk.pixbuf_get_from_surface(s, 0, 0, width, height)
        window.destroy()        
        if output=='pixbuf':
            return p
        elif output=='image':
            return Gtk.Image.new_from_pixbuf(p)            
            
    def create_delete_overlay(self, leaf):
        if leaf%2==0:
            width, height = self.left_canvas.w, self.left_canvas.h
        else:
            width, height = self.right_canvas.w, self.right_canvas.h
        pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                                  1, 8, width, height)
        attrs = Gdk.WindowAttr()
        attrs.width = width
        attrs.height = height
        attrs.window_type = Gdk.WindowType.CHILD
        types = Gdk.WindowAttributesType.X | Gdk.WindowAttributesType.Y        
        window = Gdk.Window(self.editor.window.get_window(), attrs, types)
        surface = Gdk.cairo_surface_create_from_pixbuf(pb, 0, window)
        ctx = cairo.Context(surface)                
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.set_source_rgba(4.0, 0.0, 0.0, 0.3)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint()
        s = ctx.get_target()        
        s.flush()
        pb = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        window.destroy()
        return pb

    def draw_delete_overlay(self, leaf):
        if leaf is None:
            return
        self.remove_overlays()
        overlay = self.create_delete_overlay(leaf)
        if leaf%2==0:
            x, y = 0, 0
            self.left_delete_overlay = Gtk.Image.new_from_pixbuf(overlay)
            overlay = self.left_delete_overlay
        else:
            x, y = self.left_canvas.w, 0
            self.right_delete_overlay = Gtk.Image.new_from_pixbuf(overlay)
            overlay = self.right_delete_overlay        
        self.main_layout.put(overlay, x,y)
        overlay.show()

    def remove_overlays(self):
        if self.left_delete_overlay:
            try:
                self.main_layout.remove(self.left_delete_overlay)
            except:
                pass
            finally:
                self.left_delete_overlay = None
        if self.right_delete_overlay:
            try:
                self.main_layout.remove(self.right_delete_overlay)
            except:
                pass
            finally:
                self.right_delete_overlay = None

         #self.main_layout.remove(self.right_background_overlay)
         #self.main_layout.remove(self.left_background_overlay)

    """
    def create_background_overlay(self, leaf):
        if leaf%2==0:
            width, height = self.left_canvas.w, self.left_canvas.h
        else:
            width, height = self.right_canvas.w, self.right_canvas.h

        pb = GdkPixbuf.Pixbuf(GdkPixbuf.Colorspace.RGB,
                            1,
                            8,
                            width,
                            height)
        pixmap = Gdk.Pixmap(None, width, height, 24)
        t_win = pixmap.cairo_create()
        t_win.set_operator(cairo.OPERATOR_CLEAR)
        t_win.set_source_rgba(0.0, 0.0, 0.0, 0.3)
        t_win.set_operator(cairo.OPERATOR_OVER)
        t_win.paint()
        pb.get_from_drawable(pixmap, pixmap.get_colormap(), 0, 0, 0, 0, width, height)
        return pb



    def draw_background_overlay(self, leaf):
        if leaf is None:
            return

        overlay = self.create_background_overlay(leaf)
        if leaf%2==0:
            x, y = 0,0
            self.left_background_overlay = Gtk.image_new_from_pixbuf(overlay)
            overlay = self.left_background_overlay
        else:
            x, y = self.left_canvas.w, 0
            self.right_background_overlay = Gtk.image_new_from_pixbuf(overlay)
            overlay = self.right_background_overlay
        #self.remove_overlays()
        overlay.show()
        self.main_layout.put(overlay, x,y)
        """



    """
    def create_select_overlay(self):
        if self.selected%2==0:
            width, height = self.left_canvas.w, self.left_canvas.h
        else:
            width, height = self.right_canvas.w, self.right_canvas.h
        rect = self.main_layout.get_allocation()
        height = rect[3]-175

        #screen = self.editor.get_screen()
        #sc = screen.get_rgba_colormap()

        pb = GdkPixbuf.Pixbuf(GdkPixbuf.Colorspace.RGB,
                            1,
                            8,
                            width,
                            height)
        pixmap = Gdk.Pixmap(None, width, height, 24)
        t_win = pixmap.cairo_create()
        t_win.set_operator(cairo.OPERATOR_CLEAR)
        t_win.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        t_win.set_operator(cairo.OPERATOR_OVER)
        t_win.paint()
        t_win.set_line_width(10)
        t_win.set_source_rgba(0.0, 1.0, 1.0, 1.0)
        t_win.rectangle(0,0, width, height)
        t_win.stroke()
        pb.get_from_drawable(pixmap, pixmap.get_colormap(), 0, 0, 0, 0, width, height)
        return pb#Gtk.image_new_from_pixbuf(pb)


    def draw_select(self):
        if self.selected is None:
            return
        if self.selected%2==0:
            x, y = 0,0
        else:
            x, y = self.left_canvas.w, 0

        self.remove_selection_overlay()
        self.update_canvas(self.selected)
        overlay = self.create_select_overlay()
        self.selection_overlay = Gtk.image_new_from_pixbuf(overlay)
        self.main_layout.put(self.selection_overlay, x,y)
        self.selection_overlay.show()
        #self.selection_overlay.window.lower()


    def remove_selection_overlay(self):
        try:
            self.main_layout.remove(self.selection_overlay)
        except:
            #print 'failed to remove'
            pass
        try:
            self.selection_overlay.destroy()
            self.selection_overlay = None
        except:
            #print 'failed to destroy'
            pass
            """

    def rotate_selected(self, rot_dir):
        if self.selected is None:
            return
        if rot_dir == self.book.cropBox.rotate_degree[self.selected]:
            return

        orig_w = self.book.raw_image_dimensions[self.selected]['width']
        orig_h = self.book.raw_image_dimensions[self.selected]['height']
        w = self.book.cropBox.image_width[self.selected]
        h = self.book.cropBox.image_height[self.selected]

        print (w, h)
        for crop in ('cropBox','pageCrop','standardCrop','contentCrop'):
            if self.book.crops[crop].box[self.selected].is_valid():
                self.book.crops[crop].box[self.selected].rotate(rot_dir, w, h)
                self.book.crops[crop].box_with_skew_padding[self.selected].rotate(rot_dir, w, h)
                self.book.crops[crop].rotate_degree[self.selected] += rot_dir
                if self.book.crops[crop].rotate_degree[self.selected] == 0:
                    self.book.crops[crop].image_width[self.selected] = orig_w
                    self.book.crops[crop].image_height[self.selected] = orig_h
                else:
                    self.book.crops[crop].image_width[self.selected] = orig_h
                    self.book.crops[crop].image_height[self.selected] = orig_w
        self.set_save_needed(self.selected)
        self.draw_leaf(self.selected)

    def get_subsection(self, image, leaf):
        if self.book.cropBox.box_with_skew_padding[leaf].is_valid():
            x = self.book.cropBox.box_with_skew_padding[leaf].x
            y = self.book.cropBox.box_with_skew_padding[leaf].y
            w = self.book.cropBox.box_with_skew_padding[leaf].w
            h = self.book.cropBox.box_with_skew_padding[leaf].h
        elif self.book.cropBox.box[leaf].is_valid():
            x = self.book.cropBox.box[leaf].x
            y = self.book.cropBox.box[leaf].y
            w = self.book.cropBox.box[leaf].w
            h = self.book.cropBox.box[leaf].h
        else:
            return None

        if leaf%2==0:
            scale_factor = self.left_scale_factor
        else:
            scale_factor = self.right_scale_factor

        subsection = image.new_subpixbuf(int((x/4)/scale_factor),
                                         int((y/4)/scale_factor),
                                         int((w/4)/scale_factor),
                                         int((h/4)/scale_factor))

        return Gtk.Image.new_from_pixbuf(subsection)


    def update_canvas(self, leaf):
        angle = self.get_angle(leaf)
        if leaf%2==0:
            src = self.left_src
            canvas = self.left_canvas
            zones = self.left_zones
            event_box = self.left_event_box
        else:
            src = self.right_src
            canvas = self.right_canvas
            zones = self.right_zones
            event_box = self.right_event_box

        image = self.get_rotated(src, leaf, angle, output='pixbuf')
        self.set_canvas(leaf, image, canvas)
        self.set_event_box(leaf, image, canvas, event_box, zones)
        #if self.selection_overlay is not None:
        #    self.draw_select()
        canvas.image.show()
        if not self.book.cropBox.add_to_access_formats[leaf]:
            self.draw_delete_overlay(leaf)
        #else:
        #    self.draw_background_overlay(leaf)

    def set_canvas(self, leaf, image, canvas):
        if canvas.image:
            try:
                self.main_layout.remove(canvas.image)
            except:
                pass
            finally:
                canvas.image = None
        try:
            self.main_layout.remove(canvas.page_number_box)
        except:
            pass
        
        width, height = image.get_width(), image.get_height()

        if leaf%2==0:
            self.left_canvas.image = \
                self.render_image(image, width, height, 
                                  leaf, self.left_scale_factor)
        
            canvas = self.left_canvas
            canvas.set_dimension('x', 0)
            canvas.set_dimension('y', 0)
            canvas.set_dimension('w', width)
            canvas.set_dimension('h', height)
        else:        
            self.right_canvas.image = \
                self.render_image(image, width, height, 
                                  leaf, self.right_scale_factor)
        
            canvas = self.right_canvas
            canvas.set_dimension('x', self.left_canvas.w)
            canvas.set_dimension('y', 0)
            canvas.set_dimension('w', width)
            canvas.set_dimension('h', height)

        if not self.show_background:
            canvas.image.clear()

        self.main_layout.put(canvas.image, canvas.x, canvas.y)
        canvas.image.show()
        self.draw_page_number(leaf, canvas)

        if leaf %2==0 and self.right_canvas.image is not None:
            self.main_layout.move(self.right_canvas.image,
                                  self.left_canvas.w, self.right_canvas.y)
            self.right_canvas.update_dimension('x', self.left_canvas.w)
            self.main_layout.move(self.right_event_box.image,
                                  self.right_canvas.x + self.right_event_box.x, 
                                  self.right_event_box.y)
            self.right_zones = self.get_zones(self.right_canvas.x + 
                                              self.right_event_box.x, 
                                              self.right_event_box.y,
                                              self.right_event_box.w, 
                                              self.right_event_box.h)
            self.right_event_box.image.hide()

    def draw_page_number(self, leaf, canvas):
        if leaf in self.book.cropBox.pagination:
            number = self.book.cropBox.pagination[leaf]
        if number:
            if re.search('[0-9]+!$', number):
                prefix = 'g'
            elif re.search('[0-9]+\?$', number):
                prefix = 'o'
            elif re.search('[0-9]+', number):
                prefix = 'y'
            images = []
            for char in number:
                if char not in ('!', '?'):
                    img = Environment.current_path + '/gui/pagenumbers/' + \
                        prefix + char + '.png'
                    images.append(img)

            num_w, num_h = 50, 50
            kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                      'visible': True}
            canvas.page_number_box = Gtk.Box(**kwargs)
            canvas.page_number_box.set_size_request(num_w, num_h)
                                               
            for img in images:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(img)
                pixbuf = pixbuf.scale_simple(num_w/2, num_h/2, 
                                             GdkPixbuf.InterpType.NEAREST)
                image = Gtk.Image.new_from_pixbuf(pixbuf)
                canvas.page_number_box.pack_start(image, False, True, 0)
                image.show()
            self.main_layout.put(canvas.page_number_box, canvas.x, canvas.y)

    def set_event_box(self, leaf, image, canvas, event_box, zones):
        if hasattr(event_box, 'image') and event_box.image:
            try:
                self.main_layout.remove(event_box.image)
                #event_box.image.destroy()
            except:
                pass

        width, height = image.get_width(), image.get_height()
        subsection = self.get_subsection(image, leaf)

        if leaf%2==0:
            self.left_event_box = self.get_crop_event_box(subsection, leaf)
            event_box = self.left_event_box
            if subsection is not None:
                self.left_zones = self.get_zones(event_box.x, event_box.y,
                                                 event_box.w, event_box.h)
            else:
                self.left_zones = None
        else:
            self.right_event_box = self.get_crop_event_box(subsection, leaf)
            event_box = self.right_event_box
            if subsection is not None:
                self.right_zones = self.get_zones(canvas.x + event_box.x, event_box.y,
                                                  event_box.w, event_box.h)
            else:
                self.right_zones = None

        if not self.book.cropBox.add_to_access_formats[leaf]:
            event_box.image.hide()
        if subsection:
            self.main_layout.put(event_box.image,
                                 canvas.x + event_box.x,
                                 event_box.y)

    def get_angle(self, leaf):
        if self.book.cropBox.skew_active[leaf]:
            angle = 0-self.book.cropBox.skew_angle[leaf]
        else:
            angle = 0
        if leaf%2==0:
            if self.book.cropBox.rotate_degree[leaf] == 0:
                angle -= 90
            elif self.book.cropBox.rotate_degree[leaf] == 90:
                angle += 180
        else:
            if self.book.cropBox.rotate_degree[leaf] == 0:
                angle += 90
            elif self.book.cropBox.rotate_degree[leaf] == -90:
                angle += 180
        return angle

    def draw_leaf(self, leaf):
        leafnum = "%04d" % leaf
        image_file = (self.book.dirs['book'] + '/' + self.book.identifier + '_scaled/' +
                      self.book.identifier + '_scaled_' + str(leafnum) + '.jpg')

        #image_file = (self.book.dirs['book'] + '/' + self.book.identifier + '_corners_thumbs/' +
        #              self.book.identifier + '_thumb_' + str(leafnum) + '.jpg')

        angle = self.get_angle(leaf)

        if leaf%2==0:
            canvas = self.left_canvas
            event_box = self.left_event_box
            zones = self.left_zones
        else:
            canvas = self.right_canvas
            event_box = self.right_event_box
            zones = self.right_zones

        #if os.path.exists(image_file):
        image = self.get_rotated_scaled_image(image_file, leaf, angle)
        self.set_canvas(leaf, image, canvas)
        self.set_event_box(leaf, image, canvas, event_box, zones)
        if not self.book.cropBox.add_to_access_formats[leaf]:
            self.draw_delete_overlay(leaf)
            #else:
                #self.draw_background_overlay(leaf)

    def draw_spread(self, spread):
        left_leaf = (spread * 2)
        right_leaf = (spread * 2) + 1
        self.draw_leaf(left_leaf)
        self.draw_leaf(right_leaf)

    def get_scaled(self, image_file, scale_factor, output='pixbuf'):
        if os.path.exists(image_file):
            image = GdkPixbuf.Pixbuf.new_from_file(image_file)
            width = image.get_width()
            height = image.get_height()
            #w_scale_factor = float(width) / float(self.editor.window.width - 250)
            #h_scale_factor = float(height) / float(self.editor.window.height - 140)
            #self.scale_factor = w_scale_factor if w_scale_factor > h_scale_factor else h_scale_factor
            image_scaled = image.scale_simple(int(width/scale_factor),
                                              int(height/scale_factor),
                                              GdkPixbuf.InterpType.BILINEAR)
            if output == 'pixbuf':
                return image_scaled
            elif output == 'image':
                return Gtk.image_new_from_pixbuf(image_scaled)

    def get_rotated(self, image, leaf, angle, output='pixbuf'):
        rotated = image.rotate(angle,
                               Image.BILINEAR, expand=True)
        IS_RGBA = rotated.mode=='RGBA'
        if output == 'pixbuf':
            return self.image_to_pixbuf(rotated)
        elif output == 'image':
            return rotated

    def image_to_pixbuf(self, image):
        buf = BytesIO()
        image.save(buf, format='jpeg')
        data = buf.getvalue()
        loader = GdkPixbuf.PixbufLoader.new_with_mime_type('image/jpeg')
        try:
            loader.write(data)
            pixbuf = loader.get_pixbuf()
        except:
            raise
        finally:
            loader.close()
        return pixbuf

    def get_rotated_scaled_image(self, image_file, leaf, angle):
        tmp = Image.open(image_file)
        rotated = tmp.rotate(angle,
                             Image.BILINEAR, expand=True)
        IS_RGBA = tmp.mode=='RGBA'
        image_rotated = self.image_to_pixbuf(rotated)                                                                                                    
        if self.book.cropBox.rotate_degree[leaf] == 0:
            w, h = tmp.size[1], tmp.size[0]
        else:
            w, h = tmp.size[0], tmp.size[1]

        w_scale_factor = float(w) / float((self.editor.window.width - 250)/2)
        h_scale_factor = float(h) / float(self.editor.window.height - 175)

        scale_factor = w_scale_factor if w_scale_factor > h_scale_factor else h_scale_factor

        if leaf%2==0:
            self.left_scale_factor = scale_factor
        else:
            self.right_scale_factor = scale_factor

        image_rotated_scaled = image_rotated.scale_simple(int(rotated.size[0]/scale_factor),
                                                          int(rotated.size[1]/scale_factor),
                                                          GdkPixbuf.InterpType.BILINEAR)

        pixbuf = self.get_scaled(image_file, scale_factor, output='pixbuf')
        src = Image.frombuffer('RGB', (pixbuf.get_width(), pixbuf.get_height()),
                               pixbuf.get_pixels(),
                               'raw',
                               'RGB',
                               pixbuf.get_rowstride(), 1)
        if leaf %2==0:
            self.left_src = src
        else:
            self.right_src = src

        return image_rotated_scaled

    def set_save_needed(self, leaf, affected=None):
        if affected is None: affected = [leaf]
        if leaf%2==0:
            self.save_needed['l'] = leaf, affected
        else:
            self.save_needed['r'] = leaf, affected
        self.save_button.set_sensitive(True)
        #if self.history.has_history(self.selected):
        self.undo_button.set_sensitive(True)
        #else:
        #    self.undo_button.set_sensitive(False)


    def save_changes(self, widget=None, data=None, update_scandata=True):
        left_data = None
        right_data = None
        if self.save_needed['l'][0]:
            leaf = self.save_needed['l'][0]
            left_data = {'leaf': leaf,
                         'affected': {leaf: self.get_current_state(leaf)}}
            for affected_leaf in self.save_needed['l'][1]:
                left_data['affected'][affected_leaf] = self.get_current_state(leaf)
        if self.save_needed['r'][0]:
            leaf = self.save_needed['r'][0]
            right_data = {'leaf': leaf,
                          'affected': {leaf: self.get_current_state(leaf)}}
            for affected_leaf in self.save_needed['r'][1]:
                right_data['affected'][affected_leaf] = self.get_current_state(leaf)
        data = (left_data, right_data)
        if data[0] is not None or data[1] is not None:
            self.history.record_change(data)
            if update_scandata:
                self.update_scandata()
        self.save_needed['l'], self.save_needed['r'] = (False, None), (False, None)
        self.save_button.set_sensitive(False)
        self.released = True
        if self.history.has_history(self.selected):
            self.undo_button.set_sensitive(True)
        else:
            self.undo_button.set_sensitive(False)


    def undo_changes(self, widget=None, data=None):
        if self.selected is None:
            return
        self.released = True
        leaf = self.selected
        current = self.history.state[leaf]['current']
        prev = current - 1
        current_state = self.history.state[leaf]['history'][current]
        for leaf, current_data in current_state.items():
            if prev > self.history.state[leaf]['current']: prev = self.history.state[leaf]['current']-1
            if prev < 0: prev = 0
            undo_data = self.history.state[leaf]['history'][prev]
            for u_leaf, data in undo_data.items():
                for crop in ('cropBox', 'pageCrop', 'standardCrop', 'contentCrop'):
                    if crop in data:
                        self.book.crops[crop].box[leaf] = copy(data[crop]['box'])
                        self.book.crops[crop].box_with_skew_padding[leaf] = copy(data[crop]['box_with_skew_padding'])
                        self.book.crops[crop].active[leaf] = data[crop]['active']
                        self.book.crops[crop].page_type[leaf] = copy(data[crop]['page_type'])
                        self.book.crops[crop].add_to_access_formats[leaf] = copy(data[crop]['add_to_access_formats'])
                        self.book.crops[crop].rotate_degree[leaf] = copy(data[crop]['rotate_degree'])
                        self.book.crops[crop].skew_angle[leaf] = copy(data[crop]['skew_angle'])
                        self.book.crops[crop].skew_conf[leaf] = copy(data[crop]['skew_conf'])
                        self.book.crops[crop].skew_active[leaf] = copy(data[crop]['skew_active'])
                        self.history.state[leaf]['current'] = prev
        self.update_horizontal_control_widgets()
        self.draw_spread(self.current_spread)
        self.update_scandata()
        self.save_button.set_sensitive(False)
        if self.history.has_history(self.selected):
            self.undo_button.set_sensitive(True)
        else:
            self.undo_button.set_sensitive(False)


    def get_current_state(self, leaf):
        return {'cropBox': self.book.cropBox.return_state(leaf),
                'pageCrop': self.book.pageCrop.return_state(leaf),
                'standardCrop': self.book.standardCrop.return_state(leaf),
                'contentCrop': self.book.contentCrop.return_state(leaf)}


    def update_scandata(self):
        for crop in ('pageCrop', 'standardCrop', 'contentCrop', 'cropBox'):
            self.book.crops[crop].xml_io('export')



class MetaEditor(object):

    def __init__(self, editor):
        self.editor = editor
        self.book = editor.book
        kwargs = {'visible': True}
        self.main_layout = Gtk.Layout(**kwargs)
        self.main_layout.set_size_request(self.editor.window.width,
                                          self.editor.window.height)
                                              
        #self.init_main_menu()


    def init_main_menu(self):
        self.main_menu_frame = ca.new_widget('Frame',
                                                 {'size_request': (self.editor.window.width/4, 50),
                                                  'set_shadow_type': Gtk.ShadowType.OUT,
                                                  'show': True})

        self.main_menu_hbox = ca.new_widget('HBox',
                                                {'size_request': (-1, -1),
                                                 'show': True})

        self.meta_custom = ca.new_widget('Button',
                                             {'label': 'Custom',
                                              'show': True})
        self.meta_custom.connect('clicked', self.init_custom)

        self.meta_search = ca.new_widget('Button',
                                             {'label': 'Search',
                                              'show': True})
        self.meta_search.connect('clicked', self.init_search)

        self.main_menu_hbox.pack_start(self.meta_custom, True, True, 0)
        self.main_menu_hbox.pack_start(self.meta_search, True, True, 0)
        self.main_menu_frame.add(self.main_menu_hbox)
        self.main_layout.put(self.main_menu_frame,
                             (self.editor.window.width/2) - (self.editor.window.width/4)/2,
                             (self.editor.window.height/2) - (self.editor.window.height/4)/2)

    def init_custom(self, data):
        pass


    def init_search(self, data):
        pass
        #self.bibs = Bibs()
        #self.main_menu_frame.hide()
        #self.build_view_boxes()
        #self.build_search_box()


    def build_view_boxes(self):
        self.search_vbox = ca.new_widget('VBox',
                                             {'size_request': (int(3*(self.editor.window.width/2)),
                                                               self.editor.window.height),
                                              'show': True})
        self.metadata_vbox = ca.new_widget('VBox',
                                               {'size_request': (int(self.editor.window.width/3),
                                                                 self.editor.window.height),
                                                'show': True})


    def build_search_box(self):
        self.search_bar_box = ca.new_widget('HBox',
                                             {'size_request': (-1, -1),
                                              'show': True})

        self.search_bar = ca.new_widget('Entry',
                                            {'size_request': (self.editor.window.width/2, 50),
                                             'show': True})
        Gtk.rc_parse_string("""style "search-bar-font" { font_name="Sans 20" } class "GtkEntry"  style "search-bar-font" """)

        self.search_button = ca.new_widget('Button',
                                               {'label':'Search',
                                                'size_request': (-1, -1),
                                                'show': True})
        self.search_button.connect('clicked', self.submit_query)

        self.init_search_source()
        self.init_search_api()

        self.results_vbox = ca.new_widget('VBox',
                                              {'size_request': (int(3*(self.editor.window.width/2)),-1),
                                               'show': True})

        self.search_bar_box.pack_start(self.search_bar, False, False, 0)
        self.search_bar_box.pack_start(self.search_button, False, False, 0)
        self.search_bar_box.pack_start(self.search_source, False, False, 0)
        self.search_bar_box.pack_start(self.search_source_api, False, False, 0)
        self.search_vbox.pack_start(self.search_bar_box, False, False, 0)
        self.search_vbox.pack_start(self.results_vbox, True, False, 0)
        self.main_layout.put(self.search_vbox, 0, 0)


    def init_search_source(self):
        self.search_source = Gtk.ComboBoxText()
        self.search_source.show()
        self.bibs.find_sources()
        for filename in self.bibs.source_list:
            name = os.path.basename(filename).split('.yaml')[0]
            self.search_source.insert_text(1, name)
        self.search_source.connect('changed', self.change_source)


    def init_search_api(self):
        self.search_source_api = Gtk.ComboBoxText()
        self.search_source_api.show()


    def change_source(self, data):
        active = self.search_source.get_active_text()
        new_source = self.bibs.get_source(active)
        apis = new_source['api'].keys()
        new_api = new_source['api']['default']['namespace']
        self.set_search_api(new_source, new_api)


    def set_search_api(self, source, api):
        self.search_source_api.insert_text(0, api)
        self.search_source_api.set_active(0)
        for name, a in source['api'].items():
            if name not in (api, 'default'):
                self.search_source_api.insert_text(1, name)

    def submit_query(self, widget):
        source = self.search_source.get_active_text()
        api = self.search_source_api.get_active_text()
        query = self.search_bar.get_text()
        #print source, api
        #results = self.bibs.search(query, source, api)
        #print results
        #self.test_entry.set_text(str(results))


class ExportHandler(object):

    def __init__(self, editor):
        self.editor = editor
        self.book = editor.book
        kwargs = {'visible': True}
        self.main_layout = Gtk.Layout(**kwargs)
        self.main_layout.set_size_request(self.editor.window.width,
                                          self.editor.window.height)
        self.ProcessHandler = ProcessHandling()
        self.build_stack_controls()
        self.build_derivative_controls()
        self.build_global_controls()

    def build_global_controls(self):
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.global_controls = Gtk.Box(**kwargs)
        w, h = int(self.editor.window.width*.95), 50
        self.global_controls.set_size_request(w, h)
        
        kwargs = {'text': '0%',
                  'show_text': True,
                  'visible': True}
        self.global_progress = Gtk.ProgressBar(**kwargs)
        
        kwargs = {'label': 'Run All',
                  'visible': True}
        self.global_derive_button = Gtk.Button(**kwargs)
        self.global_derive_button.set_size_request(100, -1)
        self.global_derive_button.connect('clicked', self.run_all)

        self.global_controls.pack_start(self.global_progress, True, True, 0)
        self.global_controls.pack_start(self.global_derive_button, False, False, 0)
        self.main_layout.put(self.global_controls, 0, self.editor.window.height-50)

    def build_stack_controls(self):
        kwargs = {'visible': True}
        self.stack_controls = Gtk.Layout(**kwargs)
        self.stack_controls.set_size_request(self.editor.window.width/2,
                                             self.editor.window.height-50),
                                             
        kwargs = {'shadow_type': Gtk.ShadowType.NONE,
                  'visible': True}
        self.stack_controls_frame = Gtk.Frame(**kwargs)
        self.stack_controls.set_size_request(self.editor.window.width/2,
                                             self.editor.window.height-50),
                                 
        self.init_cropper()
        self.init_ocr()

        self.stack_controls_frame.add(self.stack_controls)
        self.main_layout.put(self.stack_controls_frame, 0, 0)

    def disable_interface(self):
        self.toggle_pdf(mode=False)
        self.toggle_djvu(mode=False)
        ca.set_all_sensitive((self.init_crop_button,
                              self.init_ocr_button,
                              self.ocr_lang_options,
                              self.derive_button,
                              self.global_derive_button), False)

    def enable_interface(self):
        self.toggle_pdf()
        self.toggle_djvu()
        self.toggle_derive()
        ca.set_all_sensitive((self.init_crop_button,
                              self.init_ocr_button,
                              self.ocr_lang_options,
                              self.global_derive_button), True)

    def init_cropper(self):
        kwargs = {'label': 'Cropper',
                  'shadow_type': Gtk.ShadowType.OUT,
                  'label_xalign': 0.5,
                  'label_yalign': 0.5,
                  'visible': True}
        self.cropper_frame = Gtk.Frame(**kwargs)
        self.cropper_frame.set_size_request(self.editor.window.width/3, -1),
                                            
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.cropper_vbox = Gtk.Box(**kwargs)
        self.cropper_vbox.set_size_request(-1, -1),
                                           
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.controls_hbox = Gtk.Box(**kwargs)
        self.controls_hbox.set_size_request(-1, -1)

        kwargs = {'show_text': True,
                  'text': '0%',
                  'visible': True}
        self.cropper_progress = Gtk.ProgressBar(**kwargs)
        
        kwargs = {'label': 'Initialize Cropper',
                  'visible': True}
        self.init_crop_button = Gtk.Button(**kwargs)
        self.init_crop_button.set_size_request(-1, -1)
        self.init_crop_button.connect('clicked', self.run_cropper)

        self.cropper_vbox.pack_start(self.controls_hbox, True, False, 0)
        self.cropper_vbox.pack_start(self.init_crop_button, True, True, 0)
        self.cropper_vbox.pack_start(self.cropper_progress, True, True, 0)
        self.cropper_frame.add(self.cropper_vbox)
        self.stack_controls.put(self.cropper_frame, 
                                ((self.editor.window.width/4) - 
                                 (self.editor.window.width/3)/2 ), 0)

    def toggle_active_crop(self, widget):
        selection = widget.get_label()
        if selection is not None:
            self.active_crop = selection

    def init_ocr(self):
        kwargs = {'label': 'OCR',
                  'shadow_type': Gtk.ShadowType.OUT,
                  'label_xalign': 0.5,
                  'label_yalign': 0.5,
                  'visible': True}
        self.ocr_frame = Gtk.Frame(**kwargs)
        self.ocr_frame.set_size_request(int(self.editor.window.width*.45), -1)
                                       
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.ocr_vbox = Gtk.Box(**kwargs)
        self.ocr_vbox.set_size_request(-1, -1)
                                      
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.ocr_hbox = Gtk.Box(**kwargs)
        self.ocr_hbox.set_size_request(-1, 50)

        self.language = None
        self.ocr_lang_options = Gtk.ComboBoxText()
        for num, lang in enumerate(Tesseract.languages):
            self.ocr_lang_options.insert_text(int(num), str(lang))
        self.ocr_lang_options.insert_text(0, 'choose a language')
        self.ocr_lang_options.set_active(0)
        self.ocr_lang_options.connect('changed', self.set_language)
        self.ocr_lang_options.show()

        kwargs = {'label': 'Initialize OCR',
                  'sensitive': False,
                  'visible': True}
        self.init_ocr_button = Gtk.Button(**kwargs)
        self.init_ocr_button.connect('clicked', self.run_ocr)

        kwargs = {'label': 'Auto-Spellcheck',
                  'sensitive': False,
                  'visible': True}
        self.ocr_auto_spellcheck = Gtk.RadioButton(**kwargs)
                                                     
        kwargs = {'label': 'Interactive Spellcheck',
                  'group': self.ocr_auto_spellcheck,
                  'sensitive': False,
                  'visible': True}
        self.ocr_interactive_spellcheck = Gtk.RadioButton(**kwargs)
                                   
        kwargs = {'text': '0%',
                  'show_text': True,
                  'visible': True}
        self.ocr_progress = Gtk.ProgressBar(**kwargs)
        
        self.ocr_hbox.pack_start(self.ocr_lang_options, False, True, 0)
        self.ocr_hbox.pack_start(self.init_ocr_button, True, True, 0)
        self.ocr_vbox.pack_start(self.ocr_hbox, True, False, 0)
        self.ocr_vbox.pack_start(self.ocr_progress, True, True, 0)
        self.ocr_frame.add(self.ocr_vbox)
        self.stack_controls.put(self.ocr_frame, 0, 200)

    def build_derivative_controls(self):
        kwargs = {'visible': True}
        self.derivative_controls = Gtk.Layout(**kwargs)
        self.derivative_controls.set_size_request(self.editor.window.width/2,
                                                  self.editor.window.height-50)
                                                      
        kwargs = {'shadow_type': Gtk.ShadowType.NONE,
                  'visible': True}
        self.derivative_controls_frame = Gtk.Frame(**kwargs)
        w, h = int(self.editor.window.width/2)-25, self.editor.window.height-50
        self.derivative_controls_frame.set_size_request(w, h)
                                                            
        self.init_derivatives()

        self.derivative_controls_frame.add(self.derivative_controls)
        self.main_layout.put(self.derivative_controls_frame, w, 0)

    def init_derivatives(self):
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.formats_vbox = Gtk.Box(**kwargs)
        w, h = -1, -1
        self.formats_vbox.set_size_request(w, h)
                                          
        for d in ('pdf', 'djvu', 'epub', 'text'):
            kwargs = {'text': '0%',
                      'show_text': True,
                      'visible': True}
            setattr(self, d+'_progress', Gtk.ProgressBar(**kwargs))

        self.init_pdf()
        self.init_djvu()

        kwargs = {'label': 'EPUB',
                  'visible': True}
        self.derive_epub = Gtk.CheckButton(**kwargs)
                                             
        kwargs = {'label': 'Full Plain Text',
                  'visible': True}
        self.derive_plain_text = Gtk.CheckButton(**kwargs)
        self.derive_plain_text.connect('clicked', self.toggle_plain_text)
    
        kwargs = {'label': 'Initialize Derive',
                  'sensitive': False,
                  'visible': True}
        self.derive_button = Gtk.Button(**kwargs)
        self.derive_button.set_size_request(-1, -1)
                                                
        self.derivatives = {'pdf': (self.derive_pdf, self.return_pdf_args),
                            'djvu': (self.derive_djvu, self.return_djvu_args),
                            'epub': (self.derive_epub, None),
                            'text': (self.derive_plain_text, None)}

        self.derive_button.connect('clicked', self.run_derive)

        self.formats_vbox.pack_start(self.pdf_frame, True, False, padding=15)
        self.formats_vbox.pack_start(self.djvu_frame, True, False, padding=15)

        self.formats_vbox.pack_start(self.derive_epub, True, False, 0)
        self.formats_vbox.pack_start(self.epub_progress, True, False, 0)
        self.formats_vbox.pack_start(self.derive_plain_text, True, False, 0)
        self.formats_vbox.pack_start(self.text_progress, True, False, 0)

        self.formats_vbox.pack_start(self.derive_button, True, False, 0)
        self.derivative_controls.put(self.formats_vbox, 0, 0)

    def toggle_derive(self):
        if self.check_derive_format_selected():
            self.derive_button.set_sensitive(True)
        else:
            self.derive_button.set_sensitive(False)

    def check_derive_format_selected(self):
        if (self.derive_pdf.get_active() or self.derive_djvu.get_active() or
            self.derive_epub.get_active() or self.derive_plain_text.get_active()):
            return True
        else:
            return False

    def init_pdf(self):
        kwargs = {'shadow_type': Gtk.ShadowType.OUT,
                  'visible': True}
        self.pdf_frame = Gtk.Frame(**kwargs)
        self.pdf_frame.set_size_request(-1, 100)
        
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.pdf_vbox = Gtk.Box(**kwargs)
        self.pdf_vbox.set_size_request(-1, -1)
                                      
        kwargs = {'label': 'PDF',
                  'visible': True}
        self.derive_pdf = Gtk.CheckButton(**kwargs)
        self.derive_pdf.connect('clicked', self.toggle_pdf)

        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.pdf_options = Gtk.Box(**kwargs)
        self.pdf_options.set_size_request(-1, -1)
                                         
        kwargs = {'label': 'No Image',
                  'sensitive': False,
                  'visible': True}
        self.pdf_no_image = Gtk.CheckButton(**kwargs)
                                              
        kwargs = {'label': 'Sloppy Text',
                  'sensitive': False,
                  'visible': True}
        self.pdf_sloppy = Gtk.CheckButton(**kwargs)
                                            
        kwargs = {'label': 'PPI',
                  'visible': True}
        ppi_label = Gtk.Label(**kwargs)
        ppi_label.set_size_request(-1, -1)
                                  
        kwargs = {'sensitive': False,
                  'visible': True}
        self.pdf_resolution = Gtk.Entry(**kwargs)
        self.pdf_resolution.set_size_request(40, 25)

        #self.pdf_resolution_buffer = Gtk.TextBuffer()
        #self.pdf_resolution.set_buffer(

        self.pdf_options.pack_start(self.pdf_no_image, True, False, 0)
        self.pdf_options.pack_start(self.pdf_sloppy, True, False, 0)
        self.pdf_options.pack_start(ppi_label, False, False, 0)
        self.pdf_options.pack_start(self.pdf_resolution, True, True, 0)

        self.pdf_vbox.pack_start(self.derive_pdf, False, False, 0)
        self.pdf_vbox.pack_start(self.pdf_options, True, False, 0)
        self.pdf_vbox.pack_start(self.pdf_progress, False, False, 0)
        self.pdf_frame.add(self.pdf_vbox)

    def toggle_pdf(self, widget=None, mode=None):
        if widget is not None:
            self.toggle_derive()

        widgets = (self.pdf_no_image,
                   self.pdf_sloppy,
                   self.pdf_resolution)
        if mode:
            ca.set_all_sensitive(widgets, True)
        elif mode == False:
            ca.set_all_sensitive(widgets, False)
        elif self.derive_pdf.get_active():
            ca.set_all_sensitive(widgets, True)
        elif not self.derive_pdf.get_active():
            ca.set_all_sensitive(widgets, False)

    def return_pdf_args(self):
        return {'no_image': self.pdf_no_image.get_active(),
                'sloppy': self.pdf_sloppy.get_active(),
                'ppi': self.pdf_resolution.get_text()}

    def init_djvu(self):
        kwargs = {'shadow_type': Gtk.ShadowType.OUT,
                  'visible': True}
        self.djvu_frame = Gtk.Frame(**kwargs)
        self.djvu_frame.set_size_request(-1, -1)
                                        
        self.djvu_table = Gtk.Table(4, 4)
        self.djvu_table.show()

        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.djvu_vbox = Gtk.Box(**kwargs)
        self.djvu_vbox.set_size_request(-1, -1)
                                       
        kwargs = {'label': 'DjVu',
                  'visible': True}
        self.derive_djvu = Gtk.CheckButton(**kwargs)
        self.derive_djvu.connect('clicked', self.toggle_djvu)

        kwargs = {'label': 'Slice',
                  'visible': True}
        slice_label = Gtk.Label(**kwargs)
        slice_label.set_size_request(60, -1)

        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_slice = Gtk.Entry(**kwargs)
        self.djvu_slice.set_size_request(100, 25)
                            
        kwargs = {'label': 'Size',
                  'visible': True}
        size_label = Gtk.Label(**kwargs)
        size_label.set_size_request(60, -1)
                                   
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_size = Gtk.Entry(**kwargs)
        self.djvu_size.set_size_request(100, 25)
                                 
        kwargs = {'label': 'Bpp:',
                  'visible': True}
        bpp_label = Gtk.Label(**kwargs)
        bpp_label.set_size_request(60, -1)
                                  
        kwargs = {'text': '', 
                  'sensitive': False,
                  'visible': True}
        self.djvu_bpp = Gtk.Entry(**kwargs)
        self.djvu_bpp.set_size_request(100, 25)
                                           
        kwargs = {'label': 'Percent',
                  'visible': True}
        percent_label = Gtk.Label(**kwargs)
        percent_label.set_size_request(60, -1)
                                           
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_percent = Gtk.Entry(**kwargs)
        self.djvu_percent.set_size_request(100, 25)
                                          
        kwargs = {'label': 'PPI:',
                  'visible': True}
        ppi_label = Gtk.Label(**kwargs)
        ppi_label.set_size_request(60, -1)
                                       
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_ppi = Gtk.Entry(**kwargs)
        self.djvu_ppi.set_size_request(40, 25)
                                      
        kwargs = {'label': 'Gamma:',
                  'visible': True}
        gamma_label = Gtk.Label(**kwargs)
        gamma_label.set_size_request(60, -1)
                               
        kwargs = {'lower': 0.3,
                  'upper': 4.9,
                  'step_increment': 0.1, 
                  'value': 2.2}
        adj = Gtk.Adjustment(**kwargs)

        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'adjustment': adj,
                  'sensitive': False,
                  'digits': 1,
                  'value_pos': Gtk.PositionType.BOTTOM,
                  'visible': True}
        self.djvu_gamma = Gtk.Scale(**kwargs)
        self.djvu_gamma.set_size_request(100, -1)
                                                     
        kwargs = {'label': 'Decibel',
                  'visible': True}
        decibel_label = Gtk.Label(**kwargs)
        decibel_label.set_size_request(60, -1)
                                           
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_decibel = Gtk.Entry(**kwargs)
        self.djvu_decibel.set_size_request(100, 25)
                                                                                              
        kwargs = {'label': 'Fract:',
                  'visible': True}
        fract_label = Gtk.Label(**kwargs)
        fract_label.set_size_request(50, -1)
                                         
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_fract = Gtk.Entry(**kwargs)
        self.djvu_fract.set_size_request(60, 25)
                                             
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.djvu_crcboptions = Gtk.Box(**kwargs)
        self.djvu_crcboptions.set_size_request(-1, -1)
                                                 
        kwargs = {'label': 'CRCB Normal',
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbnorm = Gtk.RadioButton(**kwargs)
                                  
        kwargs = {'label': 'CRCB Half',
                  'group': self.djvu_crcbnorm,
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbhalf = Gtk.RadioButton(**kwargs)
                                               
        kwargs = {'label': 'CRCB Full',
                  'group': self.djvu_crcbnorm,
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbfull = Gtk.RadioButton(**kwargs)
                                               
        kwargs = {'label': 'CRCB None',
                  'group': self.djvu_crcbnorm,
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbnone = Gtk.RadioButton(**kwargs)
                                               
        self.djvu_crcbnorm.set_active(True)

        self.djvu_crcbnorm.connect('toggled', self.toggle_crcb)
        self.djvu_crcbhalf.connect('toggled', self.toggle_crcb)
        self.djvu_crcbfull.connect('toggled', self.toggle_crcb)
        self.djvu_crcbnone.connect('toggled', self.toggle_crcb)

        kwargs = {'label': 'CRCB Delay:',
                  'visible': True}
        crcbdelay_label = Gtk.Label(**kwargs)
        crcbdelay_label.set_size_request(-1, -1)
                                             
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbdelay = Gtk.Entry(**kwargs)
        self.djvu_crcbdelay.set_size_request(60, 25)
                                                 
        self.djvu_table.attach(slice_label, 0, 1, 0, 1)
        self.djvu_table.attach(self.djvu_slice, 1, 2, 0, 1)
        self.djvu_table.attach(size_label, 2, 3, 0, 1)
        self.djvu_table.attach(self.djvu_size, 3, 4, 0, 1)

        self.djvu_table.attach(bpp_label, 0, 1, 1, 2)
        self.djvu_table.attach(self.djvu_bpp, 1, 2, 1, 2)
        self.djvu_table.attach(percent_label, 2, 3, 1, 2)
        self.djvu_table.attach(self.djvu_percent, 3, 4, 1, 2)

        self.djvu_table.attach(ppi_label, 0, 1, 2, 3)
        self.djvu_table.attach(self.djvu_ppi, 1, 2, 2, 3)
        self.djvu_table.attach(gamma_label, 2, 3, 2, 3)
        self.djvu_table.attach(self.djvu_gamma, 3, 4, 2, 3)

        self.djvu_table.attach(decibel_label, 0, 1, 3, 4)
        self.djvu_table.attach(self.djvu_decibel, 1, 2, 3, 4)
        self.djvu_table.attach(fract_label, 2, 3, 3, 4)
        self.djvu_table.attach(self.djvu_fract, 3, 4, 3, 4)

        self.djvu_crcboptions.pack_start(self.djvu_crcbnorm, True, True, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbhalf, True, True, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbfull, True, True, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbnone, True, True, 0)
        self.djvu_crcboptions.pack_start(crcbdelay_label, True, False, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbdelay, True, True, 0)

        self.djvu_vbox.pack_start(self.derive_djvu, False, False, 0)
        self.djvu_vbox.pack_start(self.djvu_table, False, False, 0)
        self.djvu_vbox.pack_start(self.djvu_crcboptions, True, True, 0)
        self.djvu_vbox.pack_start(self.djvu_progress, False, False, 0)

        self.djvu_frame.add(self.djvu_vbox)

    def toggle_crcb(self, widget):
        if self.djvu_crcbnorm.get_active() or self.djvu_crcbhalf.get_active():
            self.djvu_crcbdelay.set_sensitive(True)
        else:
            self.djvu_crcbdelay.set_sensitive(False)

    def toggle_djvu(self, widget=None, mode=None):
        if widget is not None:
            self.toggle_derive()
        widgets = (self.djvu_slice,
                   self.djvu_size,
                   self.djvu_bpp,
                   self.djvu_percent,
                   self.djvu_ppi,
                   self.djvu_gamma,
                   self.djvu_decibel,
                   self.djvu_fract,
                   self.djvu_crcbnorm,
                   self.djvu_crcbhalf,
                   self.djvu_crcbfull,
                   self.djvu_crcbnone,
                   self.djvu_crcbdelay)
        if mode:
            ca.set_all_sensitive(widgets, True)
        elif mode == False:
            ca.set_all_sensitive(widgets, False)
        elif self.derive_djvu.get_active():
            ca.set_all_sensitive(widgets, True)
            self.toggle_crcb(None)
        elif not self.derive_djvu.get_active():
            ca.set_all_sensitive(widgets, False)

    def toggle_plain_text(self, widget=None):
        if widget is not None:
            self.toggle_derive()

    def return_djvu_args(self):
        return {'slice': self.djvu_slice.get_text(),
                'size': self.djvu_size.get_text(),
                'bpp': self.djvu_bpp.get_text(),
                'percent': self.djvu_percent.get_text(),
                'dpi': self.djvu_ppi.get_text(),
                'gamma': self.djvu_gamma.get_value(),
                'decibel': self.djvu_decibel.get_text(),
                'dbfract': self.djvu_fract.get_text(),
                'crcbnorm': self.djvu_crcbnorm.get_active(),
                'crcbhalf': self.djvu_crcbhalf.get_active(),
                'crcbfull': self.djvu_crcbfull.get_active(),
                'crcbnone': self.djvu_crcbnone.get_active(),
                'crcbdelay': self.djvu_crcbdelay.get_text()}

    def set_language(self, widget):
        active = widget.get_active()
        if active == 0:
            self.init_ocr_button.set_sensitive(False)
        else:
            active -= 1
            for num, language in enumerate(Tesseract.languages.items()):
                if active == num:
                    self.language = language[1]
                    self.init_ocr_button.set_sensitive(True)
                    break

    def run_all(self, widget):
        self.disable_interface()
        queue = self.ProcessHandler.new_queue()
        update = []
        fnc = self.ProcessHandler.run_pipeline_distributed

        cls = 'Crop'
        mth = 'cropper_pipeline'
        pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
        queue[pid] = {'func': fnc,
                      'args': [cls, mth, self.book, 
                               None, {'crop': 'cropBox'}],
                      'kwargs': {},
                      'callback': None}
        ca.run_in_background(self.update_progress, 2000, args=('Crop', 'cropper'))
        update.append('cropper')

        if self.language is not None:
            cls = 'OCR'
            mth = 'tesseract_hocr_pipeline'
            pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
            queue[pid] = {'func': fnc,
                          'args': [cls, mth, self.book, 
                                   None, {'lang': self.language}],
                          'kwargs': {},
                          'callback': None}
            ca.run_in_background(self.update_progress, 2000, args=('OCR', 'ocr'))
            update.append('ocr')

        if self.check_derive_format_selected():
            formats = self.get_derive_format_args()
            if 'djvu' in formats:
                cls = 'Djvu'
                mth = 'make_djvu_with_c44'
                pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, self.book, 
                                       None, self.return_djvu_args()],
                              'kwargs': {},
                              'callback': 'assemble_djvu_with_djvm'}
                ca.run_in_background(self.update_progress, 2000, args=('Djvu', 'djvu'))
                update.append('djvu')
            
            if 'pdf' in formats:
                cls = 'PDF'
                mth = 'make_pdf_with_hocr2pdf'
                pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, self.book, 
                                       None, self.return_pdf_args()],
                              'kwargs': {},
                              'callback': 'assemble_pdf_with_pypdf'}
                ca.run_in_background(self.update_progress, 2000, args=('PDF', 'pdf'))
                update.append('pdf')

            if 'text' in formats:
                cls = 'PlainText'
                mth = 'make_full_plain_text'
                pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, self.book, None, None],
                              'kwargs': {},
                              'callback': 'assemble_ocr_text'}
                ca.run_in_background(self.update_progress, 2000, args=('PlainText', 'text'))
                update.append('text')

        self.ProcessHandler.add_process(func=self.ProcessHandler.drain_queue,
                                        pid=self.book.identifier + '_drain_queue',
                                        args=[queue, 'sync'],
                                        kwargs={},
                                        callback=None)
        ca.run_in_background(self.update_run_all_progress, 2000, update)
        
    def update_progress(self, args):
        cls, gui_id = args
        identifier = self.book.identifier
        if not identifier in self.ProcessHandler.OperationObjects:
            return True
        if cls not in self.ProcessHandler.OperationObjects[identifier]:
            return True
        else:
            progress = getattr(self, gui_id + '_progress')
            total = self.book.page_count-2
            state = self.ProcessHandler.get_op_state(self.book, 
                                                     identifier, cls, 
                                                     total)                        
            if state['finished']:
                setattr(self, gui_id + '_fraction', 1.0)
                progress.set_fraction(1.0)
                progress.set_text('100%')
                return False
            else:
                fraction = state['fraction']
                setattr(self, gui_id + '_fraction', fraction)
                progress.set_fraction(fraction)                
                string = str(int(fraction*100)) + '% -- Time Remaining: ' \
                    + str(state['estimated_mins']) + ' mins ' + \
                    str(state['estimated_secs']) + ' secs' 
                progress.set_text(string)
                return True

    def update_run_all_progress(self, update):
        identifier = self.book.identifier
        if not identifier in self.ProcessHandler.OperationObjects:
            return True
        op_obj = self.ProcessHandler.OperationObjects[identifier]
        num_tasks = len(update)
        total_fraction = 0.0
        for op, cls in {'cropper': 'Crop',
                        'ocr': 'OCR',
                        'pdf': 'PDF',
                        'djvu': 'Djvu',
                        'text': 'PlainText'}.items():
            if op in update:
                if not hasattr(self, op+'_fraction'):
                    #if the other update threads have not
                    #finished their first pass then this
                    #won't exist.
                    continue
                if cls in op_obj:
                    state = self.ProcessHandler.get_op_state\
                        (self.book, identifier,
                         cls, self.book.page_count)
                    total_fraction += getattr(self, op+'_fraction')
        total_fraction /= num_tasks
        self.global_progress.set_fraction(total_fraction)
        self.global_progress.set_text(str(int(total_fraction*100)) + '%')
        if total_fraction == 1.0:
            self.enable_interface()
            return False
        else:
            return True

    def run_cropper(self, widget):
        fnc = self.ProcessHandler.run_pipeline_distributed
        cls = 'Crop'
        mth = 'cropper_pipeline'
        pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth ))
        args = [cls, mth, self.book, None, {'crop': 'cropBox'}]
        kwargs = {}
        self.book.start_time = Util.microseconds()
        self.ProcessHandler.add_process(fnc, pid, args, kwargs)  
        ca.run_in_background(self.update_progress, 2000, args=('Crop', 'cropper'))

    def run_ocr(self, widget):
        fnc = self.ProcessHandler.run_pipeline_distributed
        cls = 'OCR'
        mth = 'tesseract_hocr_pipeline'
        pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
        args = [cls, mth, self.book, None, {'lang': self.language}]
        self.ProcessHandler.add_process(fnc, pid, args, {})
        ca.run_in_background(self.update_progress, 2000, args=('OCR', 'ocr'))

    def run_derive(self, widget):
        if self.derive_pdf.get_active():
            self.make_pdf(widget)
        if self.derive_djvu.get_active():
            self.make_djvu(widget)
        if self.derive_plain_text.get_active():
            self.make_plain_text(widget)

    def make_pdf(self, widget):
        fnc = self.ProcessHandler.run_pipeline_distributed
        cls = 'PDF'
        mth = 'make_pdf_with_hocr2pdf'
        pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
        args = [cls, mth, self.book, None, self.return_pdf_args()]
        self.ProcessHandler.add_process(fnc, pid, args, 
                                        {'callback': 'assemble_pdf_with_pypdf'})
        ca.run_in_background(self.update_progress, 2000, args=('PDF', 'pdf'))

    def make_djvu(self, widget):
        fnc = self.ProcessHandler.run_pipeline_distributed
        cls = 'Djvu'
        mth = 'make_djvu_with_c44'
        pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
        args = [cls, mth, self.book, None, self.return_djvu_args()]
        self.ProcessHandler.add_process(fnc, pid, args, 
                                        {'callback': 'assemble_djvu_with_djvm'})
        ca.run_in_background(self.update_progress, 2000, args=('Djvu', 'djvu'))
    
    def make_plain_text(self, widget):
        fnc = self.ProcessHandler.run_pipeline_distributed
        cls = 'PlainText'
        mth = 'make_full_plain_text'
        pid = '.'.join((self.book.identifier, fnc.__name__, cls, mth))
        args = [cls, mth, self.book, None, None]
        self.ProcessHandler.add_process(fnc, pid, args, {'callback': 'assemble_ocr_text'})
        ca.run_in_background(self.update_progress, 2000, args=('PlainText', 'text'))

    def get_derive_format_args(self):
        formats = {}
        for name, attr in self.derivatives.items():
            if attr[0].get_active():
                if attr[1] is not None:
                    formats[name] = attr[1]()
                else:
                    formats[name] = None
        if len(formats) < 1:
            return None
        else:
            return formats
