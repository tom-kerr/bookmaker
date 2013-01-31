#!/usr/bin/python
import sys, argparse
from environment import Environment
from processing import ProcessHandler


def main(args):
    
    E = Environment(args.root_dir)
    
    if args.respawn:
        Environment.settings['respawn'] = True
    elif args.no_respawn:
        Environment.settings['respawn'] = False
        
    P = ProcessHandler()

    for book in E.books:
        P.queue_process(P.run_main, (book.identifier, book), book.logger)
        if args.derive_all or args.derive:
            if Environment.settings['respawn']:
                P.queue_process(P.run_cropper, (book, args.active_crop), book.logger)
                P.queue_process(P.run_ocr, (book, args.language), book.logger)
            if args.derive_all:
                P.queue_process(P.derive_formats, (book, ('djvu', 'pdf', 'epub', 'text')), book.logger)
            elif args.derive:
                P.queue_process(P.derive_formats, (book, tuple(args.derive)), book.logger)
        P.run_queue()        
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser('./bookmaker')
    parser.add_argument('--root-dir', required=True, help='A single item or a directory of items')
    parser.add_argument('--language', nargs='?', default='English')
    parser.add_argument('--active-crop', nargs='?', default='cropBox')
    parser.add_argument('--derive', nargs='+', help='Formats: djvu, pdf, epub, text')
    parser.add_argument('--derive-all', action='store_true', help='Derive all formats')

    parser.add_argument('--respawn', action='store_true', help='Files/Data will be re-created (default)')
    parser.add_argument('--no-respawn', action='store_false', help='Files/Data will be not be re-created')
    
    if len(sys.argv)<2:
        parser.print_help()
        sys.exit(0);
    else:
        args = parser.parse_args()
        main(args)
