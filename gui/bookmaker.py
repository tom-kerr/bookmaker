import sys, os, re
from lxml import etree
import pygtk
pygtk.require("2.0")
import gtk

from environment import Environment, BookData, Logger
from datastructures import Crop

from common import Common
from process import Process
from editor import Editor


class Bookmaker:

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
        gtk.main()


    def init_window(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)        
        self.window.set_title('Main Menu')
        Bookmaker.colormap = self.window.get_colormap()
        self.window.connect('delete-event', gtk.main_quit)
        self.window.show()


    def return_to_op_toggle(self, widget):
        self.window.show_all()
        

    def set_operation_toggle(self):
        self.op_toggle = gtk.VBox()
        capture_button = gtk.Button(label='capture')
        #capture_button.set_can_focus(False)
        #capture_button.set_sensitive(False)
        capture_handle = capture_button.connect('clicked', self.capture_book)
        self.op_toggle.pack_start(capture_button, expand=True, fill=True)
        process_button = gtk.Button(label='process')
        process_handle = process_button.connect('clicked', self.process_book)
        self.op_toggle.pack_start(process_button, expand=True, fill=True)
        edit_button = gtk.Button(label='edit')
        edit_handle = edit_button.connect('clicked', self.edit_book)
        self.op_toggle.pack_start(edit_button, expand=True, fill=True)
        self.window.add(self.op_toggle)
        

    def capture_book(self, widget):
        Common.dialog(None, gtk.MESSAGE_INFO, 
                      'can\'t do this yet...', 
                      {gtk.STOCK_OK: gtk.RESPONSE_OK})


    def process_book(self, widget):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        window.set_title('Processing Queue')
        window.connect('destroy', self.return_to_op_toggle)
        Common.set_window_size(window,
                               (2*gtk.gdk.screen_width())/3, 
                               (2*gtk.gdk.screen_height())/3)
        self.process = Process(window)
        self.window.hide()


    def edit_book(self, widget, window=None, selected=None):
        if selected is None:
            selected = Common.get_user_selection()
            if not selected:
                return
        if window is None:
            window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
            window.connect('destroy', self.return_to_op_toggle)
            raw_data = self.select_book(selected, 'edit')
            if raw_data:
                book_data = BookData(selected, raw_data)
                book_data.logger = Logger()
                Environment.set_logs(book_data, 'a')
                try:
                    book_data.import_crops()
                except Exception as e:
                    Common.dialog(None, gtk.MESSAGE_ERROR, str(e))
                    return
                Common.set_window_size(window,
                                       gtk.gdk.screen_width()-1,
                                       gtk.gdk.screen_height()-25)
            #try:
            self.editor = Editor(window, book_data)
            #except Exception as E:
            #    d = gtk.MessageDialog(message_format=str(E))
            #    d.run()
            #    return
            self.window.hide()

        
    def select_book(self, item, op):
        data = Environment.is_sane(item)
        if data:
            return data
        else:
            Common.dialog(None, gtk.MESSAGE_ERROR, 
                          str(item) + ' does not exist!', 
                          {gtk.STOCK_OK: gtk.RESPONSE_OK})
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
                Common.dialog(None, gtk.MESSAGE_ERROR, 
                              'Did not find essential item ' + str(essential),
                              {gtk.STOCK_OK: gtk.RESPONSE_OK})
                return False
        return True
            
