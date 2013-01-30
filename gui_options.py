import os, sys
import pygtk
pygtk.require("2.0")
import gtk
from gui_common import Common
from environment import Environment

class Options:
    
    def __init__(self, window, books):
        self.window = window
        self.books = books
        self.build_selector()
        self.window.add(self.main_layout)
        self.window.show_all()


    def build_selector(self):
        Common.set_window_size(self.window, 450, 210)
        self.main_layout = gtk.Layout(None, None)
        self.vbox = gtk.VBox()
        self.vbox.set_size_request(self.window.width, -1)
        self.radio_buttons = {}
        for identifier, book in self.books.items():
            for setting, value in book.settings.items():
                self.radio_buttons[setting] = {}
                self.radio_buttons[setting]['hbox'] = gtk.HBox()
                buff = gtk.TextBuffer()
                self.radio_buttons[setting]['text'] = gtk.TextView(buff)
                self.radio_buttons[setting]['text'].set_size_request(self.window.width/3 ,-1)
                buff.set_text(str(setting))
            
                self.radio_buttons[setting][1] = gtk.RadioButton(group=None, label='True')
                self.radio_buttons[setting][0] = gtk.RadioButton(self.radio_buttons[setting][1], label='False')
            
                if value is True:
                    self.radio_buttons[setting][1].set_active(True)
                else:
                    self.radio_buttons[setting][0].set_active(True)

                self.radio_buttons[setting][1].connect('toggled', self.modify_setting, setting)
                self.radio_buttons[setting][0].connect('toggled', self.modify_setting, setting)

                self.radio_buttons[setting]['hbox'].pack_start(self.radio_buttons[setting]['text'])
                self.radio_buttons[setting]['hbox'].pack_start(self.radio_buttons[setting][1])
                self.radio_buttons[setting]['hbox'].pack_start(self.radio_buttons[setting][0])
                self.vbox.pack_start(self.radio_buttons[setting]['hbox'])
            break
        self.main_layout.put(self.vbox, 0, 0)


    def modify_setting(self, widget, setting):
        if widget.get_active():
            label = widget.get_label()
            if label == 'True':
                value = True
            elif label == 'False':
                value = False
            for identifier, book in self.books.items():
                book.settings[setting] = value
                Environment.write_settings(book.root_dir, book.settings)
