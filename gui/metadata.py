import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf
import cairo

from .common import CommonActions as ca

class MetadataGui(object):
    """ Interface for adding metadata to an item 
    """
    def __init__(self, window, book):
        self.window = window
        self.book = book
        kwargs = {'visible': True}
        self.main_layout = Gtk.Layout(**kwargs)
        self.main_layout.set_size_request(self.window.width,
                                          self.window.height)
                                              
        #self.init_main_menu()
        #self.main_layout.show_all()


    def init_main_menu(self):
        self.main_menu_frame = ca.new_widget('Frame',
                                             {'size_request': (self.window.width/4, 50),
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
                             (self.window.width/2) - (self.window.width/4)/2,
                             (self.window.height/2) - (self.window.height/4)/2)

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
                                             {'size_request': (int(3*(self.window.width/2)),
                                                               self.window.height),
                                              'show': True})
        self.metadata_vbox = ca.new_widget('VBox',
                                               {'size_request': (int(self.window.width/3),
                                                                 self.window.height),
                                                'show': True})


    def build_search_box(self):
        self.search_bar_box = ca.new_widget('HBox',
                                             {'size_request': (-1, -1),
                                              'show': True})

        self.search_bar = ca.new_widget('Entry',
                                            {'size_request': (self.window.width/2, 50),
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
                                              {'size_request': (int(3*(self.window.width/2)),-1),
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
