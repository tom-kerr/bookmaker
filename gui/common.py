import pygtk
pygtk.require("2.0")
import gtk, gobject
gobject.threads_init()

from util import Util


class Common:

    colormap = gtk.Window().get_colormap()


    @staticmethod
    def dialog(parent=None, d_type=gtk.MESSAGE_INFO, message='Error.', Buttons={gtk.STOCK_OK: gtk.RESPONSE_OK}):
        d = gtk.MessageDialog(parent, gtk.DIALOG_DESTROY_WITH_PARENT,  
                              d_type, message_format=message)
        for text, response_id in Buttons.items():
            d.add_button(text, response_id)
        response = d.run()
        d.destroy()
        if response in (gtk.RESPONSE_YES, gtk.RESPONSE_ACCEPT, 
                        gtk.RESPONSE_OK, gtk.RESPONSE_APPLY):
            return True
        elif response in (gtk.RESPONSE_NO, gtk.RESPONSE_REJECT,
                          gtk.RESPONSE_CANCEL, gtk.RESPONSE_CLOSE):
            return False        
        
    
    @staticmethod
    def get_user_selection():
        file_chooser = gtk.FileChooserDialog(title='Select Book Directory',
                                             action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                             buttons=(gtk.STOCK_OPEN, gtk.RESPONSE_APPLY,
                                                      gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        while True:
            response = file_chooser.run()
            if response == gtk.RESPONSE_APPLY:
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
    def new_widget(widget, args=None):
        if widget is None:
            return None
        try:
            if widget == 'Layout': 
                widget = gtk.Layout(None, None)
            elif widget == 'ScrolledWindow':
                widget = gtk.ScrolledWindow(None, None)
            elif widget == 'Notebook':
                widget = gtk.Notebook()
            elif widget == 'HBox':
                widget = gtk.HBox()
            elif widget == 'VBox':
                widget = gtk.VBox()
            elif widget == 'EventBox':
                widget = gtk.EventBox()
            elif widget == 'Label':
                widget = gtk.Label()
            elif widget == 'Frame':
                widget = gtk.Frame()
            elif widget == 'HButtonBox':
                widget = gtk.HButtonBox()
            elif widget == 'Button':
                widget = gtk.Button()
            elif widget == 'RadioButton':
                widget = gtk.RadioButton()
            elif widget == 'CheckButton':
                widget = gtk.CheckButton()
            elif widget == 'Entry':
                widget = gtk.Entry()
            elif widget == 'TextBuffer':
                widget = gtk.TextBuffer()
            elif widget == 'HScale':
                widget = gtk.HScale()
        except:
            return None
            
        if args is not None and len(args) > 0:
                try:
                    Common.set_widget_properties(widget, args)
                except Exception as E:
                    print 'failed to set widget ' + str(widget) + ' properties: ' + str(E)
                    return None
        return widget


    @staticmethod
    def set_widget_properties(widget, properties):
        if widget is None:
            return False
        for property, value in properties.items():
            if property == 'label':
                widget.set_label(value)
            elif property == 'group':
                widget.set_group(value)
            elif property == 'size':
                widget.set_size(value[0], value[1])
                widget.width, widget.height = value[0], value[0]
            elif property == 'size_request':
                widget.set_size_request(value[0], value[1])
                widget.width, widget.height = value[0], value[0]
            elif property == 'color':
                Common.set_color(widget, value)
            elif property == 'set_active':
                widget.set_active(value)
            elif property == 'is_sensitive':
                widget.set_sensitive(value)
            elif property == 'can_set_focus':
                widget.set_can_focus(False)
            elif property == 'set_child_visible':
                widget.set_child_visible(value)
            elif property == 'set_update_policy':
                widget.set_update_policy(value)
            elif property == 'set_value_pos':
                widget.set_value_pos(value)
            elif property == 'set_range':
                widget.set_range(value[0], value[1])
            elif property == 'increments':
                widget.set_increments(value[0], value[1])
            elif property == 'set_digits':
                widget.set_digits(value)
            elif property == 'set_value':
                widget.set_value(value)
            elif property == 'set_text':
                widget.set_text(str(value))
            elif property == 'set_shadow_type':
                widget.set_shadow_type(value)
            elif property == 'set_label_align':
                widget.set_label_align(value[0], value[1])
            elif property == 'append_page':
                for page, label_info in value.items():
                    label = gtk.Label(label_info[0])
                    label.set_size_request(label_info[4][0], label_info[4][1])
                    markup = '<span foreground="'+label_info[1]+'" background="'+label_info[2]+'" size="'+label_info[3] + '">'+label_info[0]+'</span>'
                    label.set_markup(str(markup))
                    widget.append_page(page, label)
            elif property == 'set_tab_position':
                widget.set_tab_pos(value)
            elif property == 'set_single_line_mode':
                widget.set_single_line_mode(value)
            elif property == 'set_border_width':
                widget.set_border_width(value)
            elif property == 'show':
                if value:
                    widget.show()


    @staticmethod
    def set_color(widget, color):
        color = Common.colormap.alloc_color(color)
        style = widget.get_style().copy()
        style.bg[gtk.STATE_NORMAL] = color
        widget.set_style(style)


    @staticmethod
    def get_rotation_constant(rot_dir):
        if rot_dir in (None, 0):
            return gtk.gdk.PIXBUF_ROTATE_NONE
        elif rot_dir == 90:
            return gtk.gdk.PIXBUF_ROTATE_CLOCKWISE
        elif rot_dir == -90:
            return gtk.gdk.PIXBUF_ROTATE_COUNTERCLOCKWISE


    @staticmethod
    def get_crop_radio_selector():
        pageCrop_selector = Common.new_widget('RadioButton',
                                              {'label': 'pageCrop',
                                               'show': True})
        cropBox_selector = Common.new_widget('RadioButton',
                                             {'label': 'cropBox',
                                              'group': pageCrop_selector,
                                              'show': True})
        contentCrop_selector = Common.new_widget('RadioButton',
                                                 {'label': 'contentCrop',
                                                  'group': pageCrop_selector,
                                                  'show': True}) 
        return (pageCrop_selector, cropBox_selector, contentCrop_selector)


    @staticmethod
    def run_in_background(func, milliseconds=100):
        gobject.timeout_add(milliseconds, func)

