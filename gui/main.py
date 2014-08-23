""" GUI entry point
"""

import sys, os, re

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GObject

from environment import Environment, Book; Environment('gui')

from processing import ProcessHandling
from core.capture import ImageCapture
from components.gphoto2 import Gphoto2
from .common import CommonActions as ca
from .capture import CaptureGui
from .process import ProcessingGui
from .editor import EditorGui
from .metadata import MetadataGui
from .export import ExportGui

class BookmakerGui:

    def __init__(self):
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
        self.window.connect('delete-event', Gtk.main_quit)
        self.window.show()

    def return_to_op_toggle(self, widget):
        self.window.show_all()        

    def set_operation_toggle(self):
        self.op_toggle = Gtk.VBox()
        capture_button = Gtk.Button(label='Capture')
        capture_handle = capture_button.connect('clicked', self.capture_book)
        self.op_toggle.pack_start(capture_button, True, True, 0)
        process_button = Gtk.Button(label='Process')
        process_handle = process_button.connect('clicked', self.process_book)
        self.op_toggle.pack_start(process_button, True, True, 0)
        edit_button = Gtk.Button(label='Edit')
        edit_handle = edit_button.connect('clicked', self.edit_book)
        self.op_toggle.pack_start(edit_button, True, True, 0)
        meta_button = Gtk.Button(label='Metadata')
        meta_handle = meta_button.connect('clicked', self.add_metadata)
        self.op_toggle.pack_start(meta_button, True, True, 0)
        derive_button = Gtk.Button(label='Export')
        derive_handle = derive_button.connect('clicked', self.derive)
        self.op_toggle.pack_start(derive_button, True, True, 0)
        self.window.add(self.op_toggle)
        
    def capture_book(self, widget):
        book = None
        new = ca.dialog(message='What would you like to do?', 
                        Buttons=[('Create New Project', 0),
                                 ('Open Existing Project', 1),
                                 ('cancel', 2)])
        if new == 2:
            return
        if new == 0:
            try:
                book = self.create_new_book()
                if not book:
                    return
            except (IOError, OSError) as e:
                ca.dialog(message=str(e))
                return
        else:
            root_dir = ca.get_user_selection()
            if not root_dir:
                return
            try:
                books = Environment.get_books(root_dir, None, 
                                              stage='append_capture')
            except (Exception, BaseException) as e:
                ca.dialog(None, Gtk.MessageType.ERROR, str(e))
                return
            if not books:
                ca.dialog(None, Gtk.MessageType.ERROR, 
                          str(root_dir) + ' is not a valid bookmaker directory!')                          
                return
            elif len(books) > 1:
                ca.dialog(None, Gtk.MessageType.ERROR, 
                          'Cannot edit multiple books. Please refine your selection.')                          
                return
        book = books[0]
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        window.set_title('Image Capture')
        window.connect('destroy', self.return_to_op_toggle)
        ca.set_window_size(window,Gdk.Screen.width()*.95, 
                           Gdk.Screen.height()*.95)
        ProcessHandler = ProcessHandling()
        try:
            IC = ImageCapture(ProcessHandler, book)
        except Warning as e:
            ca.dialog(None, Gtk.MessageType.WARNING, str(e))
        except (Exception, BaseException) as e:
            ca.dialog(None, Gtk.MessageType.ERROR, str(e))
            return
        ProcessHandler.add_operation_instance(IC, book)
        self.capture_gui = CaptureGui(window, book, ProcessHandler, IC)
        self.window.hide()

    def create_new_book(self):
        capture_style = ca.dialog(message='Please Select a capture style:', 
                                  Buttons=[('Single Camera', 1),
                                           ('Dual Cameras', 2)])
        if capture_style == 1:
            capture_style = 'Single'
        else:
            capture_style = 'Dual'
        identifier = ca.dialog(message='Please name this project:', 
                               Buttons=[(Gtk.STOCK_OK, Gtk.ResponseType.OK),
                                        (Gtk.STOCK_CANCEL, Gtk.ResponseType.NO)],
                               get_input=True)
        if not identifier:
            return False
        location = ca.get_user_selection(title='Please choose a location for this project:')
        if not location:
            return False
        while os.path.exists(location + '/' + identifier):
            identifier = ca.dialog(message='Sorry, a project by that name already exists. '+
                                   'Please try another name:', get_input=True)
            if not identifier:
                return False
            location = ca.get_user_selection(title='Please choose a location for this project:')
            if not location:
                return False
        Environment.create_new_book_stub(location, identifier)
        return Environment.get_books(location + '/' + identifier, 
                                     None,
                                     stage='new_capture', 
                                     capture_style=capture_style)
        
    def process_book(self, widget):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        window.set_title('Processing Queue')
        window.connect('destroy', self.return_to_op_toggle)
        ca.set_window_size(window,
                           (2*Gdk.Screen.width())/3, 
                           (2*Gdk.Screen.height())/3)
        ProcessHandler = ProcessHandling()
        self.processing_gui = ProcessingGui(window, ProcessHandler)
        self.window.hide()

    def edit_book(self, widget):
        root_dir = ca.get_user_selection()
        if not root_dir:
            return
        try:
            books = Environment.get_books(root_dir, None, 'edit')
        except (Exception, BaseException) as e:
            ca.dialog(None, Gtk.MessageType.ERROR, str(e))
            return
        if not books:
            ca.dialog(None, Gtk.MessageType.ERROR, 
                      str(root_dir) + ' is not a valid bookmaker directory!')
            return
        elif len(books) > 1:
            ca.dialog(None, Gtk.MessageType.ERROR, 
                      'Cannot edit multiple books. Please refine your selection.')
            return
        book = books[0]
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        window.connect('destroy', self.return_to_op_toggle)
        ca.set_window_size(window,
                           int(Gdk.Screen.width()-40),
                           int(Gdk.Screen.height()-50))
        try:
            self.editor = EditorGui(window, book)
        except (Exception, BaseException) as e:
            ca.dialog(None, Gtk.MessageType.ERROR, str(e))
            return
        self.window.hide()

    def add_metadata(self, widget):
        pass

    def derive(self, wiget):
        root_dir = ca.get_user_selection()
        if not root_dir:
            return
        try:
            books = Environment.get_books(root_dir, None, 'edit')
        except (Exception, BaseException) as e:
            ca.dialog(None, Gtk.MessageType.ERROR, str(e))
            return
        if not books:
            ca.dialog(None, Gtk.MessageType.ERROR, 
                      str(root_dir) + ' is not a valid bookmaker directory!')
            return
        elif len(books) > 1:
            ca.dialog(None, Gtk.MessageType.ERROR, 
                      'Cannot edit multiple books. Please refine your selection.')
            return
        book = books[0]
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        window.connect('destroy', self.return_to_op_toggle)
        ca.set_window_size(window,
                           int(Gdk.Screen.width()-40),
                           int(Gdk.Screen.height()-50))
        try:
            self.export = ExportGui(window, book)
        except (Exception, BaseException) as e:
            ca.dialog(None, Gtk.MessageType.ERROR, str(e))
            return
        self.window.hide()

            
