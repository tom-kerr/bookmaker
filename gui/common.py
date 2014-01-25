import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GdkPixbuf


class CommonActions(object):

    @staticmethod
    def dialog(parent=None, d_type=Gtk.MessageType.INFO, message='Error.', 
               Buttons={Gtk.STOCK_OK: Gtk.ResponseType.OK},
               get_input=False):
        d = Gtk.MessageDialog(parent, Gtk.DialogFlags.DESTROY_WITH_PARENT,  
                              d_type, message_format=message)
        if get_input:
            entry = Gtk.Entry()
            d.vbox.pack_start(entry, True, True, 0)
            entry.show()

        for text, response_id in Buttons.items():
            d.add_button(text, response_id)
        response = d.run()

        if get_input:
            user_input = entry.get_text()
        d.destroy()
        if response in (Gtk.ResponseType.YES, Gtk.ResponseType.ACCEPT, 
                        Gtk.ResponseType.OK, Gtk.ResponseType.APPLY):
            if get_input:
                return user_input
            else:
                return True
        elif response in (Gtk.ResponseType.NO, Gtk.ResponseType.REJECT,
                          Gtk.ResponseType.CANCEL, Gtk.ResponseType.CLOSE):
            return False        
        else:
            return response
    
    @staticmethod
    def get_user_selection():
        file_chooser = \
            Gtk.FileChooserDialog(title='Select Book Directory',
                                  action=Gtk.FileChooserAction.SELECT_FOLDER,
                                  buttons=(Gtk.STOCK_OPEN, Gtk.ResponseType.APPLY,
                                           Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        while True:
            response = file_chooser.run()
            if response == Gtk.ResponseType.APPLY:
                selected =  file_chooser.get_filename()
                file_chooser.destroy()
                return selected
            else:
                file_chooser.destroy()
                return None
            
    @staticmethod
    def set_window_size(window, width, height):
        if width and height:
            window.resize(width, height)
            window.set_size_request(width, height)
            #w,h = Bookmaker.window.get_size_request()
            window.width, window.height = width, height

    @staticmethod
    def set_all_sensitive(widgets, is_sensitive):
        for widget in widgets:
            widget.set_sensitive(is_sensitive)

    @staticmethod
    def get_rotation_constant(rot_dir):
        if rot_dir in (None, 0):
            return GdkPixbuf.PixbufRotation.NONE
        elif rot_dir == 90:
            return GdkPixbuf.PixbufRotation.CLOCKWISE
        elif rot_dir == -90:
            return GdkPixbuf.PixbufRotation.COUNTERCLOCKWISE

    @staticmethod
    def run_in_background(func, milliseconds=100, args=None):
        if args:
            GObject.timeout_add(milliseconds, func, args)
        else:
            GObject.timeout_add(milliseconds, func)
