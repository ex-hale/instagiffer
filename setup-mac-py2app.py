"""
Build Instagiffer.app

Usage:
    python setup.py py2app
"""

import glob
import os
from   setuptools import setup

#
# Get version from environment
#

if "INSTAGIFFER_VERSION" in os.environ:
    INSTAGIFFER_VERSION    = os.environ[ "INSTAGIFFER_VERSION"]
else:
    exit(1)
if "INSTAGIFFER_PRERELEASE" in os.environ and '-pre' in os.environ[ "INSTAGIFFER_PRERELEASE"]:
    INSTAGIFFER_PRERELEASE = os.environ[ "INSTAGIFFER_PRERELEASE"]
    INSTAGIFFER_PRERELEASE = INSTAGIFFER_PRERELEASE.replace("-pre", ".");
else:
    INSTAGIFFER_PRERELEASE = ""


__author__     = "Exhale Software Inc."
__copyright__  = "Copyright (c) 2016, Exhale Software Inc."
__version__    = INSTAGIFFER_VERSION + INSTAGIFFER_PRERELEASE

APP = ['main.py']

DATA_FILES = [
    ('macdeps',    ['./macdeps/youtube-dl', './macdeps/ffmpeg']),
    ('macdeps/im', glob.glob('./macdeps/im/*')),
    'instagiffer.conf',
    'instagiffer.icns',
]

# Note: py2app can't create a standalone using built-in python

OPTIONS = {
	'iconfile': 'instagiffer.icns',
    #'argv_emulation': True,
    'optimize': 2,
    'packages': ['PIL'],
    'plist':    {
                    'CFBundleShortVersionString':   __version__,
                    'CFBundleVersion':              __version__,
                    'CFBundleDevelopmentRegion':    'English',
                    'CFBundleDisplayName':          'Instagiffer',
                    'CFBundleName':                 'Instagiffer',
                    'NSHumanReadableCopyright':     __copyright__,
                    'CFBundleIdentifier':           'com.instagiffer.instagiffer',
                    'LSMinimumSystemVersion':       '10.8.0',
                    'LSMultipleInstancesProhibited': True,
                    #'CFBundlePackageType':          'APPL',
                    #'CFBundleSignature':            'HAPS',
                    'LSApplicationCategoryType':     'public.app-category.graphics-design',
                    'LSEnvironment':
                    {
                        'LANG':   'en_US.UTF-8',
                        'LC_ALL': 'en_US.UTF-8'
                    },
                }
}

setup(
    name           = "Instagiffer",
    url            = 'http://instagiffer.com',
    version        = __version__,
    app            = APP,
    data_files     = DATA_FILES,
    options        = {'py2app': OPTIONS},
    setup_requires = ['py2app'],
)

# Make files executable
approot = './dist/Instagiffer.app/Contents/Resources/'
for f in [ 'macdeps/ffmpeg', 'macdeps/youtube-dl', 'macdeps/im/bin/convert' ]:
	os.chmod(approot + f, 0755)
