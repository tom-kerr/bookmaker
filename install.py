import os, sys, platform
import glob
import urllib2
import zipfile
import tarfile
import re

from util import Util

py_version = sys.version_info
if py_version[0] < 2 or py_version[0] == 2 and py_version[1] != 7:
    Util.bail('Python 2.7 required')
    
plat = sys.platform
if re.search('linux', plat):
    dist = platform.linux_distribution()[0]
if re.search('darwin', plat):
    dist = platform.mac_ver()[0]
if re.search('win', plat):
    dist = platform.win32_ver()[0]

print 'Environment: ' + dist, plat

py_dep = {'yaml':   {'Ubuntu': {'method':'pkg-manager', 
                                'pkg': 'python-yaml'}},
          'lxml':   {'Ubuntu': {'method':'pkg-manager', 
                                'pkg': 'python-lxml'}},
          'psutil': {'Ubuntu': {'method':'pkg-manager', 
                                'pkg': 'python-psutil'}},
          'pypdf':  {'Ubuntu': {'method':'pkg-manager', 
                                'pkg': 'python-pypdf'}},
          'pil':    {'Ubuntu': {'method':'pkg-manager', 
                                'pkg': 'python-imaging'}},
          'pygtk':  {},
          'xmltodict':    {'Ubuntu': {'method':'pkg-manager', 
                                'pkg': 'xmltodict'}},
          'dict2xml':    {'Ubuntu': {'method':'pkg-manager', 
                                'pkg': 'dict2xml'}},
          'bibs':   {dist: {'method':'distutils', 
                            'url': 'https://github.com/reklaklislaw/bibs/archive/master.zip'}}
          }

sys_dep = { 'make':       {'Ubuntu': 'make'},
            'libtiff':    {'Ubuntu': 'libtiff4-dev'},
            'netpbm':     {'Ubuntu': 'netpbm'},
            'djvulibre':  {'Ubuntu': 'djvulibre-bin'},
            'exactimage': {'Ubuntu': 'exactimage'},
            'fftw':       {'Ubuntu': 'libfftw3-3'},
            'leptonica':  {'Ubuntu': 'libleptonica-dev'},
            'tesseract':  {'Ubuntu': 'tesseract-ocr*'}
            }
            

def check_py_dep():
    for module, dists in py_dep.items():
        print 'Checking for ' + module
        try:
            __import__(module)
        except ImportError:            
            if dist in dists:
                method = dists[dist]['method']
                if method == 'pkg-manager':
                    if not install_with_package_manager(dists[dist]['pkg']):
                        Util.bail('Failed to install ' + module)
                elif method == 'distutils':
                    source = dists[dist]['url']
                    path = download_and_extract(source)
                    if not install_with_distutils(path):
                        Util.bail('Failed to install ' + module)
            else:
                Util.bail('Distribution ' + str(dist) + ' is not supported by this script')
        else:
            print 'Already Installed.'


def install_with_package_manager(mod):
    if dist in ('Ubuntu', 'Debian'):
        cmd = 'apt-get^ -y^ install^ ' + mod + '^'
    retval = Util.cmd(cmd, retval=True, print_output=True)
    if retval != 0:
        return False
    else:
        return True


def install_with_distutils(path):
    cmd = 'python^ setup.py^ install^'
    retval = Util.cmd(cmd, current_wd=path, retval=True, print_output=True)
    if retval != 0:
        return False
    else:
        return True


def check_sys_dep():
    for pkg, dists in sys_dep.items():
        if dist in dists:
            if not install_with_package_manager(dists[dist]):
                Util.bail('Failed to install ' + pkg)
        else:
            Util.bail('Distribution ' + str(dist) + ' is not supported by this script')


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
        if ext == '.zip':
            archive = zipfile.ZipFile('packages/' + basename)
            archive.extractall(path='packages/'+filename)        
        elif ext in ('.tar', '.tar.gz', '.tar.bz2', '.tgz'):
            archive = tarfile.open('packages/' + basename)
            archive.extractall('packages/')    
    except Exception as e:
        print 'Error downloading and extracting ' + basename
        Util.bail(str(e))
        
    match = glob.glob('packages/'+filename+'/*')
    path = None
    for m in match:
        if os.path.isdir(m):
            path = m
            break

    return path


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

