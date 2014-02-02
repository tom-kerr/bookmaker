import os, sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from environment import Environment
from .common import CommonActions as ca


class Options(object):
    
    def __init__(self, window, books):
        self.window = window
        self.books = books
        self.build_selector()
        self.window.add(self.main_layout)
        self.window.show_all()

    def build_selector(self):
        ca.set_window_size(self.window, 450, 250)
        self.main_layout = Gtk.Layout(visible=True)
        kwargs = {'orientation': Gtk.Orientation.VERTICAL, 
                  'visible': True}
        self.vbox = Gtk.Box(**kwargs)
        self.vbox.set_size_request(self.window.width, -1)
        self.radio_buttons = {}
        for identifier, book in self.books.items():
            for setting, value in book.settings.items():
                self.radio_buttons[setting] = {}
                kwargs = {'orientation': Gtk.Orientation.HORIZONTAL, 
                          'visible': True}
                self.radio_buttons[setting]['hbox'] = Gtk.Box(**kwargs)
                buff = Gtk.TextBuffer()
                self.radio_buttons[setting]['text'] = Gtk.TextView.new_with_buffer(buff)
                self.radio_buttons[setting]['text'].set_size_request(self.window.width/3 ,-1)
                buff.set_text(str(setting))
            
                kwargs = {'label': 'True',
                          'group': None,
                          'visible': True}
                self.radio_buttons[setting][1] = Gtk.RadioButton(**kwargs)

                kwargs = {'label': 'False',
                          'group': self.radio_buttons[setting][1],
                          'visible': True}
                self.radio_buttons[setting][0] = Gtk.RadioButton(**kwargs)
            
                if value is True:
                    self.radio_buttons[setting][1].set_active(True)
                else:
                    self.radio_buttons[setting][0].set_active(True)

                self.radio_buttons[setting][1].connect('toggled', self.modify_setting, setting)
                self.radio_buttons[setting][0].connect('toggled', self.modify_setting, setting)

                self.radio_buttons[setting]['hbox'].pack_start(self.radio_buttons[setting]['text'], True, True, 0)
                self.radio_buttons[setting]['hbox'].pack_start(self.radio_buttons[setting][1], True, True, 0)
                self.radio_buttons[setting]['hbox'].pack_start(self.radio_buttons[setting][0], True, True, 0)
                self.vbox.pack_start(self.radio_buttons[setting]['hbox'], True, True, 0)
            #only the first book's settings are used to set the gui
            #but all books are affected by changes made
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
                Environment.write_settings(book, book.settings)
