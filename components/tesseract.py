from environment import Environment
from component import Component

class Tesseract(Component):
    """
    Tesseract
    ---------

    Performs OCR related tasks.

    """

    args = ['in_file','out_base','language','psm', 'hocr']
    executable = 'tesseract'

    def __init__(self):
        super(Tesseract, self).__init__(Tesseract.args)
