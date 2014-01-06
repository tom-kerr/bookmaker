bookmaker
=========
A tool for capturing, processing, editing, and converting physical books into electronic media such as PDF, DjVu and Epub.


Note:
Currently undergoing lots of rewriting/refactoring/upgrades; much is broken, including the gui.


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

Processing will automatically detect the dimensions of all the pages and content as well as generate a clean crop box and record this in an Internet Archive-style 'scandata' XML file.

The minimum required to process a book is a project directory, for example, 'mybook_1', and a subdirectory of raw images (currently limited to jpgs for now). The raw image subdirectory should follow the naming convention NAME_raw_FILETYPE or NAME_RAW_FILETYPE. For example, 'mybook_1_RAW_jpg'.
	

<h3>Command line</h3>

To initialize the processing of a book, one would call bookmaker.py like so:

    ./bookmaker.py --root-dir /path/to/my/bookprojects/mybook_1

One can also pass more than one book at time, with a space between each entry, or alternatively pass an entire folder of project directories, like:

    ./bookmaker.py --root-dir /path/to/my/bookprojects

When processing multiple books, one book will be processed at a time, with each operation split across multiple cores. 

If one does not care to edit the computer generated crop boxes, one can pass the following combination of arguments to derive the digital formats immediately after processing:

    --language (for OCR (default is English))
    --active-crop (the crop box that will be used for cropping (options are standardCrop (default), pageCrop, contentCrop))
    --derive FORMAT (options are djvu, pdf, epub, text)
    or
    --derive-all

<h3>GUI</h3> 

The GUI can be started by calling gui_main.py, like:

    ./gui_main.py

The first thing you will see is the main menu:

![Main Menu] (/imgs/main_menu.png)    

Selecting 'process', will bring up the processing queue window:

![Processing Queue] (/imgs/processing_queue.png)

<h4>Add</h4>
Opens a user selection window for adding project directories to the queue.

<h4>Remove</h4>
Removes the selected project directory(s) from the queue.

<h4>Options</h4>
(Debugging options mostly likely to be hidden at some point but exposed for now)

<h4>Init</h4>
Begins the processing for the selected project directory(s).

<h4>Edit</h4>
Opens the editor for the selected project directory. Note that the processing must finish before one can edit the item. 


An illustration of three items that are undergoing processing:

![Processing] (/imgs/processing.png)


<h2>Editing</h2>


