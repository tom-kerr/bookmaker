import sys, os, re, math, time, threading
import multiprocessing
import psutil
from lxml import etree

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk
from gi.repository import GObject
GObject.threads_init()

from util import Util
from environment import Environment
from processing import ProcessHandling
from .common import CommonActions as ca
from .editor import Editor
from .options import Options


class ProcessingGui(object):

    def __init__(self, window):
        self.window = window
        self.window.connect('delete-event', self.quit)
        self.editing = []
        self.books = {}
        self.ProcessHandler = ProcessHandling()
        self.init_main()
        self.init_tasklist()
        self.init_buttons()
        self.init_treeview()
        self.init_window()
        self.window.show_all()

    def quit(self, widget, data):
        if self.ProcessHandler.processes != 0:
            if ca.dialog(None, Gtk.MessageType.QUESTION,
                         'There are processes running, are you sure you want to quit?',
                         {Gtk.STOCK_OK: Gtk.ResponseType.OK,
                          Gtk.STOCK_CANCEL: Gtk.ResponseType.CANCEL}):
                try:                    
                    self.ProcessHandler.finish()
                except Exception as e:
                    ca.dialog(None, Gtk.MessageType.ERROR,
                                  'Failed to stop processes! \nException: ' + str(e),
                                  {Gtk.STOCK_OK: Gtk.ResponseType.OK})
                    return True
                else:
                    return False
            else:
                return True

    def init_main(self):
        kwargs = {'orientation': Gtk.Orientation.VERTICAL}
        self.main = Gtk.Box(**kwargs) 
        self.main.set_size_request(self.window.width, self.window.height)
        
    def init_tasklist(self):
        kwargs = {'border_width': 25}
        self.scroll_window = Gtk.ScrolledWindow(**kwargs)
        self.scroll_window.set_size_request(self.window.width-100, self.window.height)
        self.scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)

    def init_buttons(self):
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL}
        self.button_menu = Gtk.Box(**kwargs)
        self.button_menu.set_size_request(self.window.width, 50)

        kwargs = {'label':'Add',
                  'can_focus': False}
        self.add_button = Gtk.Button(**kwargs)
        self.add_button.set_size_request(100, 25)
        self.add_button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.add_button.connect('button-press-event', self.get_book)

        kwargs = {'label':'Remove',
                  'can_focus': False}
        self.remove_button = Gtk.Button(**kwargs)
        self.remove_button.set_size_request(100, 25)
        self.remove_button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.remove_button.connect('button-press-event', self.remove_book)

        kwargs = {'label':'Options',
                  'can_focus': False}
        self.options_button = Gtk.Button(**kwargs)
        self.options_button.set_size_request(100, 25)
        self.options_button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.options_button.connect('button-press-event', self.open_options)

        kwargs = {'label':'Init',
                  'can_focus': False}
        self.init_button = Gtk.Button(**kwargs)
        self.init_button.set_size_request(100, 25)
        self.init_button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.init_button.connect('button-press-event', self.init_processing)

        kwargs = {'label':'Edit',
                  'can_focus': False,}
        self.edit_button = Gtk.Button(**kwargs)
        self.edit_button.set_size_request(100, 25)
        self.edit_button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.edit_button.connect('button-press-event', self.open_editor)

        self.button_menu.pack_start(self.add_button, True, False, 0)
        self.button_menu.pack_start(self.remove_button, True, False, 0)
        self.button_menu.pack_start(self.options_button, True, False, 0)
        self.button_menu.pack_start(self.init_button, True, False, 0)
        self.button_menu.pack_start(self.edit_button, True, False, 0)

    def init_treeview(self):
        self.model = Gtk.ListStore(str, str, int, str, str, float)
        self.treeview = Gtk.TreeView(self.model)
        self.selector = self.treeview.get_selection()
        self.selector.set_mode(Gtk.SelectionMode.MULTIPLE)
        col = Gtk.TreeViewColumn('Identifier')
        self.treeview.append_column(col)
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=0)
        col = Gtk.TreeViewColumn('Status')
        self.treeview.append_column(col)
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=1)
        col = Gtk.TreeViewColumn('Page Count')
        self.treeview.append_column(col)
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=2)
        col = Gtk.TreeViewColumn('Time Remaining')
        self.treeview.append_column(col)
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=3)
        col = Gtk.TreeViewColumn('Time Elapsed')
        self.treeview.append_column(col)
        cell = Gtk.CellRendererText()
        col.pack_start(cell, True)
        col.set_attributes(cell, text=4)
        col = Gtk.TreeViewColumn('Progress')
        self.treeview.append_column(col)
        cell = Gtk.CellRendererProgress()
        col.pack_start(cell, True)
        col.set_attributes(cell, value=5)
        self.scroll_window.add(self.treeview)

    def init_window(self):
        self.set_system_bar()
        GObject.timeout_add(3000, self.update_system_bar)
        self.main.pack_start(self.scroll_window, True, True, 0)
        self.main.pack_start(self.button_menu, False, False, 0)
        self.main.pack_start(self.sys_bar, False, False, 0)
        self.window.add(self.main)

    def set_system_bar(self):
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL}
        self.sys_bar = Gtk.Box(**kwargs)
        self.sys_bar.set_size_request(-1, 25)
                                     
        self.system_buffer = Gtk.TextBuffer()
        self.system_text = Gtk.TextView.new_with_buffer(self.system_buffer)
        b = self.system_text.get_buffer()
        cpu_usage = psutil.cpu_percent(0.1)
        b.set_text('Cores: ' + str(self.ProcessHandler.cores) +
                   '\t\t Threads: ' + str(self.ProcessHandler.processes) + ' of ' + 
                   str(self.ProcessHandler.cores) +
                   '\t\t CPU Usage: ' + str(cpu_usage) + '%')
        self.system_text.set_size_request(-1, 25)
        self.sys_bar.pack_start(self.system_text, True, False, 0)

    def update_system_bar(self):
        b = self.system_text.get_buffer()
        cpu_usage = psutil.cpu_percent(0.1)
        b.set_text('Cores: ' + str(self.ProcessHandler.cores) +
                   '\t\t Threads: ' + str(self.ProcessHandler.processes) + ' of ' + 
                   str(self.ProcessHandler.cores) +
                   '\t\t CPU Usage: ' + str(cpu_usage) + '%')
        return True

    def get_book(self, widget, data):
        self.add_button.set_child_visible(False)
        selected = ca.get_user_selection()
        if selected is not None:
            self.environment = Environment([selected])
            for book in self.environment.books:
                if book.identifier not in self.books:
                    self.add_book(book)
                else:
                    ca.dialog(None, Gtk.MessageType.INFO,
                                  str(book.identifier) + ' is already in queue...')
        self.add_button.set_child_visible(True)

    def add_book(self, book):
        self.books[book.identifier] = book
        entry = [book.identifier, 'ready', book.page_count, '--', '--', 0.0]
        self.books[book.identifier].entry = self.model.append(entry)

    def get_selected(self):
        selected = []
        model, iters = self.selector.get_selected_rows()
        for iter in iters:
            selected.append(model.get_value(model.get_iter(iter), 0))
        return selected

    #def check_item_state(self, book):


    def remove_book(self, widget, data):
        ids = self.get_selected()
        if ids is None:
            return
        rowiter = None
        for identifier in ids:
            for i, entry in enumerate(self.model):
                for attr in entry:
                    if identifier == attr:
                        rowiter = self.books[identifier].entry
                        break
            if rowiter is not None:
                self.model.remove(rowiter)
                del self.books[identifier]

    def open_editor(self, widget, data):
        identifier = self.get_selected()
        if len(identifier) > 1 or identifier is None:
            return
        identifier = identifier[0]
        if not identifier in self.editing:
            try:
                self.books[identifier].import_crops()
                window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
                window.connect('destroy', self.close_editor, identifier)
                ca.set_window_size(window,
                                   Gdk.Screen.width()-1,
                                   Gdk.Screen.height()-1)
                editor = Editor(window, self.books[identifier])
            except Exception as e:
                ca.dialog(None, Gtk.MessageType.ERROR, str(e))
                return
            self.editing.append(identifier)
            path = self.model.get_path(self.books[identifier].entry)
            self.model[path][1] = 'editing'

    def close_editor(self, widget, identifier):
        self.editing.remove(identifier)
        path = self.model.get_path(self.books[identifier].entry)
        self.model[path][1] = 'ready'

    def open_options(self, widget, data):
        ids = self.get_selected()
        if ids is None:
            return
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        title = 'Processing Options for ' + ', '.join([str(identifier) for identifier in ids])
        window.set_title(title)
        books = {}
        for identifier in ids:
            books[identifier] = self.books[identifier]
        options = Options(window, books)

    def init_processing(self, widget, data):
        ids = self.get_selected()
        if ids is None:
            return

        queue = self.ProcessHandler.new_queue()
        for identifier in ids:
            fnc = self.ProcessHandler.run_pipeline_distributed
            cls = 'FeatureDetection'
            mth = 'pipeline'
            pid = '.'.join((identifier, fnc.__name__, cls, mth))
            
            queue[pid] = {'func': fnc,
                          'args': [cls, mth, self.books[identifier], None, None],
                          'kwargs': {},
                          'callback': 'post_process'}

            fnc = self.ProcessHandler.drain_queue
            logger = self.books[identifier].logger
            pid = '.'.join((identifier, fnc.__name__))
            args = [queue, 'sync']
            kwargs = {'qpid': identifier, 
                      'qlogger': logger}
            if self.ProcessHandler.add_process(fnc, pid, args, kwargs, logger):
                self.books[identifier].start_time = Util.microseconds()
                path = self.model.get_path(self.books[identifier].entry)
                self.model[path][1] = 'processing'
                self.follow_progress(identifier)
            else:
                self.wait(identifier)

    def wait(self, identifier):
        path = self.model.get_path(self.books[identifier].entry)
        self.model[path][1] = 'waiting...'

    def follow_progress(self, identifier):
        GObject.timeout_add(300, self.update_progress, identifier)

    def update_progress(self, identifier):
        if identifier not in self.books:
            return False
        if not identifier in self.ProcessHandler.item_queue:
            path = self.model.get_path(self.books[identifier].entry)            
            if (identifier + '_main' in self.ProcessHandler.handled_exceptions or
                identifier + '_featuredetection' in self.ProcessHandler.handled_exceptions):
                self.model[path][1] = 'ERROR'
                self.model[path][3] = '--'
                #self.model[path][4] = '--'
                
            if not 'FeatureDetection' in (self.ProcessHandler.OperationObjects[identifier]):
                return True
            op_obj = self.ProcessHandler.OperationObjects[identifier]['FeatureDetection']
            op_num = len(op_obj.completed)
            completed = 0
            avg_exec_time = 0
            for op, leaf_t in op_obj.completed.items():
                c = len(leaf_t)
                completed += c
                if c > 0:
                    avg_exec_time += op_obj.get_avg_exec_time(op)
            if completed == 0:
                return True
            avg_exec_time = avg_exec_time/op_num
            fraction = float(completed) / (float(self.books[identifier].page_count) * op_num)
            remaining_page_count = (self.books[identifier].page_count * op_num) - completed
            estimated_secs = int(avg_exec_time * remaining_page_count)
            estimated_mins = int(estimated_secs/60)
            estimated_secs -= estimated_mins * 60
            self.model[path][3] = str(estimated_mins) + ' min ' + str(estimated_secs) + 'sec'

            current_time = time.time()
            elapsed_secs = int(current_time - self.books[identifier].start_time)
            elapsed_mins = int(elapsed_secs/60)
            elapsed_secs -= elapsed_mins * 60
            self.model[path][4] = str(elapsed_mins) + ' min ' + str(elapsed_secs) + 'sec'

            self.model[path][5] = fraction*100
            if fraction == 1.0:
                self.model[path][1] = 'finished'
                return False
        return True
