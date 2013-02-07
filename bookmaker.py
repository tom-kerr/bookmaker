#!/usr/bin/python
import sys, argparse
from environment import Environment
from processing import ProcessHandler


def main(args):
    
    E = Environment(args.root_dir)        
    P = ProcessHandler()

    for book in E.books:        
        queue = P.new_queue()
        
        if args.respawn:
            book.settings['respawn'] = True
        elif args.no_respawn:
            book.settings['respawn'] = False

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
    P.finish()

if __name__ == "__main__":
    parser = argparse.ArgumentParser('./bookmaker')
    parser.add_argument('--root-dir', nargs='*', required=True, help='A single item or a directory of items')
    parser.add_argument('--language', nargs='?', default='English')
    parser.add_argument('--active-crop', nargs='?', default='cropBox')
    parser.add_argument('--derive', nargs='+', help='Formats: djvu, pdf, epub, text')
    parser.add_argument('--derive-all', action='store_true', help='Derive all formats')

    parser.add_argument('--respawn', action='store_true', help='Files/Data will be re-created (default)')
    parser.add_argument('--no-respawn', action='store_true', help='Files/Data will be not be re-created')
    
    if len(sys.argv)<2:
        parser.print_help()
        sys.exit(0);
    else:
        args = parser.parse_args()
        main(args)
