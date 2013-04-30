bookmaker
=========
A tool for capturing, processing, editing, and deriving physical books into electronic media such as PDF, DjVu and Epub.

(in development)


Installation
------------

Currently only Ubuntu is supported by the install script, but support for other distros as well as OSX and Windows is planned.

- Download and unzip

- find install.py and run 'sudo python install.py'


Using bookmaker
--------------

<h2>Capturing</h2>
TODO


<h2>Processing</h2>

Processing will automatically detect the dimensions of all the pages and content as well as generate a clean crop box and record this in an Internet Archive style XML file.

The minimum required to process a book is a project directory, for example, 'mybook_1', and a subdirectory containing image files with '_raw_' or '_RAW_' in the filenames (currently limited to jpgs for now). 
	

<h3>Command line</h3>

To initialize the processing of a book, one would call bookmaker.py like so:

   ./bookmaker.py --root-dir /path/to/my/bookprojects/mybook_1

One can also pass more than one book at time, with a space between each entry, or alternatively pass an entire folder of project directories, like:

    ./bookmaker.py --root-dir /path/to/my/bookprojects

When processing multiple books, one book will be processed per core, and any books over that limit will wait until a slot opens up and begin processing automatically.
 

If one does not care to edit the computer generated crop boxes, one can pass the following combination of arguments to derive the digital formats:

   --language (for OCR)
   --derive FORMAT (options are djvu, pdf, epub, text)
   or
   --derive-all

<h2>GUI</h2> 

The GUI can be started by calling gui_main.py, like:

    ./gui_main.py

The first thing you will see is the main menu:

![Main Menu] (/imgs/main_menu.png)    


<h2>Editing</h2>

