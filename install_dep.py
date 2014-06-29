import os, sys, platform
import glob
from urllib import request
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

dist = dist.lower()

print ('Environment: ' + dist, plat)

py_dep = {'yaml': 'pyaml',
          'lxml': 'lxml',
          'psutil': 'psutil',
          'PyPDF2': 'git+git://github.com/mstamy2/PyPDF2',
          'PIL': 'pillow',
          'xmltodict': 'xmltodict',
          'dicttoxml': 'dicttoxml'
          }

sys_dep = { 'make':       {'ubuntu': 'make',
                           'debian': 'make'},
            'libtiff':    {'ubuntu': 'libtiff4-dev',
                           'debian': 'libtiff4-dev'},
            'libpng12':   {'ubuntu': 'libpng12-dev',
                           'debian': 'libpng12-dev'},
            'djvulibre':  {'ubuntu': 'djvulibre-bin',
                           'debian': 'djvulibre-bin'},
            'exactimage': {'ubuntu': 'exactimage',
                           'debian': 'exactimage'},
            'fftw':       {'ubuntu': 'libfftw3-dev',
                           'debian': 'libfftw3-dev'},
            'leptonica':  {'ubuntu': 'libleptonica-dev',
                           'debian': 'libleptonica-dev'},
            'tesseract':  {'ubuntu': 'tesseract-ocr*',
                           'debian': 'tesseract-ocr*'},
            'python3-gi': {'ubuntu': 'python3-gi',
                           'debian': 'python3-gi'},
            'gphoto2':    {'ubuntu': 'gphoto2',
                           'debian': 'gphoto2'}
            }


def check_py_dep():
    for module, pkg in py_dep.items():
        print ('Installing ' + module)
        if not install_with_pip(pkg):
            Util.bail('Failed to install ' + module)
        
def check_sys_dep():
    for pkg, dists in sys_dep.items():
        if dist in dists:
            if not install_with_package_manager(dists[dist]):
                Util.bail('Failed to install ' + pkg)
        else:
            Util.bail('Distribution ' + str(dist) + 
                      ' is not supported by this script')

def install_with_package_manager(mod):
    if dist in ('ubuntu', 'debian'):
        cmd = ['sudo', 'apt-get', '-y', 'install', mod]
    retval = Util.exec_cmd(cmd, retval=True, print_output=True)
    if retval != 0:
        return False
    else:
        return True

def install_with_pip(mod):
    pip = 'pip3'
    cmd = [pip, 'install', '-I',  mod]
    retval = Util.exec_cmd(cmd, retval=True, print_output=True)
    if retval != 0:
        return False
    else:
        return True

Util = Util()
check_py_dep()
check_sys_dep()

