import os, sys, platform
import glob
import urllib
import zipfile
import tarfile
import re

from util import Util

py_version = sys.version_info
if py_version[0] < 3:
    Util.bail('Python 3+ required')

plat = sys.platform
if re.search('linux', plat):
    dist = platform.linux_distribution()[0]
if re.search('darwin', plat):
    dist = platform.mac_ver()[0]
if re.search('win', plat):
    dist = platform.win32_ver()[0]

print ('Environment: ' + dist, plat)

py_dep = {'yaml':   {'Ubuntu': {'method':'pip',
                                'pkg': 'pyaml'}},
          'lxml':   {'Ubuntu': {'method':'pip',
                                'pkg': 'lxml'}},
          'psutil': {'Ubuntu': {'method':'pip',
                                'pkg': 'psutil'}},
          'PyPDF2':  {'Ubuntu': {'method':'distutils',
                                 'url': 'https://github.com/mstamy2/PyPDF2/archive/master.zip'}},
          'PIL':    {'Ubuntu': {'method':'pip',
                                'pkg': 'pillow'}},
          'python3-gi':  {'Ubuntu': {'method': 'pkg-manager',
                                     'pkg': 'python3-gi'}},
          'xmltodict':    {'Ubuntu': {'method':'pip',
                                      'pkg': 'xmltodict'}},
          'dicttoxml':    {'Ubuntu': {'method':'pip',
                                      'pkg': 'dicttoxml'}},
          #'bibs':   {dist: {'method':'distutils',
          #                  'url': 'https://github.com/reklaklislaw/bibs/archive/master.zip'}}
          }

sys_dep = { 'make':       {'Ubuntu': 'make'},
            'libtiff':    {'Ubuntu': 'libtiff4-dev'},
            'libpng12':   {'Ubuntu': 'libpng12-dev'},
            'djvulibre':  {'Ubuntu': 'djvulibre-bin'},
            'exactimage': {'Ubuntu': 'exactimage'},
            'fftw':       {'Ubuntu': 'libfftw3-dev'},
            'leptonica':  {'Ubuntu': 'libleptonica-dev'},
            'tesseract':  {'Ubuntu': 'tesseract-ocr*'}
            }


def check_py_dep():
    for module, dists in py_dep.items():
        print ('Checking for ' + module)
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
                elif method == 'pip':
                    if not install_with_pip(dists[dist]['pkg']):
                        Util.bail('Failed to install ' + module)
            else:
                Util.bail('Distribution ' + str(dist) + 
                          ' is not supported by this script')
        else:
            print ('Already Installed.')


def install_with_pip(mod):
    pip = 'pip-3.2'
    cmd = [pip, 'install', mod]
    retval = Util.exec_cmd(cmd, retval=True, print_output=True)
    if retval != 0:
        return False
    else:
        return True


def install_with_package_manager(mod):
    if dist in ('Ubuntu', 'Debian'):
        cmd = ['apt-get', '-y', 'install', mod]
    retval = Util.exec_cmd(cmd, retval=True, print_output=True)
    if retval != 0:
        return False
    else:
        return True


def install_with_distutils(path):
    python = 'python3.' + str(py_version[1])
    cmd = [python, 'setup.py', 'install']
    retval = Util.exec_cmd(cmd, current_wd=path, 
                           retval=True, print_output=True)
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
            Util.bail('Distribution ' + str(dist) + 
                      ' is not supported by this script')


def download_and_extract(source):
    if not os.path.exists('packages'):
        os.mkdir('packages')
    basename = os.path.basename(source)
    if not os.path.exists('packages/' + basename):
        print ('Downloading ' + source)
        try:
            fp = urllib.request.urlopen(source)
            with open('packages/' + basename, 'w+b') as f:
                f.write(fp.read())
        except Exception as e:
            print ('Error opening ' + source)
            Util.bail(str(e))

    print ('Extracting...')
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
        print ('Error downloading and extracting ' + basename)
        Util.bail(str(e))

    match = glob.glob('packages/'+filename+'/*')
    path = None
    for m in match:
        if os.path.isdir(m):
            path = m
            break

    return path


def build_bookmaker_executables():
    print('Building bookmaker executables')
    cmd = './build.sh'
    cwd = 'bin/'
    try:
        Util.exec_cmd(cmd, current_wd=cwd, print_output=True)
    except Exception as e:
        print ('Error building bookmaker executables')
        Util.bail(str(e))

Util = Util()
if not install_with_package_manager('python3-pip'):
    Util.bail('Failed to install pip')
check_py_dep()
check_sys_dep()
build_bookmaker_executables()

