#!/usr/bin/env python3
import sys, argparse
import logging

from util import Util
from environment import Environment
from processing import ProcessHandling

def main(args):
    try:
        E = Environment(args.root_dir, args)
    except Exception as e:
        Util.bail(str(e))

    P = ProcessHandling()

    for book in E.books:
        queue = P.new_queue()
        fnc = P.run_pipeline_distributed

        cls = 'FeatureDetection'
        mth = 'pipeline'
        pid = '.'.join((book.identifier, fnc.__name__, cls, mth))
        queue[pid] = {'func': fnc,
                      'args': [cls, mth, book, None, None], 
                      'kwargs': {},
                      'callback': 'post_process'}
             
        if args.derive_all or args.derive:
            if args.derive:
                formats = args.derive
            else:
                formats = ('djvu', 'pdf', 'epub', 'text')
                
            if book.settings['respawn']:
                cls = 'Crop'
                mth = 'cropper_pipeline'
                pid = '.'.join((book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, book, None, 
                                       {'crop': 'standardCrop'}], 
                              'kwargs': {},
                              'hook': None}
                                     
                cls = 'OCR'
                mth = 'tesseract_hocr_pipeline'
                pid = '.'.join((book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, book, None, 
                                       {'lang': args.language}],
                              'kwargs': {},
                              'hook': None}
                
            if 'djvu' in formats:
                cls = 'Djvu'
                mth = 'make_djvu_with_c44'
                pid = '.'.join((book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, book, None, None],
                              'kwargs': {},
                              'hook': 'assemble_djvu_with_djvm'}
            
            if 'pdf' in formats:
                cls = 'PDF'
                mth = 'make_pdf_with_hocr2pdf'
                pid = '.'.join((book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, book, None, None],
                              'kwargs': {},
                              'hook': 'assemble_pdf_with_pypdf'}
                
            if 'text' in formats:
                cls = 'PlainText'
                mth = 'make_full_plain_text'
                pid = '.'.join((book.identifier, fnc.__name__, cls, mth))
                queue[pid] = {'func': fnc,
                              'args': [cls, mth, book, None, None],
                              'kwargs': {},
                              'hook': 'assemble_ocr_text'}

        P.drain_queue(queue, 'sync', 
                      qpid=book.identifier, 
                      qlogger=book.logger)

if __name__ == "__main__":
    parser = argparse.ArgumentParser('./bookmaker')
    argu = parser.add_argument_group('Required')
    argu.add_argument('--root-dir', nargs='*', required=True, 
                      help='A single item or a directory of items')

    settings = parser.add_argument_group('Settings')
    settings.add_argument('--save-settings', action='store_true', 
                          help='Saves arguments to settings.yaml')

    proc = parser.add_argument_group('Processing')
    proc.add_argument('--respawn', action='store_true', 
                      help='Files/Data will be re-created (default)')
    proc.add_argument('--no-respawn', action='store_true', 
                      help='Files/Data will be not be re-created')

    ocr = parser.add_argument_group('OCR')
    ocr.add_argument('--language', nargs='?', default='English')

    derive = parser.add_argument_group('Derivation')
    derive.add_argument('--active-crop', nargs='?', default='standardCrop')
    derive.add_argument('--derive', nargs='+', 
                        help='Formats: djvu, pdf, epub, text')
    derive.add_argument('--derive-all', action='store_true', 
                        help='Derive all formats')

    debug = parser.add_argument_group('Debug')
    debug.add_argument('--make-cornered-scaled', 
                       action='store_true', default=None)
    debug.add_argument('--draw-clusters', 
                       action='store_true', default=None)
    debug.add_argument('--draw-removed-clusters', 
                       action='store_true', default=None)
    debug.add_argument('--draw-invalid-clusters', 
                       action='store_true', default=None)
    debug.add_argument('--draw-content-dimensions', 
                       action='store_true', default=None)
    debug.add_argument('--draw-page-number-candidates', 
                       action='store_true', default=None)
    debug.add_argument('--draw-noise', action='store_true')

    if len(sys.argv)<2:
        parser.print_help()
        sys.exit(0);
    else:
        args = parser.parse_args()
        main(args)
