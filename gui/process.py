import sys, os, re, math, time, threading
import multiprocessing
import psutil
from lxml import etree
import pygtk
pygtk.require("2.0")
import gtk
import gobject
gobject.threads_init()

from environment import Environment
from processing import ProcessHandler
from common import Common
from editor import Editor
from options import Options


class Process():

    def __init__(self, window):
        self.window = window
        self.window.connect('delete-event', self.quit)
        self.cmap = window.get_colormap()
        self.editing = []
        self.books = {}
        self.ProcessHandler = ProcessHandler()
        self.init_main()
        self.init_tasklist()
        self.init_buttons()
        self.init_treeview()
        self.init_window()
        self.window.show_all()


    def quit(self, widget, data):
        if self.ProcessHandler.processes != 0:
            if Common.dialog(None, gtk.MESSAGE_QUESTION,
                             'There are processes running, are you sure you want to quit?',
                             {gtk.STOCK_OK: gtk.RESPONSE_OK,
                              gtk.STOCK_CANCEL: gtk.RESPONSE_CANCEL}):
                try:
                    self.ProcessHandler.finish()
                except Exception as e:
                    Common.dialog(None, gtk.MESSAGE_ERROR,
                                  'Failed to stop processes! \nException: ' + str(e),
                                  {gtk.STOCK_OK: gtk.RESPONSE_OK})
                    return True
                else:
                    return False
            else:
                return True


    def init_main(self):
        self.main = Common.new_widget('VBox', 
                                      {'size_request': (self.window.width, self.window.height)})
        

    def init_tasklist(self):
        self.scroll_window = Common.new_widget('ScrolledWindow',
                                               {'size_request': (self.window.width-100, self.window.height),
                                                'set_border_width':25,
                                                'color':'gray'})
        self.scroll_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        

    def init_buttons(self):
        self.button_menu = Common.new_widget('HBox', 
                                             {'size_request': (self.window.width, 50)})

        self.add_button = Common.new_widget('Button', 
                                            {'label':'Add',
                                             'size_request':(100, 25),
                                             'set_can_focus': False,
                                             'color':'darkgray'})
        self.add_button.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.add_button.connect('button-press-event', self.get_book)

        self.remove_button = Common.new_widget('Button', 
                                               {'label':'Remove',
                                                'size_request':(100, 25),
                                                'set_can_focus': False,
                                                'color':'darkgray'})
        self.remove_button.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.remove_button.connect('button-press-event', self.remove_book)

        self.options_button = Common.new_widget('Button', 
                                                {'label':'Options',
                                                 'size_request':(100, 25),
                                                 'set_can_focus': False,
                                                 'color':'darkgray'})
        self.options_button.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.options_button.connect('button-press-event', self.open_options)
                
        self.init_button = Common.new_widget('Button', 
                                             {'label':'Init',
                                              'size_request':(100, 25),
                                              'set_can_focus': False,
                                              'color':'darkgray'})
        self.init_button.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.init_button.connect('button-press-event', self.init_processing)
                
        self.edit_button = Common.new_widget('Button', 
                                             {'label':'Edit',
                                              'size_request':(100, 25),
                                              'set_can_focus': False,
                                              'color':'darkgray'})
        self.edit_button.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.edit_button.connect('button-press-event', self.open_editor)

        self.button_menu.pack_start(self.add_button, expand=True, fill=False)
        self.button_menu.pack_start(self.remove_button, expand=True, fill=False)
        self.button_menu.pack_start(self.options_button, expand=True, fill=False)
        self.button_menu.pack_start(self.init_button, expand=True, fill=False)
        self.button_menu.pack_start(self.edit_button, expand=True, fill=False)

    
    def init_treeview(self):
        self.model = gtk.ListStore(str, str, int, str, str, float) 
        self.treeview = gtk.TreeView(self.model)
        self.selector = self.treeview.get_selection()
        self.selector.set_mode(gtk.SELECTION_MULTIPLE)
        col = gtk.TreeViewColumn('Identifier')
        self.treeview.append_column(col)
        cell = gtk.CellRendererText()
        col.pack_start(cell)
        col.set_attributes(cell, text=0)
        col = gtk.TreeViewColumn('Status')
        self.treeview.append_column(col)
        cell = gtk.CellRendererText()
        col.pack_start(cell)
        col.set_attributes(cell, text=1)
        col = gtk.TreeViewColumn('Page Count')
        self.treeview.append_column(col)
        cell = gtk.CellRendererText()
        col.pack_start(cell)
        col.set_attributes(cell, text=2)
        col = gtk.TreeViewColumn('Time Remaining')
        self.treeview.append_column(col)
        cell = gtk.CellRendererText()
        col.pack_start(cell)
        col.set_attributes(cell, text=3)
        col = gtk.TreeViewColumn('Time Elapsed')
        self.treeview.append_column(col)
        cell = gtk.CellRendererText()
        col.pack_start(cell)
        col.set_attributes(cell, text=4)
        col = gtk.TreeViewColumn('Progress')
        self.treeview.append_column(col)
        cell = gtk.CellRendererProgress()
        col.pack_start(cell)
        col.set_attributes(cell, value=5)
        self.scroll_window.add(self.treeview)


    def init_window(self):
        self.set_system_bar()
        gobject.timeout_add(3000, self.update_system_bar)
        self.main.pack_start(self.scroll_window, expand=True, fill=True)
        self.main.pack_start(self.button_menu, expand=False, fill=False)
        self.main.pack_start(self.sys_bar, expand=False, fill=False)
        self.window.add(self.main)
        
        
    def set_system_bar(self):
        self.sys_bar = Common.new_widget('HBox',
                                         {'size_request': (-1, 25),
                                          'color':'black'})
        self.system_buffer = gtk.TextBuffer()
        self.system_text = gtk.TextView(self.system_buffer)
        b = self.system_text.get_buffer()
        cpu_usage = psutil.cpu_percent(0.1)
        b.set_text('Cores: ' + str(self.ProcessHandler.cores) + 
                   '\t\t Threads: ' + str(self.ProcessHandler.processes) + ' of ' + str(self.ProcessHandler.cores) + 
                   '\t\t CPU Usage: ' + str(cpu_usage) + '%')
        self.system_text.set_size_request(-1, 25)
        self.sys_bar.pack_start(self.system_text, expand=True, fill=False)        
        

    def update_system_bar(self):
        b = self.system_text.get_buffer()
        cpu_usage = psutil.cpu_percent(0.1)
        b.set_text('Cores: ' + str(self.ProcessHandler.cores) + 
                   '\t\t Threads: ' + str(self.ProcessHandler.processes) + ' of ' + str(self.ProcessHandler.cores) + 
                   '\t\t CPU Usage: ' + str(cpu_usage) + '%')
        return True


    def get_book(self, widget, data):
        self.add_button.set_child_visible(False)
        selected = Common.get_user_selection()
        if selected is not None:
            self.environment = Environment([selected])
            for book in self.environment.books:
                if book.identifier not in self.books:
                    self.add_book(book)
                else:
                    Common.dialog(None, gtk.MESSAGE_INFO, 
                                  str(book.identifier) + ' is already in queue...')
        self.add_button.set_child_visible(True)


    def add_book(self, book):
        self.books[book.identifier] = book
        entry = [book.identifier, 'ready', book.page_count, '--', '--', 0]
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
            self.books[identifier].import_crops()
            window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            window.connect('destroy', self.close_editor, identifier)
            Common.set_window_size(window,
                                   gtk.gdk.screen_width()-1,
                                   gtk.gdk.screen_height()-1)
            editor = Editor(window, self.books[identifier])
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
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        title = 'Processing Options for ' + ', '.join([`identifier` for identifier in ids]) 
        window.set_title(title)
        books = {}
        for identifier in ids:
            books[identifier] = self.books[identifier]
        options = Options(window, books)
        

    def init_processing(self, widget, data):
        ids = self.get_selected()
        if ids is None:
            return
        rowiter = None
        for identifier in ids:
            if self.ProcessHandler.add_process(self.ProcessHandler.run_main, 
                                               identifier, self.books[identifier],
                                               self.books[identifier].logger):
                path = self.model.get_path(self.books[identifier].entry)
                self.model[path][1] = 'processing'
                self.follow_progress(identifier)
    

    def wait(self, identifier):
        path = self.model.get_path(self.books[identifier].entry)
        self.model[path][1] = 'waiting...'
        

    def follow_progress(self, identifier):
        gobject.timeout_add(300, self.update_progress, identifier)

            
    def update_progress(self, identifier):        
        #proc_id = self.ProcessHandler.check_thread_exceptions()
        #if proc_id:
        #    print proc_id
        #    self.ProcessHandler.destroy_thread(proc_id)

        if not identifier in self.ProcessHandler.item_queue:            
            path = self.model.get_path(self.books[identifier].entry)
            completed = len(self.ProcessHandler.FeatureDetection.ImageOps.completed_ops)
            fraction = float(completed) / float(self.books[identifier].page_count)  

            avg_exec_time = self.ProcessHandler.FeatureDetection.ImageOps.avg_exec_time
            remaining_page_count = self.books[identifier].page_count - completed
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
            #line = self.books[identifier].logs['global'].readline()
            #if line:
            #    path = self.model.get_path(self.books[identifier].entry)
            #    if re.search('[0-9a-zA-Z]', line):
            #        match = re.search('total exec time for leaf [0-9]+', line)
            #        if match:
            #            leaf = re.search('[0-9]+', match.group(0))
            #            fraction = float(leaf.group(0)) / float(self.books[identifier].page_count)  
            #            self.model[path][3] = fraction*100                                            
            #        match = re.search('Finished in [\.0-9]+ minutes', line)
            #        if match:
            #            self.model[path][1] = 'finished'
            #            self.model[path][3] = 100
            #            return False
        else:
            self.wait(identifier)
        return True
