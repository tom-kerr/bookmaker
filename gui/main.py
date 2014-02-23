import sys, os, re

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GObject

from environment import Environment, BookData

from .common import CommonActions as ca
from .process import ProcessingGui
from .editor import Editor


class BookmakerGUI:

    essential = {'raw':      {'regex': '[_raw_jpg$]'},
                 'scandata': {'regex': '[_scandata.xml$]'},
                 'thumb':    {'regex': '[_thumbs$]'} 
                 }

    def __init__(self):
        Environment.interface = 'gui'
        Environment.set_current_path()
        self.init_window()
        self.set_operation_toggle()
        self.window.show_all()
        self.run()        

    def run(self):
        GObject.threads_init()
        Gtk.main()

    def init_window(self):
        self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)        
        self.window.set_title('Main Menu')
        #Bookmaker.colormap = self.window.get_colormap()
        self.window.connect('delete-event', Gtk.main_quit)
        self.window.show()

    def return_to_op_toggle(self, widget):
        self.window.show_all()        

    def set_operation_toggle(self):
        self.op_toggle = Gtk.VBox()
        capture_button = Gtk.Button(label='capture')
        #capture_button.set_can_focus(False)
        #capture_button.set_sensitive(False)
        capture_handle = capture_button.connect('clicked', self.capture_book)
        self.op_toggle.pack_start(capture_button, True, True, 0)
        process_button = Gtk.Button(label='process')
        process_handle = process_button.connect('clicked', self.process_book)
        self.op_toggle.pack_start(process_button, True, True, 0)
        edit_button = Gtk.Button(label='edit')
        edit_handle = edit_button.connect('clicked', self.edit_book)
        self.op_toggle.pack_start(edit_button, True, True, 0)
        self.window.add(self.op_toggle)
        
    def capture_book(self, widget):
        ca.dialog(None, Gtk.MessageType.INFO, 
                      'can\'t do this yet...', 
                      {Gtk.STOCK_OK: Gtk.ResponseType.OK})

    def process_book(self, widget):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        window.set_title('Processing Queue')
        window.connect('destroy', self.return_to_op_toggle)
        ca.set_window_size(window,
                               (2*Gdk.Screen.width())/3, 
                               (2*Gdk.Screen.height())/3)
        self.processing_gui = ProcessingGui(window)
        self.window.hide()

    def edit_book(self, widget, window=None, selected=None):
        if selected is None:
            selected = ca.get_user_selection()
            if not selected:
                return
        if window is None:
            window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
            window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
            window.connect('destroy', self.return_to_op_toggle)
            raw_dir, raw_data = self.select_book(selected, 'edit')
            if raw_data:
                book_data = BookData(selected, raw_dir, raw_data)
                Environment.init_logger(book_data)
                try:
                    book_data.import_crops()
                except Exception as e:
                    ca.dialog(None, Gtk.MessageType.ERROR, str(e))
                    return
                ca.set_window_size(window,
                                   int(Gdk.Screen.width()-40),
                                   int(Gdk.Screen.height()-50))
            #try:
            self.editor = Editor(window, book_data)
            #except Exception as E:
            #    d = Gtk.MessageDialog(message_format=str(E))
            #    d.run()
            #    return
            self.window.hide()
        
    def select_book(self, root_dir, op):
        raw_dir = Environment.is_sane(root_dir)
        if raw_dir:
            raw_data = Environment.get_raw_data(root_dir, raw_dir)
            return (raw_dir, raw_data)
        else:
            ca.dialog(None, Gtk.MessageType.ERROR, 
                      str(root_dir) + ' does not exist!', 
                      {Gtk.STOCK_OK: Gtk.ResponseType.OK})
        return False

    def book_is_valid(self, selected, op):
        contents = os.listdir(selected)
        if op is 'process':
            required = ('raw')
        elif op is 'edit':
            required = ('raw','scandata','thumb')
        for essential, attr in Bookmaker.essential.items():
            if essential not in required:
                continue
            exists = False
            pattern = essential + attr['regex']
            for item in contents:        
                m = re.search(pattern, item)
                if m is not None:
                    exists = True
                    break
            if exists is False:
                ca.dialog(None, Gtk.MessageType.ERROR, 
                              'Did not find essential item ' + str(essential),
                              {Gtk.STOCK_OK: Gtk.ResponseType.OK})
                return False
        return True
            
