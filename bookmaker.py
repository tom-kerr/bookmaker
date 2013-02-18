#!/usr/bin/python
import sys, argparse
from util import Util
from environment import Environment
from processing import ProcessHandling

def main(args):
    
    try:
        E = Environment(args.root_dir, args)            
    except Exception as e:
        Util.bail(str(e))

    P = ProcessHandling()
    #P.add_process(P.check_thread_exceptions,
    #              'check_thread_exceptions',
    #              None)

    for book in E.books:        
        queue = P.new_queue()
        queue[book.identifier + '_main'] = P.run_main, book, book.logger, None

        if args.derive_all or args.derive:
            if book.settings['respawn']:
                queue[book.identifier + '_run_cropper'] = P.run_cropper, (book, args.active_crop), book.logger, None                
                queue[book.identifier + '_run_ocr'] = P.run_ocr, (book, args.language), book.logger, None

            if args.derive_all:
                queue[book.identifier + '_derive'] = P.derive_formats, (book, ('djvu', 'pdf', 'epub', 'text')), book.logger, None
            elif args.derive:
                queue[book.identifier + '_derive'] = P.derive_formats, (book, tuple(args.derive)), book.logger, None

        P.add_process(P.drain_queue, 
                      book.identifier + '_drain_queue', 
                      (queue, 'sync'), book.logger)
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser('./bookmaker')
    argu = parser.add_argument_group('Required')
    argu.add_argument('--root-dir', nargs='*', required=True, help='A single item or a directory of items')

    settings = parser.add_argument_group('Settings')
    settings.add_argument('--save-settings', action='store_true', help='Saves arguments to settings.yaml')

    proc = parser.add_argument_group('Processing')
    proc.add_argument('--respawn', action='store_true', help='Files/Data will be re-created (default)')
    proc.add_argument('--no-respawn', action='store_true', help='Files/Data will be not be re-created')

    ocr = parser.add_argument_group('OCR')
    ocr.add_argument('--language', nargs='?', default='English')

    derive = parser.add_argument_group('Derivation')
    derive.add_argument('--active-crop', nargs='?', default='cropBox')
    derive.add_argument('--derive', nargs='+', help='Formats: djvu, pdf, epub, text')
    derive.add_argument('--derive-all', action='store_true', help='Derive all formats')

    debug = parser.add_argument_group('Debug')
    debug.add_argument('--make-cornered-thumbs', action='store_true', default=None)
    debug.add_argument('--draw-clusters', action='store_true', default=None)
    debug.add_argument('--draw-removed-clusters', action='store_true', default=None)
    debug.add_argument('--draw-invalid-clusters', action='store_true', default=None)
    debug.add_argument('--draw-content-dimensions', action='store_true', default=None)
    debug.add_argument('--draw-page-number-candidates', action='store_true', default=None)
    debug.add_argument('--draw-noise', action='store_true')
    

    if len(sys.argv)<2:
        parser.print_help()
        sys.exit(0);
    else:
        args = parser.parse_args()
        main(args)
