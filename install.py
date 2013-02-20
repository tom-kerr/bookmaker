import os, sys, platform
import glob
import urllib2
import zipfile
import tarfile
import re

from util import Util

py_version = sys.version_info
if py_version[0] < 2 or py_version[0] == 2 and py_version[1] < 7:
    print "Python 2.7 or greater Required"
    Util.bail('Python too small')

plat = sys.platform
if re.search('linux', plat):
    dist = platform.linux_distribution()[0]
if re.search('darwin', plat):
    dist = platform.mac_ver()[0]
if re.search('win', plat):
    dist = platform.win32_ver()[0]

print 'Environment: ' + dist, plat

py_dep = {'yaml': {'Ubuntu': 'python-yaml'},
          'lxml': {'Ubuntu': 'python-lxml'},
          'psutil': {'Ubuntu': 'python-psutil'},
          'pypdf': {'Ubuntu': 'python-pypdf'},
          'pygtk': {}
          }

sys_dep = { 'djvulibre': { 'source': 'http://downloads.sourceforge.net/project/djvu/DjVuLibre/3.5.25/djvulibre-3.5.25.3.tar.gz',
                           'Ubuntu': 'djvulibre-bin'},
            'exactimage': {'source': 'http://dl.exactcode.de/oss/exact-image/exact-image-0.8.7.tar.bz2',
                           'Ubuntu': 'exactimage'},
            'fftw': {'source': 'http://www.fftw.org/fftw-3.3.3.tar.gz',
                     'Ubuntu': 'libfftw3-3'},
            'leptonica': {'source': 'http://www.leptonica.com/source/leptonica-1.69.tar.gz',
                          'Ubuntu': 'libleptonica'},
            'tesseract': {'source': '',
                          'Ubuntu': 'tesseract-ocr*'}
            }
            

def check_py_dep():
    for module, dists in py_dep.items():
        print 'checking for ' + module
        try:
            __import__(module)
        except ImportError:            
            if dist in dists:
                install_with_package_manager(dists[dist])
            else:
                print 'Distrbution not supported by this script. Consult the README for other install options.'
                Util.bail(module + ' not installed.')
        else:
            print 'Installed.'


def install_with_package_manager(mod):
    if dist in ('Ubuntu', 'Debian'):
        cmd = 'apt-get^ -y^ install^ ' + mod + '^'
    retval = Util.cmd(cmd, retval=True, print_output=True)
    if retval != 0:
        return False
    else:
        return True
    

def check_sys_dep():
    for pkg, dists in sys_dep.items():
        if dist in dists:
            if not install_with_package_manager(dists[dist]):
                print 'failed...will try to compile from source...'
                source_dir = download_and_extract(dists['source'])
                install_from_source(source_dir)
        else:
            source_dir = download_and_extract(dists['source'])
            install_from_source(source_dir)


def download_and_extract(source):
    if not os.path.exists('packages'):
        os.mkdir('packages')
    basename = os.path.basename(source)
    if not os.path.exists('packages/' + basename):
        print 'Downloading ' + source
        try:
            fp = urllib2.urlopen(source)
            f = open('packages/' + basename, 'w')
            f.write(fp.read())
            f.close()
        except Exception as e:
            print 'Error opening ' + source
            Util.bail(str(e))
                        
    print 'Extracting...'
    for extension in ('.zip','.tar','.tar.gz', '.tar.bz2', '.tgz'):
        if re.search(extension + '$', basename):
            ext = extension
            filename = basename.split(ext)[0]
            break    
    try:
        if ext == 'zip':
            archive = zipfile.ZipFile('packages/' + basename)
            archive.extractall(path='packages/')        
        elif ext in ('.tar', '.tar.gz', '.tar.bz2', '.tgz'):
            archive = tarfile.open('packages/' + basename)
            archive.extractall('packages/')    
    except Exception as e:
        print 'Error downloading and extracting ' + basename
        Util.bail(str(e))
        
    match = glob.glob('packages/'+ filename.split('.')[0] + '*')
    for m in match:
        if os.path.isdir(m):
            filename = m.split('packages/')[1]    
    return filename


def install_from_source(source_dir):
    print 'Entering ' + source_dir
    try:
        make_clean_cmd = 'make^ clean^'
        Util.cmd(make_clean_cmd, current_wd='packages/' + source_dir, print_output=True)
        configure_cmd = './configure'
        Util.cmd(configure_cmd, current_wd='packages/' + source_dir, print_output=True)
        make_cmd = 'make'
        Util.cmd(make_cmd, current_wd='packages/' + source_dir, print_output=True)
        make_install_cmd = 'make^ install^'
        Util.cmd(make_install_cmd, current_wd='packages/' + source_dir, print_output=True)
    except Exception as e:
        print 'Error in ' + source_dir + '...'
        Util.bail(str(e))


def build_bookmaker_executables():
    cmd = './build.sh'
    cwd = 'bin/'
    try:
        Util.cmd(cmd, current_wd=cwd, print_output=True)
    except Exception as e:
        print 'Error building bookmaker executables'
        Util.bail(str(e))

check_py_dep()
check_sys_dep()
build_bookmaker_executables()

