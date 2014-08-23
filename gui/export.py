import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf
import cairo

from processing import ProcessHandling
from components.tesseract import Tesseract
from .common import CommonActions as ca


class ExportGui(object):
    """ Interface for creating derivative formats
    """
    def __init__(self, window, book):
        self.window = window
        self.window.connect('delete-event', self.quit)
        self.book = book
        kwargs = {'visible': True}
        self.main_layout = Gtk.Layout(**kwargs)
        self.main_layout.set_size_request(self.window.width,
                                          self.window.height)
        self.ProcessHandler = ProcessHandling()
        self.build_stack_controls()
        self.build_derivative_controls()
        self.build_global_controls()
        self.window.add(self.main_layout)
        self.window.show()

    def quit(self, widget, data):
        if (self.ProcessHandler._are_active_processes()):
            if ca.dialog(None, Gtk.MessageType.QUESTION,
                         'There are processes running, '+
                         'are you sure you want to quit?',
                         [(Gtk.STOCK_OK, Gtk.ResponseType.OK),
                          (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)]):
                self.ProcessHandler.abort(exception=RuntimeError('User aborted operations.'))
        
    def build_global_controls(self):
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.global_controls = Gtk.Box(**kwargs)
        w, h = int(self.window.width*.95), 50
        self.global_controls.set_size_request(w, h)
        
        kwargs = {'text': '0%',
                  'show_text': True,
                  'visible': True}
        self.global_progress = Gtk.ProgressBar(**kwargs)
        
        kwargs = {'label': 'Run All',
                  'visible': True}
        self.global_derive_button = Gtk.Button(**kwargs)
        self.global_derive_button.set_size_request(100, -1)
        self.global_derive_button.connect('clicked', self.run_all)

        self.global_controls.pack_start(self.global_progress, True, True, 0)
        self.global_controls.pack_start(self.global_derive_button, False, False, 0)
        self.main_layout.put(self.global_controls, 0, self.window.height-50)

    def build_stack_controls(self):
        kwargs = {'visible': True}
        self.stack_controls = Gtk.Layout(**kwargs)
        self.stack_controls.set_size_request(self.window.width/2,
                                             self.window.height-50),
                                             
        kwargs = {'shadow_type': Gtk.ShadowType.NONE,
                  'visible': True}
        self.stack_controls_frame = Gtk.Frame(**kwargs)
        self.stack_controls.set_size_request(self.window.width/2,
                                             self.window.height-50),
                                 
        self.init_cropper()
        self.init_ocr()

        self.stack_controls_frame.add(self.stack_controls)
        self.main_layout.put(self.stack_controls_frame, 0, 0)

    def disable_interface(self):
        self.toggle_pdf(mode=False)
        self.toggle_djvu(mode=False)
        ca.set_all_sensitive((self.init_crop_button,
                              self.init_ocr_button,
                              self.ocr_lang_options,
                              self.derive_button,
                              self.global_derive_button), False)

    def enable_interface(self):
        self.toggle_pdf()
        self.toggle_djvu()
        self.toggle_derive()
        ca.set_all_sensitive((self.init_crop_button,
                              self.init_ocr_button,
                              self.ocr_lang_options,
                              self.global_derive_button), True)

    def init_cropper(self):
        kwargs = {'label': 'Cropper',
                  'shadow_type': Gtk.ShadowType.OUT,
                  'label_xalign': 0.5,
                  'label_yalign': 0.5,
                  'visible': True}
        self.cropper_frame = Gtk.Frame(**kwargs)
        self.cropper_frame.set_size_request(self.window.width/3, -1),
                                            
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.cropper_vbox = Gtk.Box(**kwargs)
        self.cropper_vbox.set_size_request(-1, -1),
                                           
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.controls_hbox = Gtk.Box(**kwargs)
        self.controls_hbox.set_size_request(-1, -1)

        kwargs = {'show_text': True,
                  'text': '0%',
                  'visible': True}
        self.cropper_progress = Gtk.ProgressBar(**kwargs)
        
        kwargs = {'label': 'Initialize Cropper',
                  'visible': True}
        self.init_crop_button = Gtk.Button(**kwargs)
        self.init_crop_button.set_size_request(-1, -1)
        self.init_crop_button.connect('clicked', self.run_cropper)

        self.cropper_vbox.pack_start(self.controls_hbox, True, False, 0)
        self.cropper_vbox.pack_start(self.init_crop_button, True, True, 0)
        self.cropper_vbox.pack_start(self.cropper_progress, True, True, 0)
        self.cropper_frame.add(self.cropper_vbox)
        self.stack_controls.put(self.cropper_frame, 
                                ((self.window.width/4) - 
                                 (self.window.width/3)/2 ), 0)

    def toggle_active_crop(self, widget):
        selection = widget.get_label()
        if selection is not None:
            self.active_crop = selection

    def init_ocr(self):
        kwargs = {'label': 'OCR',
                  'shadow_type': Gtk.ShadowType.OUT,
                  'label_xalign': 0.5,
                  'label_yalign': 0.5,
                  'visible': True}
        self.ocr_frame = Gtk.Frame(**kwargs)
        self.ocr_frame.set_size_request(int(self.window.width*.45), -1)
                                       
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.ocr_vbox = Gtk.Box(**kwargs)
        self.ocr_vbox.set_size_request(-1, -1)
                                      
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.ocr_hbox = Gtk.Box(**kwargs)
        self.ocr_hbox.set_size_request(-1, 50)

        self.language = None
        self.ocr_lang_options = Gtk.ComboBoxText()
        for num, lang in enumerate(Tesseract.languages):
            self.ocr_lang_options.insert_text(int(num), str(lang))
        self.ocr_lang_options.insert_text(0, 'choose a language')
        self.ocr_lang_options.set_active(0)
        self.ocr_lang_options.connect('changed', self.set_language)
        self.ocr_lang_options.show()

        kwargs = {'label': 'Initialize OCR',
                  'sensitive': False,
                  'visible': True}
        self.init_ocr_button = Gtk.Button(**kwargs)
        self.init_ocr_button.connect('clicked', self.run_ocr)

        kwargs = {'label': 'Auto-Spellcheck',
                  'sensitive': False,
                  'visible': True}
        self.ocr_auto_spellcheck = Gtk.RadioButton(**kwargs)
                                                     
        kwargs = {'label': 'Interactive Spellcheck',
                  'group': self.ocr_auto_spellcheck,
                  'sensitive': False,
                  'visible': True}
        self.ocr_interactive_spellcheck = Gtk.RadioButton(**kwargs)
                                   
        kwargs = {'text': '0%',
                  'show_text': True,
                  'visible': True}
        self.ocr_progress = Gtk.ProgressBar(**kwargs)
        
        self.ocr_hbox.pack_start(self.ocr_lang_options, False, True, 0)
        self.ocr_hbox.pack_start(self.init_ocr_button, True, True, 0)
        self.ocr_vbox.pack_start(self.ocr_hbox, True, False, 0)
        self.ocr_vbox.pack_start(self.ocr_progress, True, True, 0)
        self.ocr_frame.add(self.ocr_vbox)
        self.stack_controls.put(self.ocr_frame, 0, 200)

    def build_derivative_controls(self):
        kwargs = {'visible': True}
        self.derivative_controls = Gtk.Layout(**kwargs)
        self.derivative_controls.set_size_request(self.window.width/2,
                                                  self.window.height-50)
                                                      
        kwargs = {'shadow_type': Gtk.ShadowType.NONE,
                  'visible': True}
        self.derivative_controls_frame = Gtk.Frame(**kwargs)
        w, h = int(self.window.width/2)-25, self.window.height-50
        self.derivative_controls_frame.set_size_request(w, h)
                                                            
        self.init_derivatives()

        self.derivative_controls_frame.add(self.derivative_controls)
        self.main_layout.put(self.derivative_controls_frame, w, 0)

    def init_derivatives(self):
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.formats_vbox = Gtk.Box(**kwargs)
        w, h = -1, -1
        self.formats_vbox.set_size_request(w, h)
                                          
        for d in ('pdf', 'djvu', 'epub', 'text'):
            kwargs = {'text': '0%',
                      'show_text': True,
                      'visible': True}
            setattr(self, d+'_progress', Gtk.ProgressBar(**kwargs))

        self.init_pdf()
        self.init_djvu()

        kwargs = {'label': 'EPUB',
                  'visible': True}
        self.derive_epub = Gtk.CheckButton(**kwargs)
        self.derive_epub.connect('clicked', self.toggle_epub)
                                             
        kwargs = {'label': 'Full Plain Text',
                  'visible': True}
        self.derive_plain_text = Gtk.CheckButton(**kwargs)
        self.derive_plain_text.connect('clicked', self.toggle_plain_text)
    
        kwargs = {'label': 'Initialize Derive',
                  'sensitive': False,
                  'visible': True}
        self.derive_button = Gtk.Button(**kwargs)
        self.derive_button.set_size_request(-1, -1)
                                                
        self.derivatives = {'pdf': (self.derive_pdf, self.return_pdf_args),
                            'djvu': (self.derive_djvu, self.return_djvu_args),
                            'epub': (self.derive_epub, None),
                            'text': (self.derive_plain_text, None)}

        self.derive_button.connect('clicked', self.run_derive)

        self.formats_vbox.pack_start(self.pdf_frame, True, False, padding=15)
        self.formats_vbox.pack_start(self.djvu_frame, True, False, padding=15)

        self.formats_vbox.pack_start(self.derive_epub, True, False, 0)
        self.formats_vbox.pack_start(self.epub_progress, True, False, 0)
        self.formats_vbox.pack_start(self.derive_plain_text, True, False, 0)
        self.formats_vbox.pack_start(self.text_progress, True, False, 0)

        self.formats_vbox.pack_start(self.derive_button, True, False, 0)
        self.derivative_controls.put(self.formats_vbox, 0, 0)

    def toggle_derive(self):
        if self.check_derive_format_selected():
            self.derive_button.set_sensitive(True)
        else:
            self.derive_button.set_sensitive(False)

    def check_derive_format_selected(self):
        if (self.derive_pdf.get_active() or self.derive_djvu.get_active() or
            self.derive_epub.get_active() or self.derive_plain_text.get_active()):
            return True
        else:
            return False

    def init_pdf(self):
        kwargs = {'shadow_type': Gtk.ShadowType.OUT,
                  'visible': True}
        self.pdf_frame = Gtk.Frame(**kwargs)
        self.pdf_frame.set_size_request(-1, 100)
        
        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.pdf_vbox = Gtk.Box(**kwargs)
        self.pdf_vbox.set_size_request(-1, -1)
                                      
        kwargs = {'label': 'PDF',
                  'visible': True}
        self.derive_pdf = Gtk.CheckButton(**kwargs)
        self.derive_pdf.connect('clicked', self.toggle_pdf)

        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.pdf_options = Gtk.Box(**kwargs)
        self.pdf_options.set_size_request(-1, -1)
                                         
        kwargs = {'label': 'No Image',
                  'sensitive': False,
                  'visible': True}
        self.pdf_no_image = Gtk.CheckButton(**kwargs)
                                              
        kwargs = {'label': 'Sloppy Text',
                  'sensitive': False,
                  'visible': True}
        self.pdf_sloppy = Gtk.CheckButton(**kwargs)
                                            
        kwargs = {'label': 'PPI',
                  'visible': True}
        ppi_label = Gtk.Label(**kwargs)
        ppi_label.set_size_request(-1, -1)
                                  
        kwargs = {'sensitive': False,
                  'visible': True}
        self.pdf_resolution = Gtk.Entry(**kwargs)
        self.pdf_resolution.set_size_request(40, 25)

        #self.pdf_resolution_buffer = Gtk.TextBuffer()
        #self.pdf_resolution.set_buffer(

        self.pdf_options.pack_start(self.pdf_no_image, True, False, 0)
        self.pdf_options.pack_start(self.pdf_sloppy, True, False, 0)
        self.pdf_options.pack_start(ppi_label, False, False, 0)
        self.pdf_options.pack_start(self.pdf_resolution, True, True, 0)

        self.pdf_vbox.pack_start(self.derive_pdf, False, False, 0)
        self.pdf_vbox.pack_start(self.pdf_options, True, False, 0)
        self.pdf_vbox.pack_start(self.pdf_progress, False, False, 0)
        self.pdf_frame.add(self.pdf_vbox)

    def toggle_pdf(self, widget=None, mode=None):
        if widget is not None:
            self.toggle_derive()

        widgets = (self.pdf_no_image,
                   self.pdf_sloppy,
                   self.pdf_resolution)
        if mode:
            ca.set_all_sensitive(widgets, True)
        elif mode == False:
            ca.set_all_sensitive(widgets, False)
        elif self.derive_pdf.get_active():
            ca.set_all_sensitive(widgets, True)
        elif not self.derive_pdf.get_active():
            ca.set_all_sensitive(widgets, False)

    def return_pdf_args(self):
        return {'no_image': self.pdf_no_image.get_active(),
                'sloppy': self.pdf_sloppy.get_active(),
                'ppi': self.pdf_resolution.get_text()}

    def init_djvu(self):
        kwargs = {'shadow_type': Gtk.ShadowType.OUT,
                  'visible': True}
        self.djvu_frame = Gtk.Frame(**kwargs)
        self.djvu_frame.set_size_request(-1, -1)
                                        
        self.djvu_table = Gtk.Table(4, 4)
        self.djvu_table.show()

        kwargs = {'orientation': Gtk.Orientation.VERTICAL,
                  'visible': True}
        self.djvu_vbox = Gtk.Box(**kwargs)
        self.djvu_vbox.set_size_request(-1, -1)
                                       
        kwargs = {'label': 'DjVu',
                  'visible': True}
        self.derive_djvu = Gtk.CheckButton(**kwargs)
        self.derive_djvu.connect('clicked', self.toggle_djvu)

        kwargs = {'label': 'Slice',
                  'visible': True}
        slice_label = Gtk.Label(**kwargs)
        slice_label.set_size_request(60, -1)

        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_slice = Gtk.Entry(**kwargs)
        self.djvu_slice.set_size_request(100, 25)
                            
        kwargs = {'label': 'Size',
                  'visible': True}
        size_label = Gtk.Label(**kwargs)
        size_label.set_size_request(60, -1)
                                   
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_size = Gtk.Entry(**kwargs)
        self.djvu_size.set_size_request(100, 25)
                                 
        kwargs = {'label': 'Bpp:',
                  'visible': True}
        bpp_label = Gtk.Label(**kwargs)
        bpp_label.set_size_request(60, -1)
                                  
        kwargs = {'text': '', 
                  'sensitive': False,
                  'visible': True}
        self.djvu_bpp = Gtk.Entry(**kwargs)
        self.djvu_bpp.set_size_request(100, 25)
                                           
        kwargs = {'label': 'Percent',
                  'visible': True}
        percent_label = Gtk.Label(**kwargs)
        percent_label.set_size_request(60, -1)
                                           
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_percent = Gtk.Entry(**kwargs)
        self.djvu_percent.set_size_request(100, 25)
                                          
        kwargs = {'label': 'PPI:',
                  'visible': True}
        ppi_label = Gtk.Label(**kwargs)
        ppi_label.set_size_request(60, -1)
                                       
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_ppi = Gtk.Entry(**kwargs)
        self.djvu_ppi.set_size_request(40, 25)
                                      
        kwargs = {'label': 'Gamma:',
                  'visible': True}
        gamma_label = Gtk.Label(**kwargs)
        gamma_label.set_size_request(60, -1)
                               
        kwargs = {'lower': 0.3,
                  'upper': 4.9,
                  'step_increment': 0.1, 
                  'value': 2.2}
        adj = Gtk.Adjustment(**kwargs)

        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'adjustment': adj,
                  'sensitive': False,
                  'digits': 1,
                  'value_pos': Gtk.PositionType.BOTTOM,
                  'visible': True}
        self.djvu_gamma = Gtk.Scale(**kwargs)
        self.djvu_gamma.set_size_request(100, -1)
                                                     
        kwargs = {'label': 'Decibel',
                  'visible': True}
        decibel_label = Gtk.Label(**kwargs)
        decibel_label.set_size_request(60, -1)
                                           
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_decibel = Gtk.Entry(**kwargs)
        self.djvu_decibel.set_size_request(100, 25)
                                                                                              
        kwargs = {'label': 'Fract:',
                  'visible': True}
        fract_label = Gtk.Label(**kwargs)
        fract_label.set_size_request(50, -1)
                                         
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_fract = Gtk.Entry(**kwargs)
        self.djvu_fract.set_size_request(60, 25)
                                             
        kwargs = {'orientation': Gtk.Orientation.HORIZONTAL,
                  'visible': True}
        self.djvu_crcboptions = Gtk.Box(**kwargs)
        self.djvu_crcboptions.set_size_request(-1, -1)
                                                 
        kwargs = {'label': 'CRCB Normal',
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbnorm = Gtk.RadioButton(**kwargs)
                                  
        kwargs = {'label': 'CRCB Half',
                  'group': self.djvu_crcbnorm,
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbhalf = Gtk.RadioButton(**kwargs)
                                               
        kwargs = {'label': 'CRCB Full',
                  'group': self.djvu_crcbnorm,
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbfull = Gtk.RadioButton(**kwargs)
                                               
        kwargs = {'label': 'CRCB None',
                  'group': self.djvu_crcbnorm,
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbnone = Gtk.RadioButton(**kwargs)
                                               
        self.djvu_crcbnorm.set_active(True)

        self.djvu_crcbnorm.connect('toggled', self.toggle_crcb)
        self.djvu_crcbhalf.connect('toggled', self.toggle_crcb)
        self.djvu_crcbfull.connect('toggled', self.toggle_crcb)
        self.djvu_crcbnone.connect('toggled', self.toggle_crcb)

        kwargs = {'label': 'CRCB Delay:',
                  'visible': True}
        crcbdelay_label = Gtk.Label(**kwargs)
        crcbdelay_label.set_size_request(-1, -1)
                                             
        kwargs = {'text': '',
                  'sensitive': False,
                  'visible': True}
        self.djvu_crcbdelay = Gtk.Entry(**kwargs)
        self.djvu_crcbdelay.set_size_request(60, 25)
                                                 
        self.djvu_table.attach(slice_label, 0, 1, 0, 1)
        self.djvu_table.attach(self.djvu_slice, 1, 2, 0, 1)
        self.djvu_table.attach(size_label, 2, 3, 0, 1)
        self.djvu_table.attach(self.djvu_size, 3, 4, 0, 1)

        self.djvu_table.attach(bpp_label, 0, 1, 1, 2)
        self.djvu_table.attach(self.djvu_bpp, 1, 2, 1, 2)
        self.djvu_table.attach(percent_label, 2, 3, 1, 2)
        self.djvu_table.attach(self.djvu_percent, 3, 4, 1, 2)

        self.djvu_table.attach(ppi_label, 0, 1, 2, 3)
        self.djvu_table.attach(self.djvu_ppi, 1, 2, 2, 3)
        self.djvu_table.attach(gamma_label, 2, 3, 2, 3)
        self.djvu_table.attach(self.djvu_gamma, 3, 4, 2, 3)

        self.djvu_table.attach(decibel_label, 0, 1, 3, 4)
        self.djvu_table.attach(self.djvu_decibel, 1, 2, 3, 4)
        self.djvu_table.attach(fract_label, 2, 3, 3, 4)
        self.djvu_table.attach(self.djvu_fract, 3, 4, 3, 4)

        self.djvu_crcboptions.pack_start(self.djvu_crcbnorm, True, True, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbhalf, True, True, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbfull, True, True, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbnone, True, True, 0)
        self.djvu_crcboptions.pack_start(crcbdelay_label, True, False, 0)
        self.djvu_crcboptions.pack_start(self.djvu_crcbdelay, True, True, 0)

        self.djvu_vbox.pack_start(self.derive_djvu, False, False, 0)
        self.djvu_vbox.pack_start(self.djvu_table, False, False, 0)
        self.djvu_vbox.pack_start(self.djvu_crcboptions, True, True, 0)
        self.djvu_vbox.pack_start(self.djvu_progress, False, False, 0)

        self.djvu_frame.add(self.djvu_vbox)

    def toggle_crcb(self, widget):
        if self.djvu_crcbnorm.get_active() or self.djvu_crcbhalf.get_active():
            self.djvu_crcbdelay.set_sensitive(True)
        else:
            self.djvu_crcbdelay.set_sensitive(False)

    def toggle_djvu(self, widget=None, mode=None):
        if widget is not None:
            self.toggle_derive()
        widgets = (self.djvu_slice,
                   self.djvu_size,
                   self.djvu_bpp,
                   self.djvu_percent,
                   self.djvu_ppi,
                   self.djvu_gamma,
                   self.djvu_decibel,
                   self.djvu_fract,
                   self.djvu_crcbnorm,
                   self.djvu_crcbhalf,
                   self.djvu_crcbfull,
                   self.djvu_crcbnone,
                   self.djvu_crcbdelay)
        if mode:
            ca.set_all_sensitive(widgets, True)
        elif mode == False:
            ca.set_all_sensitive(widgets, False)
        elif self.derive_djvu.get_active():
            ca.set_all_sensitive(widgets, True)
            self.toggle_crcb(None)
        elif not self.derive_djvu.get_active():
            ca.set_all_sensitive(widgets, False)

    def toggle_plain_text(self, widget=None):
        if widget is not None:
            self.toggle_derive()

    def toggle_epub(self, widget=None):
        if widget is not None:
            self.toggle_derive()

    def return_djvu_args(self):
        return {'slice': self.djvu_slice.get_text(),
                'size': self.djvu_size.get_text(),
                'bpp': self.djvu_bpp.get_text(),
                'percent': self.djvu_percent.get_text(),
                'dpi': self.djvu_ppi.get_text(),
                'gamma': self.djvu_gamma.get_value(),
                'decibel': self.djvu_decibel.get_text(),
                'dbfract': self.djvu_fract.get_text(),
                'crcbnorm': self.djvu_crcbnorm.get_active(),
                'crcbhalf': self.djvu_crcbhalf.get_active(),
                'crcbfull': self.djvu_crcbfull.get_active(),
                'crcbnone': self.djvu_crcbnone.get_active(),
                'crcbdelay': self.djvu_crcbdelay.get_text()}

    def set_language(self, widget):
        active = widget.get_active()
        if active == 0:
            self.init_ocr_button.set_sensitive(False)
        else:
            active -= 1
            for num, language in enumerate(Tesseract.languages.items()):
                if active == num:
                    self.language = language[1]
                    self.init_ocr_button.set_sensitive(True)
                    break

    def run_all(self, widget):
        self.disable_interface()
        queue = self.ProcessHandler.new_queue()
        update = []
        
        queue.add(self.book, cls='Crop', mth='cropper_pipeline', 
                  kwargs={'crop': 'cropBox'})
        ca.run_in_background(self.update_progress, 2000, args=('Crop', 'cropper'))
        update.append('cropper')

        if self.language is not None:
            queue.add(self.book, cls='OCR', mth='tesseract_hocr_pipeline',
                      kwargs={'lang': self.language})            
            ca.run_in_background(self.update_progress, 2000, args=('OCR', 'ocr'))
            update.append('ocr')

        if self.check_derive_format_selected():
            formats = self.get_derive_format_args()
            if 'djvu' in formats:
                queue.add(self.book, cls='Djvu', mth='make_djvu_with_c44', 
                          kwargs=self.return_djvu_args())
                ca.run_in_background(self.update_progress, 2000, args=('Djvu', 'djvu'))
                update.append('djvu')
            
            if 'pdf' in formats:
                queue.add(self.book, cls='PDF', mth='make_pdf_with_hocr2pdf', 
                          kwargs=self.return_pdf_args())
                ca.run_in_background(self.update_progress, 2000, args=('PDF', 'pdf'))
                update.append('pdf')
            
            if 'epub' in formats:
                queue.add(self.book, cls='EPUB', mth='make_epub')
                ca.run_in_background(self.update_progress, 2000, args=('EPUB', 'epub'))
                update.append('epub')

            if 'text' in formats:
                queue.add(self.book, cls='PlainText', mth='make_full_plain_text')
                ca.run_in_background(self.update_progress, 2000, args=('PlainText', 'text'))
                update.append('text')
        queue.drain(mode='sync', thread=True)
        ca.run_in_background(self.update_run_all_progress, 2000, update)
        
    def update_progress(self, args):
        cls, gui_id = args
        identifier = self.book.identifier
        if not identifier in self.ProcessHandler.OperationObjects:
            return True
        if cls not in self.ProcessHandler.OperationObjects[identifier]:
            return True
        else:
            progress = getattr(self, gui_id + '_progress')
            total = self.book.page_count-2
            state = self.ProcessHandler.get_op_state(self.book, 
                                                     identifier, cls, 
                                                     total)
            if state['finished']:
                setattr(self, gui_id + '_fraction', 1.0)
                progress.set_fraction(1.0)
                progress.set_text('100%')
                return False
            else:
                fraction = state['fraction']
                setattr(self, gui_id + '_fraction', fraction)
                progress.set_fraction(fraction)                
                string = str(int(fraction*100)) + '% -- Time Remaining: ' \
                    + str(state['estimated_mins']) + ' mins ' + \
                    str(state['estimated_secs']) + ' secs' 
                progress.set_text(string)
                return True

    def update_run_all_progress(self, update):
        identifier = self.book.identifier
        if not identifier in self.ProcessHandler.OperationObjects:
            return True
        op_obj = self.ProcessHandler.OperationObjects[identifier]
        num_tasks = len(update)
        total_fraction = 0.0
        for op, cls in {'cropper': 'Crop',
                        'ocr': 'OCR',
                        'pdf': 'PDF',
                        'djvu': 'Djvu',
                        'epub': 'EPUB',
                        'text': 'PlainText'}.items():
            if op in update:
                if not hasattr(self, op+'_fraction'):
                    #if the other update threads have not
                    #finished their first pass then this
                    #won't exist.
                    continue
                if cls in op_obj:
                    state = self.ProcessHandler.get_op_state\
                        (self.book, identifier,
                         cls, self.book.page_count)
                    total_fraction += getattr(self, op+'_fraction')
        total_fraction /= num_tasks
        self.global_progress.set_fraction(total_fraction)
        self.global_progress.set_text(str(int(total_fraction*100)) + '%')
        if total_fraction == 1.0:
            self.enable_interface()
            return False
        else:
            return True

    def run_cropper(self, widget):
        queue = self.ProcessHandler.new_queue()
        queue.add(self.book, cls='Crop', mth='cropper_pipeline',
                  kwargs={'crop': 'cropBox'})
        queue.drain(mode='sync', thread=True)
        ca.run_in_background(self.update_progress, 2000, args=('Crop', 'cropper'))

    def run_ocr(self, widget):
        queue = self.ProcessHandler.new_queue()
        queue.add(self.book, cls='OCR', mth='tesseract_hocr_pipeline',
                  kwargs={'lang': self.language})
        queue.drain(mode='sync', thread=True)
        ca.run_in_background(self.update_progress, 2000, args=('OCR', 'ocr'))

    def run_derive(self, widget):
        queue = self.ProcessHandler.new_queue()
        if self.derive_pdf.get_active():
            queue.add(self.book, cls='PDF', mth='make_pdf_with_hocr2pdf',
                      kwargs=self.return_pdf_args())
            ca.run_in_background(self.update_progress, 2000, args=('PDF', 'pdf'))
        if self.derive_djvu.get_active():
            queue.add(self.book, cls='Djvu', mth='make_djvu_with_c44',
                      kwargs=self.return_djvu_args())
            ca.run_in_background(self.update_progress, 2000, args=('Djvu', 'djvu'))
        if self.derive_plain_text.get_active():
            queue.add(self.book, cls='PlainText', mth='make_full_plain_text')
            ca.run_in_background(self.update_progress, 2000, args=('PlainText', 'text'))
        if self.derive_epub.get_active():
            queue.add(self.book, cls='EPUB', mth='make_epub')
            ca.run_in_background(self.update_progress, 2000, args=('EPUB', 'epub'))        
        queue.drain(mode='sync', thread=True)
        
    def get_derive_format_args(self):
        formats = {}
        for name, attr in self.derivatives.items():
            if attr[0].get_active():
                if attr[1] is not None:
                    formats[name] = attr[1]()
                else:
                    formats[name] = None
        if len(formats) < 1:
            return None
        else:
            return formats
