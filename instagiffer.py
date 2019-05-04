#/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2019 Exhale Software Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#    This product includes software developed by Exhale Software Inc.
# 4. Neither Exhale Software Inc., nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY EXHALE SOFTWARE INC. ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL EXHALE SOFTWARE INC.  BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
###############################################################################

"""instagiffer.py: The easy way to make GIFs"""

# Only use odd-numbered minor revisions for pre-release builds
INSTAGIFFER_VERSION="1.77"
# If not a pre-release set to "", else set to "pre-X"
INSTAGIFFER_PRERELEASE=""

__author__       = "Justin Todd"
__copyright__    = "Copyright 2013-2019, Exhale Software Inc."
__maintainer__   = "Justin Todd"
__email__        = "instagiffer@gmail.com"
__imgurcid__     = "58fc34d08ab311d"
__status__       = "Production"
__version__      = INSTAGIFFER_VERSION+INSTAGIFFER_PRERELEASE
__release__      = True  # If this is false, bindep output, and info-level statements will be displayed stdout
__changelogUrl__ = "http://instagiffer.com/post/146636589471/instagiffer-175-macpc"
__faqUrl__       = "http://www.instagiffer.com/post/51787746324/frequently-asked-questions"
 
import hashlib
import argparse
import base64
import json
import urllib
import urllib2
import sys
import os
import shutil
import subprocess
import re
import glob
import uuid
import time
import itertools
import logging
import random 
import locale
import shlex
import traceback
import codecs
from   random import randrange
from   os.path import expanduser
from   ConfigParser import SafeConfigParser, RawConfigParser
from   threading  import Thread
from   Queue import Queue, Empty
from   fractions import gcd

# PIL
import PIL
from   PIL import Image, ImageTk, ImageFilter, ImageDraw

# TK
import ttk
import tkFont
import tkMessageBox
from   Tkinter import *
from   tkColorChooser import *
from   tkFileDialog import askopenfilename, askdirectory, asksaveasfilename


# Win32 specific includes
if sys.platform == 'win32':
    import winsound
    import win32api
     # Windows uses the PIL ImageGrab module for screen capture
    from PIL import ImageGrab

# Return true if running on a MAC
#

def ImAMac():
    return sys.platform == 'darwin'

#
# Return true if running on a PC
#

def ImAPC():
    return sys.platform == 'win32'

#
# Open a file in the application associated with this file extension
#

def OpenFileWithDefaultApp(fileName):
    if sys.platform == 'darwin':
        os.system('open ' + fileName)
    else:
        try:
            os.startfile(fileName)
        except:
            tkMessageBox.showinfo("Unable to open!", "I wasn't allowed to open '" + fileName + "'. You will need to perform this task manually.")

def GetFileExtension(filename):
    try:
        fname, fext = os.path.splitext(filename)
    except:
        return ""

    if fext is None:
        return ""

    fext = str(fext).lower()
    fext = fext.strip('.')
    return fext


def AudioPlay(wavPath):
    if ImAMac():
        if wavPath is not None:
            subprocess.call(["afplay", wavPath]) # blocks
    elif ImAPC():
        if wavPath is None:
            winsound.PlaySound(None, 0)
        else:
            winsound.PlaySound(wavPath, winsound.SND_FILENAME|winsound.SND_ASYNC)

    return True

def IsPictureFile(fileName):
    return GetFileExtension(fileName) in [ 'jpeg', 'jpg', 'png', 'bmp', 'tif' ]

def IsUrl(s):
    urlPatterns = re.compile('^(www\.|https://|http://)', re.I)
    return urlPatterns.match(s)


def GetLogPath():
    return os.path.dirname(os.path.realpath(sys.argv[0])) + os.sep + 'instagiffer-event.log'

#
# Mostly for Windows. Converts path into short form to bypass unicode headaches
#

def CleanupPath(path):
    #
    # Deal with Unicode video paths. On Windows, simply DON'T
    # deal with it. Use short names and paths instead :S
    #

    if ImAPC():

        try:
            path.decode('ascii')
        except:
            path = win32api.GetShortPathName(path)

    return path


#
# Re-scale a value
#

def ReScale(val, oldScale, newScale):
    OldMax   = oldScale[1]
    OldMin   = oldScale[0]
    NewMax   = newScale[1]
    NewMin   = newScale[0]
    OldValue = val
    OldRange = (OldMax - OldMin)  
    NewRange = (NewMax - NewMin)  
    NewValue = (((OldValue - OldMin) * NewRange) / OldRange) + NewMin
    return NewValue


#
# norecurse decorator
#
def norecurse(func):
    func.called = False
    def f(*args, **kwargs):
        if func.called:
            print "Recursion!"
            return False
        else:
            func.called = True
            result      = func(*args, **kwargs)
            func.called = False
            return result
    return f

#
# Convert a time or duration (hh:mm:ss.ms) string into a value in milliseconds
#

def DurationStrToMillisec(str, throwParseError=False):
    if str is not None:
        r      = re.compile('[^0-9]+')
        tokens = r.split(str)
        vidLen = ((int(tokens[0]) * 3600) + (int(tokens[1]) * 60) + (int(tokens[2]))) * 1000 + int(tokens[3])
        return vidLen
    else:
        if throwParseError:
            raise ValueError("Invalid duration format")

        return 0


def DurationStrToSec(durationStr):
    ms = DurationStrToMillisec(durationStr)

    if ms == 0:
        return 0
    else:
        #return int((ms + 500) / 1000) # Rouding
        return int(ms/1000) # Floor


def MillisecToDurationComponents(msTotal):
    secTotal = msTotal / 1000
    h  = int(secTotal  / 3600)
    m  = int((secTotal % 3600) / 60)
    s  = int(secTotal  % 60)
    ms = int(msTotal   % 1000)

    return [h, m, s, ms]


def MillisecToDurationStr(msTotal):
    dur = MillisecToDurationComponents(msTotal)
    return "%02d:%02d:%02d.%03d" % (dur[0],dur[1],dur[2],dur[3])


def CountFilesInDir(dirname, filenamePattern=None):
    if filenamePattern is None:
        return len([name for name in os.listdir(dirname) if os.path.isfile(os.path.join(dirname, name))])
    else:
        fileglobber = dirname + filenamePattern + '*'
        return len(glob.glob(fileglobber))

#
# Run non-blocking
#

#
# Converts process output to status bar messages - there is some cross-cutting here
#
def DefaultOutputHandler(stdoutLines, stderrLines, cmd):
    s = None
    i = False

    for outData in [stdoutLines, stderrLines, cmd]:
        if outData is None or len(outData) == 0:
            continue

        if ImAMac() and type(outData) == list:
            outData = " ".join('"{0}"'.format(arg) for arg in outData)

        # youtube dl
        youtubeDlSearch = re.search(r'\[download\]\s+([0-9\.]+)% of', outData, re.MULTILINE)
        if youtubeDlSearch:
            i = int(float(youtubeDlSearch.group(1)))
            s = "Downloaded %d%%..." % (i)   

        # ffmpeg frame extraction progress
        ffmpegSearch = re.search(r'frame=.+time=(\d+:\d+:\d+\.\d+)', outData, re.MULTILINE)
        if ffmpegSearch:
            secs = DurationStrToMillisec(ffmpegSearch.group(1))
            s = "Extracted %.1f seconds..." % (secs/1000.0)

        # imagemagick - figure out what we're doing based on comments
        imSearch = re.search(r'^".+(convert\.exe|convert)".+-comment"? "([^"]+):(\d+)"', outData)
        if imSearch:
            n = int(imSearch.group(3))

            if n == -1:
                s = "%s" % (imSearch.group(2))
            else:
                i = n
                s = "%d%% %s" % (i, imSearch.group(2))

    return s, i


ON_POSIX = 'posix' in sys.builtin_module_names

def EnqueueProcessOutput(streamId, inStream, outQueue):
    for line in iter(inStream.readline, b''):
        #logging.info(streamId + ": " + line)
        outQueue.put(line)


#
# Prompt User
#
def NotifyUser(title, msg):
    return tkMessageBox.showinfo(title, msg)

#
# Run a process
#

def RunProcess(cmd, callback = None, returnOutput = False, callBackFinalize = True, outputTranslator = DefaultOutputHandler):
    if not __release__:
        logging.info("Running Command: " + cmd)

    try:
        cmd = cmd.encode(locale.getpreferredencoding())
    except UnicodeError:
        logging.error("RunProcess: Command '" + cmd + "' contained undecodable unicode. Local encoding: " + str(locale.getpreferredencoding()))

        if returnOutput:
            return "",""
        else:
            return False

    env = os.environ.copy()

    if ImAPC():
        startupinfo              = subprocess.STARTUPINFO()
        startupinfo.dwFlags     |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow  = subprocess.SW_HIDE
    elif ImAMac():
        startupinfo = None
        cmd         = shlex.split(cmd)

    pipe  = subprocess.Popen(cmd, startupinfo=startupinfo, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, bufsize=1, close_fds=ON_POSIX)
    qOut  = Queue()
    qErr  = Queue()
    tOut  = Thread(target=EnqueueProcessOutput, args=("OUT", pipe.stdout, qOut))
    tErr  = Thread(target=EnqueueProcessOutput, args=("ERR", pipe.stderr, qErr))

    tOut.start()
    tErr.start()

    callbackReturnedFalse = False

    stdout = ""
    stderr = ""

    percent = None
    while True:
        statusStr   = None
        stderrLines = None
        stdoutLines = None

        try:
            while True: # Exhaust the queue
                stdoutLines = qOut.get_nowait()
                stdout     += stdoutLines
        except: pass

        try:
            while True:
                stderrLines = qErr.get_nowait()
                stderr     += stderrLines
        except: pass

        if outputTranslator is not None:
            #try:
            statusStr, percentDoneInt = outputTranslator(stdoutLines, stderrLines, cmd)

            if type(percentDoneInt) == int:
                percent = percentDoneInt
            elif percent is not None:
                percentDoneInt = percent

            #except:
            #    pass

        # Caller wants to abort!
        if callback is not None and callback(percentDoneInt, statusStr) == False:       
            try:
                pipe.terminate()
                pipe.kill()
            except:
                logging.error("RunProcess: kill() or terminate() caused an exception")

            callbackReturnedFalse = True
            break

        # Check if done
        if pipe.poll() is not None:
            break

        time.sleep(0.1) # Polling frequency. Lengthening this will decrease responsiveness

    # Notify callback of exit. Check callballFinalize so we don't prematurely reset the progress bar
    if callback is not None and callBackFinalize is True:
        callback(True)

    # Callback aborted command
    if callbackReturnedFalse:
        logging.error("RunProcess was aborted by caller")
        #return False

    # result
    try:
        remainingStdout = ""
        remainingStderr = ""
        remainingStdout, remainingStderr = pipe.communicate()
    except IOError as e:
        logging.error("Encountered error communicating with sub-process" + str(e))

    success = (pipe.returncode == 0)
    stdout += remainingStdout
    stderr += remainingStderr

    # Logging
    if not __release__:
        logging.info("return:  " + str(success))
        logging.info("stdout:  " + stdout)
        logging.error("stderr: " + stderr)

    if returnOutput:
        return stdout, stderr #, success
    else:
        return success


#
# Create working directory
#

def CreateWorkingDir(conf):
    tempDir = None

    # See if they specified a custom dir
    if conf.ParamExists('paths', 'workingDir'):
        tempDir = conf.GetParam('paths', 'workingDir')

    appDataRoot = ''

    # No temp dir configured
    if tempDir == None or tempDir == '':
        if ImAMac():
            appDataRoot  = expanduser("~") + '/Library/Application Support/'
            tempDir      = appDataRoot + 'Instagiffer/'
        else:
            appDataRoot  = expanduser("~") + os.sep
            tempDir      = appDataRoot + '.instagiffer' + os.sep + 'working'

    # Pre-emptive detection and correction of language issues
    try:
        tempDir.encode(locale.getpreferredencoding())
    except UnicodeError:
        logging.info("Users home directory is problematic due to non-latin characters: " + tempDir)
        tempDir = GetFailSafeDir(conf, tempDir)

    # Try to create temp directory
    if not os.path.exists(tempDir):
        os.makedirs(tempDir)
        if not os.path.exists(tempDir):
            logging.error("Failed to create working directory: " + tempDir)
            return ""

    logging.info("Working directory created: " + tempDir)
    return tempDir


#
# For language auto-fix 
#
def GetFailSafeDir(conf, badPath):
    path = badPath

    if ImAPC():
        goodPath = conf.GetParam('paths', 'failSafeDir')
        if not os.path.exists(goodPath):
            if tkMessageBox.askyesno("Automatically Fix Language Issue?", "It looks like you are using a non-latin locale. Can Instagiffer create directory " + goodPath + " to solve this issue?"):
                err = False
                try:
                    os.makedirs(goodPath)
                except:
                    err = True

                if os.path.exists(goodPath):
                    path = goodPath
                else:
                    err = True

                if err:
                    tkMessageBox.showinfo("Error Fixing Language Issue", "Failed to create '" + goodPath + "'. Please make this directory manually in Windows Explorer, then restart Instagiffer.")
        else:
            path = goodPath

    return path

#
# Configuration Class
#

class InstaConfig:

    description = "Configuration Class"
    author      = "Justin Todd"

    def __init__(self, configPath):
        self.path = configPath

        # Load configuration file
        if not os.path.exists(self.path):
            logging.error("Unable to find configuration file: " + self.path)

        self.ReloadFromFile()

    def ReloadFromFile(self):
        self.config = None
        self.config = SafeConfigParser()
        self.config.read(self.path)

    def ParamExists(self, category, key):
        if not category in self.config._sections:
            return False

        if not key.lower() in self.config._sections[category.lower()]:
            #self.Dump()
            #logging.error("Configuration parameter %s.%s does not exist" % (category, key))
            return False
        else:
            #logging.info("Configuration parameter %s.%s exists" % (category, key))
            return True

    def GetParam(self, category, key):
        retVal = u""

        if self.ParamExists(category, key):
            retVal = self.config._sections[category.lower()][key.lower()]
        elif self.ParamExists(category + '-' + sys.platform, key):
            retVal = self.config._sections[category.lower() + '-' + sys.platform][key.lower()] # platform specific config

        if isinstance(retVal, bool) or isinstance(retVal, int):
            return retVal

        # We are dealing with strings or unicode 

        # Expand variables
        try:
            retVal = os.path.expandvars(retVal)
        except:
            pass

        # Config file encoding is UTF-8
        if not isinstance(retVal, unicode):
            retVal = unicode(retVal, 'utf-8')


        if retVal.startswith(";"):
            retVal = ""

        return retVal

    # 
    def GetParamBool(self, category, key):
        val = self.GetParam(category, key)
        boolVal = True

        if isinstance(val, int):
            boolVal = not (val == 0)
        elif val == None:
            boolVal = False
        elif val == "":
            boolVal = False
        elif val.lower() == "false" or val == "0":
            boolVal = False

        return boolVal

    #
    def SetParam(self, category, key, value):
        
        try:
            current = self.config._sections[category.lower()][key.lower()]
        except KeyError:
            current = None

        self.config._sections[category.lower()][key.lower()] = value
        if value != current:
            return 1
        else:
            return 0

    def SetParamBool(self, category, key, val):
        boolVal = True
        if isinstance(val, int):
            boolVal = not (val == 0)        
        elif val == None:
            boolVal = False
        elif val == "":
            boolVal = False
        elif val.lower() == "false" or val == "0":
            boolVal = False

        boolVal = str(boolVal)
        changed = self.SetParam(category, key, val)
        return changed


    def Dump(self):
        logging.info("=== GIF Configuration =========================================")

        for cat in self.config._sections:
            logging.info("%s:" % (str(cat)))

            for k in self.config._sections[cat]:
                dumpStr = u"  - " + k + u": "
                val = self.GetParam(cat, k)

                if isinstance(val, bool):
                    dumpStr += str(val) + " (boolean)"
                elif isinstance(val, int):
                    dumpStr += str(val) + " (int)"
                else:
                    dumpStr += val
                logging.info(dumpStr)

        logging.info("===============================================================")


#
# Wrapper around the Imagemagick font engine
#

class ImagemagickFont:
    def __init__(self, imagemagickFontData):

        self.fonts = dict()
        fonts = re.findall(r'\s*Font: (.+?)\n\s*family: (.+?)\n\s*style: (.+?)\n\s*stretch: (.+?)\n\s*weight: (.+?)\n\s*glyphs: (.+?)\n', imagemagickFontData, re.DOTALL|re.M|re.UNICODE)

        for font in fonts:
            fontFamily  = font[1].strip()
            fontId      = font[0].strip()
            fontFile    = font[5].strip()
            fontStyle   = font[2].strip()
            fontStretch = font[3].strip()
            fontWeight  = font[4].strip()


            try:
                fontFamily.decode('ascii')
                fontId.decode('ascii')
                fontFile.decode('ascii')
            except:
                logging.error("Unable to load font: " + fontFamily)
                continue

            # ignore stretched fonts, and styles other than italic, and weights we don't know about
            if fontFamily != 'unknown' and fontStretch == "Normal" and (fontStyle == 'Italic' or fontStyle == 'Normal') and (fontWeight == '400' or fontWeight == '700'):

                overallStyle = None
                if fontStyle == 'Normal' and fontWeight =='400':
                    overallStyle = "Regular"
                elif fontStyle == 'Normal' and fontWeight =='700':
                    overallStyle = "Bold"
                elif fontStyle == 'Italic' and fontWeight =='400':
                    overallStyle = "Italic"
                elif fontStyle == 'Italic' and fontWeight == '700':
                    overallStyle = "Bold Italic"

                if overallStyle is not None:
                    if fontFamily not in self.fonts:
                        self.fonts[fontFamily] = dict()
                    self.fonts[fontFamily][overallStyle] = fontId

    def GetFontCount(self):
        return len(self.fonts.keys())

    def GetFamilyList(self):
        ret = self.fonts.keys()
        ret.sort()
        return tuple(ret)

    def GetFontAttributeList(self, fontFamily):
        ret = self.fonts[fontFamily].keys()
        ret.sort(reverse=True)
        return tuple(ret)

    def GetFontId(self, fontFamily, fontStyle):
        return self.fonts[fontFamily][fontStyle]

    def GetBestFontFamilyIdx(self, userChoice=""):
        fontFamilyList = self.GetFamilyList()

        if len(userChoice) and userChoice in fontFamilyList:
            return fontFamilyList.index(userChoice)
        elif 'Impact' in fontFamilyList:
            return fontFamilyList.index('Impact')
        elif 'Arial Rounded MT Bold' in fontFamilyList:
            return fontFamilyList.index('Arial Rounded MT Bold')
        elif 'Arial' in fontFamilyList:
            return fontFamilyList.index('Arial')
        else:
            return 0


#
# Animated Gif Engine
#
# Try to keep this class fully de-coupled from the GUI
#

class AnimatedGif:

    description = "Animated Gif Engine"
    author      = "Justin Todd"

    def __init__(self, config, mediaLocator, workDir, periodicCallback, rootWindow):
        self.conf          = config
        self.workDir       = workDir
        self.callback      = periodicCallback
        self.origURL       = mediaLocator
        self.isUrl         = False
        self.videoWidth    = 0
        self.videoHeight   = 0
        self.videoLength   = None
        self.videoFps      = 0.0
        self.videoPath     = None
        self.videoFileName = ""
        self.imageSequence = []
        self.imageSequenceCropParams = None  # At the moment, used for mac screen grab only. When the image sequence is "extracted" we sneak in the crop operation instead of resizing
        self.fonts         = None
        self.rootWindow    = rootWindow # Needed for mouse cursor
        self.gifCreated    = False
        self.gifOutPath    = None  # Warning: Don't use this directly!
        self.lastSavedGifPath = None
        self.overwriteGif  = True
        self.frameDir      = workDir + os.sep + 'original'
        self.resizeDir     = workDir + os.sep + 'resized'
        self.processedDir  = workDir + os.sep + 'processed'
        self.captureDir    = workDir + os.sep + 'capture'
        self.maskDir       = workDir + os.sep + 'mask'
        self.downloadDir   = workDir + os.sep + 'downloads'
        self.previewFile   = workDir + os.sep + 'preview.gif'
        self.vidThumbFile  = workDir + os.sep + 'thumb.png'
        self.blankImgFile  = workDir + os.sep + 'blank.gif'
        self.audioClipFile = workDir + os.sep + 'audio.wav'



        self.OverwriteOutputGif(self.conf.GetParamBool('settings', 'overwriteGif'))

        if self.conf.GetParam('paths', 'gifOutputPath').lower() == 'default':
            self.gifOutPath = self.GetDefaultOutputDir() + os.sep + 'insta.gif'
        else:
            self.gifOutPath = self.conf.GetParam('paths', 'gifOutputPath')

        startupLog = "AnimatedGif:: media: ["+mediaLocator+"], workingDir: ["+workDir+"], gifOut: ["+self.GetNextOutputPath()+"]"
        logging.info(startupLog)

        # if mediaLocator == self.GetGifOutputPath():
        #     self.FatalError("This file is in-use by Instagiffer!")

        if not os.path.exists(os.path.dirname(self.gifOutPath)):
            os.makedirs(os.path.dirname(self.gifOutPath))
            if not os.path.exists(os.path.dirname(self.gifOutPath)):
                self.FatalError("Failed to create gif output directory: " + os.path.dirname(self.gifOutPath))
        if not os.path.exists(self.frameDir):
            os.makedirs(self.frameDir)
            if not os.path.exists(self.frameDir):
                self.FatalError("Failed to create working directory: " + self.frameDir)
        if not os.path.exists(self.resizeDir):
            os.makedirs(self.resizeDir)
            if not os.path.exists(self.resizeDir):
                self.FatalError("Failed to create working directory: " + self.resizeDir)
        if not os.path.exists(self.processedDir):
            os.makedirs(self.processedDir)
            if not os.path.exists(self.processedDir):
                self.FatalError("Failed to create working directory: " + self.processedDir)
        if not os.path.exists(self.downloadDir):
            os.makedirs(self.downloadDir)
            if not os.path.exists(self.downloadDir):
                self.FatalError("Failed to create working directory: " + self.downloadDir)
        if not os.path.exists(self.captureDir):
            os.makedirs(self.captureDir)
            if not os.path.exists(self.captureDir):
                self.FatalError("Failed to create working directory: " + self.captureDir)
        if not os.path.exists(self.maskDir):
            os.makedirs(self.maskDir)
            if not os.path.exists(self.maskDir):
                self.FatalError("Failed to create working directory: " + self.maskDir)

        self.LoadFonts()
        self.CheckPaths()
        self.DeleteResizedImages()
        self.DeleteExtractedImages()
        self.DeleteProcessedImages()
        self.DeleteCapturedImages()
        self.DeleteMaskImages()
        self.DeleteAudioClip()

        #self.DeleteGifOutput()

        mediaLocator = self.ResolveUrlShortcutFile(mediaLocator)


        logging.info("Analyzing the media path to determine what kind of video this is...")
        self.isUrl      = IsUrl(mediaLocator)
        captureRe       = re.findall('^::capture ([\.0-9]+) ([\.0-9]+) ([0-9]+)x([0-9]+)\+(\-?[0-9]+)\+(\-?[0-9]+) cursor=(\d+) retina=(\d+) web=(\d+)$', mediaLocator)
        isImgSeq        = "|" in mediaLocator or IsPictureFile(mediaLocator)

        if captureRe and len(captureRe[0]) == 9:
            logging.info("Media locator indicates screen capture")
            capDuration  = float(captureRe[0][0])
            capTargetFps = float(captureRe[0][1])
            capWidth     = int(captureRe[0][2])
            capHeight    = int(captureRe[0][3])
            capX         = int(captureRe[0][4])
            capY         = int(captureRe[0][5])
            cursorOn     = int(captureRe[0][6])
            retina       = int(captureRe[0][7])
            web          = int(captureRe[0][8])

            self.Capture(capDuration, capTargetFps, capWidth, capHeight, capX, capY, cursorOn, retina, web)

        elif isImgSeq:
            logging.info("Media Locator is an image sequence")

            for fname in mediaLocator.split("|"):
                if len(fname):
                    self.imageSequence.append(fname)

            # Arbitrarily pick an FPS of 10 for image sequences
            self.videoFps = 10.0

        else:
            if self.isUrl:
                logging.info("Media locator is a URL")
                self.downloadQuality = self.conf.GetParam('settings', 'downloadQuality')
                self.videoPath       = self.DownloadVideo(mediaLocator)
            else:
                logging.info("Media locator points to a local file")
                self.videoPath     = CleanupPath(mediaLocator)
                self.videoFileName = os.path.basename(mediaLocator)

        self.GetVideoParameters()


    def ResolveUrlShortcutFile(self, filename):
        """Given a Windows .url filename, returns the main URL, or argument passed in if it can't
        find one."""

        fname, fext = os.path.splitext(filename)
        if not fext or len(fext) == 0 or str(fext.lower()) != '.url':
            return filename
    
        # Windows .URL file format is compatible with built-in ConfigParser class.
        config = RawConfigParser()
        try:
            config.read(filename)
        except:
            return filename

        # Return the URL= value from the [InternetShortcut] section.
        if config.has_option('InternetShortcut', 'url'):
            return config.get('InternetShortcut', 'url').strip('"')
        # If there is none, return the BASEURL= value from the [DEFAULT] section.
        if 'baseurl' in config.defaults().keys():
            return config.defaults()['baseurl'].strip('"')
        else:
            return filename


    def GetConfig(self):
        return self.conf

    def Capture(self, seconds, targetFps, width, height, x, y, showCursor, retinaDisplay, web):
        if seconds < 1:
            return False

        # Capture as fast as possible
        imgIdx      = 1
        nowTs       = time.time()
        endTs       = nowTs + seconds
        nextFrameTs = nowTs

        #
        imgDataArray    = []
        imgDimensions   = ()

        if retinaDisplay:
            width  *= 2
            height *= 2
            x      *= 2
            y      *= 2


        resizeRatio = 1.0

        # Max width/height restrictions
        if web:
            maxWH     = int(self.conf.GetParam('screencap', 'webMaxWidthHeight'))
            targetFps = int(self.conf.GetParam('screencap', 'webMaxFps'))

            if width >= height and width > maxWH:
                resizeRatio = maxWH / float(width)
            elif height >= width and height > maxWH:
                resizeRatio = maxWH / float(height)


        while time.time() < endTs:
            # Rate-limiting
            if targetFps != 0:
                nowTs = time.time()
                if nowTs < nextFrameTs:
                    time.sleep(nextFrameTs - nowTs)
                nextFrameTs = time.time() + 1.0/targetFps

            # Filename
            capFileName = self.GetCapturedImagesDir() + 'cap%04d' % (imgIdx)

            if ImAPC():
                capFileName += '.bmp'

                try:
                    img = ImageGrab.grab((x, y, x+width, y+height))
                except MemoryError:
                    self.callback(True)
                    self.FatalError("Ran out of memory during screen capture. Try recording a smaller area, or decreasing your duration.")
                    return False
                
                imgDimensions = img.size

                if showCursor:
                    # Get mouse cursor position
                    cursorX, cursorY = self.rootWindow.winfo_pointerxy()

                    if cursorX > x and cursorX < x+width and cursorY > y and cursorY < y + height:
                        # Draw Cursor (Just a dot for now)
                        r    = 2 # radius
                        draw = ImageDraw.Draw(img)
                        draw.ellipse((cursorX-x-r, cursorY-y-r, cursorX-x+r, cursorY-y+r), fill="#ffffff", outline="#000000")

                if self.conf.GetParamBool('screencap', 'DirectToDisk'):
                    img.save(capFileName)
                else:
                    #imgDataArray.append(img.tostring()) # PIL
                    imgDataArray.append(img.tobytes()) # PILLOW

            elif ImAMac():
                capFileName += '.bmp' # Supported formats: png, bmp jpg

                scrCapCmd  = "screencapture -x "

                if showCursor:
                    scrCapCmd += "-C "

                scrCapCmd += "\"%s\"" % (capFileName)

                os.system(scrCapCmd)

            self.imageSequence.append(capFileName)
            imgIdx += 1
            self.callback(False)

        # Post-process
        if ImAPC():
            if not self.conf.GetParamBool('screencap', 'DirectToDisk'):
                logging.info("Using fps-optimized screen cap")

                frameCount = 0
                for x in range(0, len(imgDataArray)):
                    try:
                        capPath = self.imageSequence[frameCount]
                    except IndexError:
                        break
                    # PIL uses fromstring
                    PIL.Image.frombytes('RGB', imgDimensions, imgDataArray[x]).resize((int(width*resizeRatio), int(height*resizeRatio)), PIL.Image.ANTIALIAS).save(capPath)
                    if os.path.exists(capPath):
                        frameCount += 1
                    else:
                        logging.error("Capture file " + capPath + " was not saved to disk for some reason")
                
                # Trim the list to the actual size
                missingCount = len(self.imageSequence) - frameCount
                if missingCount != 0:
                    logging.error("Not all capture files were accounted for: %d missing " % (missingCount))
                    self.imageSequence = self.imageSequence[0:min(frameCount, len(self.imageSequence))]


        # Screen capper for Mac can't crop a specific region, so we need to do it
        # Todo: for some reason, PNG to PNG doesn't work!!
        if ImAMac():
            for i in range(0, len(self.imageSequence)):
                newFileName = os.path.dirname(self.imageSequence[i]) + '/' + os.path.splitext(os.path.basename(self.imageSequence[i]))[0] + '.jpg'

                cmdConvert = '"%s" -comment "Converting captured frames:%d" -comment "instagiffer" "%s" -quality 100%% %s "%s"' % \
                    (
                        self.conf.GetParam('paths','convert'),
                        i * 100 / len(self.imageSequence),
                        self.imageSequence[i],
                        "-crop %dx%d+%d+%d" % (width, height, x, y),
                        newFileName
                    )

                self.imageSequence[i] = newFileName
       
                if not RunProcess(cmdConvert, self.callback, False, False):
                    self.FatalError("Unable to crop screen capture frame: " + os.path.basename(self.imageSequence[x]))

            self.callback(True)

        self.videoLength = "00:00:%02d.000" % (seconds)
        self.videoFps    = imgIdx/seconds
        self.callback(True)
        logging.info("Capture complete. FPS acheived: %f" % (self.videoFps))

        return True

    def CheckPaths(self):
        if not os.access(os.path.dirname(self.gifOutPath), os.W_OK):
            logging.error("Warning. " + os.path.dirname(self.gifOutPath) + " is not writable")

        if not os.path.exists(self.conf.GetParam('paths','ffmpeg')):
            self.FatalError("ffmpeg not found")
        elif not os.path.exists(self.conf.GetParam('paths','convert')):
            self.FatalError("imagemagick convert not found")
        elif not os.path.exists(self.conf.GetParam('paths','youtubedl')):
            self.FatalError("Youtube-dl not found")
        # elif not os.path.exists(self.conf.GetParam('paths','gifsicle')):
        #     self.FatalError("gifsicle not found")            
        elif self.videoPath is not None and not os.path.exists(self.videoPath):
            self.FatalError("Local video file '" + self.videoPath + "' does not exist")

        logging.info("Check paths... OK")
        return True

    def LoadFonts(self):
        logging.info("Retrieve font list...")

        runCallback = None
        statBarCB   = DefaultOutputHandler

        def FontConfOutHandler(unused1, unused2, unused3):
            return "First time running Instagiffer for Mac. Configuring fonts. This will take a few minutes...", None

        if ImAMac():
            fontCacheDir = './macdeps/im/var/cache/fontconfig' #expanduser("~") + '/.cache/fontconfig'

            if not os.path.exists(fontCacheDir):
                NotifyUser("First Time", "Welcome to Instagiffer for Mac! Before you can use text features, I need to build a font database. This will take a few minutes.")
                logging.info("First run. Need to build font cache first: " + fontCacheDir)
                runCallback = self.callback
                statBarCB   = FontConfOutHandler

        cmdListFonts       = '"%s" -list font' % (self.conf.GetParam('paths', 'convert'))
        (fontsOutput, err) = RunProcess(cmdListFonts, callback=runCallback, returnOutput=True, outputTranslator=statBarCB)
        self.fonts         = ImagemagickFont(fontsOutput)

        return True

    def GetFonts(self):
        return self.fonts

    def SetSavePath(self, savePath):
        self.gifOutPath = savePath

    def RotateImageFile(self, fileName, rotateDegrees):
        if rotateDegrees % 360 == 0:
            return True

        cmdRotate = '"%s" "%s" -rotate %d -alpha remove -alpha off "%s"' % \
            (
                self.conf.GetParam('paths', 'convert'),
                fileName,
                rotateDegrees,
                fileName
            )

        if not RunProcess(cmdRotate, self.callback, False):
            self.FatalError("Unable to rotate image %s by %d degrees" % (fileName, rotateDegrees))
            return False

        return True

    def ExportFrames(self, start, end, prefix, includeCropAndResize, rotateDeg, path):
        files = []

        if includeCropAndResize:
            files = self.GetResizedImageList()
        else:
            files = self.GetExtractedImageList()
        
        logging.info("Export frames %d to %d" % (start,end))
        x = 1

        for i in range(start, end + 1):
            fromFile = files[i - 1]
            toFile   = "%s%s%04d.png" % (path + os.sep, prefix, x)
            logging.info("Export %s to %s..." % (fromFile, toFile))

            try:
                shutil.copy(fromFile, toFile)
            except:
                self.callback(True)
                return False
                #self.FatalError("Unable to export frames to the directory specified. Are you sure you can write files to this location?")

            self.RotateImageFile(toFile, rotateDeg)

            self.callback(False)
            x += 1
  
        self.callback(True)
        return True
 
    # If manual deletions are made, the enumumeration gets messed up, which screws up the import
    def ReEnumerateExtractedFrames(self):
        if not self.ExtractedImagesExist(): 
            return True
        return self.ReEnumeratePngFrames(self.GetExtractedImagesDir(), self.GetExtractedImageList())


    def ReEnumeratePngFrames(self, directory, imageList):
        imageList.sort()
        retVal = True

        x = 1

        if len(imageList) > 0:
            logging.info("Re-enumerate %d files starting with %s" % (len(imageList), imageList[0]))

        for fromFile in imageList:
            self.callback(False)

            toFile = "%simage%04d.png" % (directory + os.sep, x)
            #logging.info("Re-enumerate %s to %s" % (fromFile, toFile))
            try:
                shutil.move(fromFile, toFile)
            except:
                retVal = False
                break

            x += 1

        self.callback(True)

        return retVal

    def ReverseFrames(self):
         # Get current image list
        currentImgList = self.GetExtractedImageList()
        numImgs        = len(currentImgList)     

        def GetOrigName(idx):
            return "%simage%04d.png" % (self.GetExtractedImagesDir() + os.sep, idx)

        def GetRenamedName(idx):
            return "%scurrent_image%04d.png" % (self.GetExtractedImagesDir() + os.sep, idx)

        for x in range(0, len(currentImgList)):
            toFile   = GetRenamedName(x+1)
            logging.info("Temporarily rename image %s to %s" % (currentImgList[x], toFile))
            shutil.move(currentImgList[x], toFile)

        for x in range(0, len(currentImgList)):
            fromFile = GetRenamedName(numImgs - x)
            toFile   = GetOrigName(x + 1)
            logging.info("Move %s to %s" % (fromFile, toFile))
            shutil.move(fromFile, toFile)

        return True


    def CreateBlankFrame(self, color):
        cmdConvert = '"%s" -size %dx%d xc:%s "%s"' % \
            (
                self.conf.GetParam('paths', 'convert'),
                self.GetVideoWidth(),
                self.GetVideoHeight(),
                color,
                self.blankImgFile
            )

        if not RunProcess(cmdConvert, self.callback, False) or not os.path.exists(self.blankImgFile):
            self.FatalError("Couldn't create blank image!")

        return True
        

    def CreateCrossFade(self, start, end):
        totCount = self.GetNumFrames()
        if start > end:
            xfadeFrames = totCount - (start - end)
        else:
            xfadeFrames = end-start

        if xfadeFrames < 3:
            return False

        if xfadeFrames % 2:
            if end < totCount:
                xfadeFrames += 1
            elif start > 1:
                xfadeFrames += 1
                start -= 1

        xfadeLen = xfadeFrames/2

        logging.info("Create cross fade between %d and %d (%d fade frames) - fade length: %d - %d frames total" % (start, end, xfadeFrames, xfadeLen, totCount))

        origImgList = self.GetExtractedImageList()

        # Add up to start
        for x in range(0, xfadeLen):
            fadePercent = (x+1)*100/(xfadeLen+1)
            ia          = (start-1+x) % totCount
            ib          = (start-1+x+xfadeLen)%totCount

            fa = origImgList[ia]
            fb = origImgList[ib]

            logging.info('xfade %d with %d by %d percent' % (ia+1, ib+1, fadePercent))

            cmdConvert = '"%s" -comment "Creating cross-fade:%d" "%s" "%s" -alpha on -compose dissolve -define compose:args=%d -composite "%s"' % \
                (
                    self.conf.GetParam('paths', 'convert'),
                    x*100/xfadeLen,
                    fa,
                    fb,
                    fadePercent,
                    fa
                )

            if not RunProcess(cmdConvert, self.callback, False):
                self.DeleteExtractedImages()
                self.FatalError("Couldn't fade!")

            try:
                os.remove(fb)
            except:
                self.DeleteExtractedImages()
                self.FatalError("Couldn't delete frame: " + fb)               

        if not self.ReEnumerateExtractedFrames():
            self.FatalError("Failed to re-enumerate frames")

        return True


    def ImportFrames(self, start, importedImgList, reverseImport, insertAfter, riffleShuffle, keepAspectRatio):
        logging.info("Import image sequence: " + ", ".join(importedImgList))

        importedImgList.sort()

        numNewFiles = len(importedImgList)

        if numNewFiles <= 0:
            return False

        # Check for blank frames
        for x in range(0, len(importedImgList)):
            i = importedImgList[x]
            if i.startswith("<") and i.endswith(">"):
                self.CreateBlankFrame(i.strip("<>"))
                importedImgList[x] = self.blankImgFile

        if insertAfter:
            start += 1

        # Get current image list
        currentImgList = self.GetExtractedImageList()

        # Temporarily rename existing images
        for x in range(0, len(currentImgList)):
            toFile   = "%scurrent_image%04d.png" % (self.GetExtractedImagesDir(), x + 1)
            logging.info("Temporarily rename image %s to %s" % (currentImgList[x], toFile))
            
            if currentImgList[x] in importedImgList:
                shutil.copy(currentImgList[x], toFile)
            else:
                shutil.move(currentImgList[x], toFile)
            
            currentImgList[x] = toFile

        # Temporarily rename and resize imported images
        logging.info("Rename, resize and rotate imported image sequence")

        def GetImportFileName(idx):
            return "%simported_image%04d.png" % (self.GetExtractedImagesDir(), x)

        x             = 1
        totalCount    = len(importedImgList)
        newImportList = list()
        for importFile in importedImgList:
            toFile = GetImportFileName(x) # "%simported_image%04d.png" % (self.GetExtractedImagesDir() + os.sep, x)
            logging.info("Copy and resize '%s' to '%s'" % (importFile, toFile))

            aspectRatioModifier=""
            if keepAspectRatio:
                # ( -clone 0 -blur 0x9 -resize %dx%d! ) ( -clone 0 -resize WxH ) -delete 0
                aspectRatioModifier = " -background black -gravity center -extent %dx%d " % (self.GetVideoWidth(), self.GetVideoHeight())
            else:
                aspectRatioModifier = "! "


            # this is a bit weird, because if user imports a gif, the number of frames increases and im blocks for a long time
            percentDone = (x-1) * 100 / len(importedImgList)
            if percentDone > 100 or GetFileExtension(importFile) == 'gif':
                percentDone = -1

            comment    = ' -comment "Importing frames:%d" -comment "instagiffer" ' % (percentDone)
            cmdConvert = '"%s" %s "%s" -resize %dx%d%s "%s"' % \
                (
                    self.conf.GetParam('paths', 'convert'),
                    comment,
                    importFile,
                    self.GetVideoWidth(),
                    self.GetVideoHeight(),
                    aspectRatioModifier,
                    toFile
                )

            if not RunProcess(cmdConvert, self.callback, False, False):
                self.DeleteExtractedImages()
                self.FatalError("Unable to resize import image %s. Import failed!" % (toFile))

            if os.path.exists(toFile):
                newImportList.append(toFile)
                x += 1
            else:
                fname, fext = os.path.splitext(toFile)

                sx = 0
                while True:
                    x      += 1
                    toFile  = GetImportFileName(x)
                    subFile = "%s-%d.png" % (fname, sx)
                    if not os.path.exists(subFile):
                        break
                    sx += 1

                    shutil.move(subFile, toFile)
                    newImportList.append(toFile)

                if sx == 0:
                    self.DeleteExtractedImages()
                    self.FatalError("Import error")

        # Sort alphabetical. Reverse?
        newImportList.sort(reverse = reverseImport)

        # Let the array magic begin
        newImgList = []

        # Add up to start
        for x in range(0, start - 1):
            newImgList.append(currentImgList.pop(0))

        # Add the new frames
        if not riffleShuffle:
            while len(newImportList):
                newImgList.append(newImportList.pop(0))

        # Add the rest of the frames after. Riffle shuffle occurs if there are still imported images in the list
        while len(currentImgList) or len(newImportList):
            if len(currentImgList):
                newImgList.append(currentImgList.pop(0))
            if len(newImportList):
                newImgList.append(newImportList.pop(0))

        # Properly name the files
        for x in range(0, len(newImgList)):
            toFile   = "%simage%04d.png" % (self.GetExtractedImagesDir(), x + 1)
            logging.info("Move %s to %s" % (newImgList[x], toFile))
            shutil.move(newImgList[x], toFile)

        self.callback(True)
        return True

    def GetDefaultOutputDir(self):
        gifDir  = expanduser("~")
        gifDir += os.sep + 'Desktop'

        try:
            gifDir.encode(locale.getpreferredencoding())
        except UnicodeError:
            logging.info("GIF output directory is problematic due to non-latin characters: " + gifDir)
            gifDir = GetFailSafeDir(self.conf, gifDir)

        return gifDir

    def OverwriteOutputGif(self, enable):
        self.overwriteGif = enable

    def GetLastGifOutputPath(self):
        return self.lastSavedGifPath

    def GetNextOutputPath(self):
        fileName = self.gifOutPath

        if self.overwriteGif == False:
            # If overwrite is off, figure out what next file is
            origFileName = self.gifOutPath
            prevFileName = origFileName
            idx          = 1
            largestTs    = 0

            while True:
                if not os.path.isfile(fileName):
                    break
                # else:
                #     fileTs = os.stat(fileName).st_mtime
                #     if fileTs < largestTs:
                          # broken sequence                    
                #     else:
                #         largestTs = fileTs

                prevFileName = fileName
                fileName     = os.path.dirname(origFileName) + os.sep + os.path.splitext(os.path.basename(origFileName))[0] + "%03d.%s" % (idx, self.GetFinalOutputFormat())
                idx         += 1


        if len(fileName) == 0:
            self.FatalError("Configuration error detected. No GIF output path specified.")

        return fileName


    # Error handler
    def FatalError(self, message):
        logging.error("FatalError occurred in the animation core: " + message)
        logging.debug("Stack:")
        for line in traceback.format_stack():
            logging.error(line.strip())
        
        logging.debug(self.conf)
        self.callback(True)

        raise RuntimeError(message)

    def GetVideoThumb(self, timeStr, maxWidthHeight):
        if not self.SourceIsVideo():
            return False

        RunProcess('"' + self.conf.GetParam('paths', 'ffmpeg') + \
                   '" -loglevel panic -i "%s" -y -ss %s -vframes 1 "%s"' % ( self.videoPath, timeStr, self.GetThumbImagePath()),
                   None, False)

        return True

    def GetThumbImagePath(self):
        return self.vidThumbFile

    def ThumbFileExists(self):
        return os.path.exists(self.GetThumbImagePath())

    def GetThumbAge(self):
        if self.ThumbFileExists():
            return time.time() - os.stat(self.GetThumbImagePath()).st_mtime
        else:
            return 1000


    def GetVideoParameters(self):
        mediaPath = None

        if self.videoPath == None:
            mediaPath = self.imageSequence[0]
        else:
            # Check path against invalid extensions list
            invalidExtensions = ['.exe', '.bat']

            for invalidExtension in invalidExtensions:
                if invalidExtension in self.videoPath:
                     self.FatalError("This video contains an unsupported file extension")

            mediaPath = self.videoPath

        logging.info("Extracting video information from " + mediaPath)

        if not os.path.exists(mediaPath):
            self.FatalError("'" + mediaPath + "' does not exist!")
  
        stdout, stderr = RunProcess('"' + self.conf.GetParam('paths','ffmpeg') + '" -i "' + CleanupPath(mediaPath) + '"', None, True)

        pattern = re.compile(r'Stream.*Video.* ([0-9]+)x([0-9]+)')
        match   = pattern.search(stderr)

        if match:
                w, h = map(int, match.groups()[0:2])
                self.videoWidth = w
                self.videoHeight = h
        else:
            self.FatalError("Unable to get video width and height parameters.")

        # Display aspect ratio - non square pixels
        pattern = re.compile(r'Stream #0.+Video.+\[SAR (\d+):(\d+) DAR (\d+):(\d+)\]') # older versions of ffmpeg
        match   = pattern.search(stderr)

        if match:
            sarX, sarY, darX, darY = map(int, match.groups()[0:4])
            
            rDar = darX/float(darY)
            rSar = sarX/float(sarY)
            
            if rSar != 1.0 and rDar != rSar:
                logging.info("Storage aspect ratio (%.2f) differs from display aspect ratio (%.2f)" % (rSar, rDar))
                self.videoWidth = self.videoHeight * rDar

        # Side Rotation
        pattern = re.compile(r'\s+rotate\s+:\s+(90|270|-90|-270)')
        match   = pattern.search(stderr)

        if match:
            logging.info("Side rotation detected")
            rotation = int(match.groups()[0])
            self.videoWidth, self.videoHeight = self.videoHeight, self.videoWidth

        # Try to get length
        pattern = re.compile(r'Duration: ([0-9\.:]+),')
        match   = pattern.search(stderr)

        if self.videoPath and match:
            self.videoLength = match.groups()[0]

        # Try to get fps
        pattern = re.compile(r'Video:.+?([0-9\.]+) tbr')
        match   = pattern.search(stderr)

        if self.videoPath and match:
            self.videoFps = match.groups()[0]
        elif self.videoFps <= 0.0:
            self.videoFps = 10.0
            logging.info("Unable to determine frame rate! Arbitrarily setting it to %d" % (self.videoFps))

        logging.info("Video Parameters: %dx%d (%d:%d or %0.3f:1); %d fps" % (
                self.GetVideoWidth(),
                self.GetVideoHeight(),
                self.GetVideoWidth()/gcd(self.GetVideoWidth(), self.GetVideoHeight()),
                self.GetVideoHeight()/gcd(self.GetVideoWidth(), self.GetVideoHeight()),
                self.GetVideoWidth()/float(self.GetVideoHeight()),
                self.GetVideoFps()))

        return True

    def GetResizedImagesDir(self):
        return self.resizeDir + os.sep

    def GetResizedImagesLastModifiedTs(self):
        if self.ResizedImagesExist():
            largestTimestamp = os.stat(self.GetResizedImagesDir()).st_mtime
            files            = glob.glob(self.GetResizedImagesDir() + '*')

            for f in files:
                if os.stat(f).st_mtime > largestTimestamp:
                    largestTimestamp = os.stat(f).st_mtime
            return largestTimestamp
        else:
            return 0

    def GetResizedImageList(self, idx=None):
        ret = []
        files = glob.glob(self.GetResizedImagesDir() + '*')
        for f in files:
            if idx is not None:
                origFiles = self.GetExtractedImageList()
                f = self.GetResizedImagesDir() + os.path.basename(origFiles[idx-1])
                return f
                # doesn't handle deleted frames - DOESNT WORK
                # imageName = "image%04d.png" % (idx)
                # if imageName in f:
                #     return f

            ret.append(f)



        return ret

    def ResizedImagesExist(self):
        count = 0
        files = glob.glob(self.GetResizedImagesDir() + '*')
        for f in files:
            count = count + 1

        if count > 0:
            return True
        else:
            return False

    def DeleteResizedImages(self):
        files = glob.glob(self.resizeDir + os.sep + '*')
        for f in files:
            try:
                os.remove(f)
            except: # WindowsError:
                logging.error("Can't delete %s" % (f))

    def GetExtractedImagesDir(self):
        return self.frameDir + os.sep

    def GetExtractedImagesLastModifiedTs(self):
        if self.ExtractedImagesExist(): 
            largestTimestamp = os.stat(self.GetExtractedImagesDir()).st_mtime
            files            = glob.glob(self.GetExtractedImagesDir() + '*')

            for f in files:
                if os.path.exists(f) and os.stat(f).st_mtime > largestTimestamp:
                    largestTimestamp = os.stat(f).st_mtime
            return largestTimestamp
        else:
            return 0

    def ExtractedImagesExist(self):
        count = 0
        files = glob.glob(self.GetExtractedImagesDir() + '*')
        for f in files:
            count = count + 1

        if count > 0:
            return True
        else:
            return False

    def GetNumFrames(self):
        return len(self.GetExtractedImageList())

    def GetExtractedImageList(self):
        ret = []
        files = glob.glob(self.GetExtractedImagesDir() + '*')
        for f in files:
            ret.append(f)
        return ret

    def DeleteExtractedImages(self):
        files = glob.glob(self.GetExtractedImagesDir() + '*')
        for f in files:
            try:
                os.remove(f)
            except: # WindowsError:
                errStr = "Can't delete the following file:\n\n%s\n\nIs it open in another program?" % (f)
                self.FatalError(errStr)


    def GetProcessedImagesDir(self):
        return self.processedDir + os.sep

    def GetProcessedImageList(self):
        ret = []
        files = glob.glob(self.GetProcessedImagesDir() + '*.' + self.GetIntermediaryFrameFormat())
        for f in files:
            ret.append(f)
        return ret

    def DeleteProcessedImages(self):
        if os.path.exists(self.previewFile):
            try:
                os.remove(self.previewFile)
            except:
                pass

        files = glob.glob(self.GetProcessedImagesDir() + '*')

        for f in files:
            try:
                os.remove(f)
            except: # WindowsError:
                errStr = "Can't delete %s. Is it open in another program?" % (f)
                self.FatalError(errStr)

    def GetCapturedImagesDir(self):
        return self.captureDir + os.sep

    def DeleteCapturedImages(self):
        files = glob.glob(self.GetCapturedImagesDir() + '*')
        for f in files:
            os.remove(f)

    def GetGifLastModifiedTs(self):
        if self.GifExists():
            return os.stat(self.GetLastGifOutputPath()).st_mtime
        else:
            return 0

    def GifExists(self):
        return  self.gifCreated and os.path.exists(self.GetLastGifOutputPath())

    def DeleteGifOutput(self):
        if not self.overwriteGif:
            if os.path.exists(self.gifOutPath):
                try:
                    os.remove(self.gifOutPath)
                except:
                    self.FatalError("Failed to delete GIF out file. Is it use?")


    def UploadGifToImgur(self):
        if not self.GifExists():
            self.FatalError("Can't find the GIF. Unable to upload to Imgur")
            return None

        try:
            b64Image = base64.b64encode(open(self.GetLastGifOutputPath(), 'rb').read())
        except:
            return None

        data = {
            'key': __imgurcid__, 
            'image': b64Image,
            'type': 'base64',
            'name': 'Instagiffer.gif',
            'title': 'Created and uploaded using Instagiffer'
        }

        req = urllib2.Request("https://api.imgur.com/3/upload.json", urllib.urlencode(data))
        req.add_header('Authorization', 'Client-ID ' +  __imgurcid__)

        try:
            response = urllib2.urlopen(req)
        except:
            return None

        response = json.loads(response.read())

        imgUrl = str(response[u'data'][u'link'])
        logging.info("Imgur URL: " + imgUrl)

        if self.rootWindow is not None:
            self.rootWindow.clipboard_clear()
            self.rootWindow.clipboard_append(imgUrl)

        return imgUrl

    def GetMaskFileName(self, maskIdx):
        return "%simage%04d.png" % (self.maskDir + os.sep, maskIdx + 1)


    def DeleteMaskImages(self):
        files = glob.glob(self.maskDir + os.sep + '*')
        for f in files:
            os.remove(f)


    def CopyFramesToResizeFolder(self):
        # Copy extracted images over again
        files = glob.glob(self.frameDir + os.sep + '*')
        for f in files:
            self.callback(False)
            shutil.copy(f, self.resizeDir)
        self.callback(True)

    def CopyFramesToProcessedFolder(self):
        # Copy extracted images over again
        files = glob.glob(self.resizeDir + os.sep + '*')
        for f in files:
            shutil.copy(f, self.processedDir)


    def IsDownloadedVideo(self):
        return self.isUrl

    def GetVideoFileName(self):
        if self.videoFileName != "":
            return self.videoFileName

        if self.isUrl and len(self.origURL):
            cmdVideoTitle = \
                '"' + self.conf.GetParam('paths','youtubedl') + '"' \
                + ' --get-filename ' \
                + ' "' + self.origURL + '"'

            stdout, stderr = RunProcess(cmdVideoTitle, self.callback, True)

            if stdout != "":
                self.videoFileName = stdout.strip()
                return self.videoFileName

        return self.videoFileName


    def SaveOriginalVideoAs(self, newFileName):
        if len(self.videoPath):
            self.callback(False)
            shutil.copy(self.videoPath, newFileName)
        self.callback(True)

    def GetDownloadedQuality(self):
        return self.downloadQuality


    def DeleteAudioClip(self):
        try:
            os.remove(self.GetAudioClipPath())
        except:
            pass


    def GetAudioClipPath(self):
        if os.path.exists(self.audioClipFile):
            return self.audioClipFile
        else:
            return None 

    def ExtractAudioClip(self):
        audioPath    = self.conf.GetParam('audio', 'path')
        startTimeStr = float(self.conf.GetParam('audio', 'startTime'))
        volume       = int(self.conf.GetParam('audio', 'volume'))/100.0
        durationSec  = self.GetTotalRuntimeSec()

        if len(audioPath) == 0:
            return None

        try:
            os.remove(self.audioClipFile)
        except:
            pass

        cmdExtractImages = u'"%s" -y -v verbose -ss %s -t %.1f -i "%s" -af "volume=%.1f" "%s"' % \
            (
                self.conf.GetParam('paths', 'ffmpeg'),
                startTimeStr,
                durationSec,
                audioPath,
                volume,
                self.audioClipFile,
            )

        success = RunProcess(cmdExtractImages, self.callback)

        if not success:
            return None
        else:
            return self.GetAudioClipPath()


    def DownloadAudio(self, url):
        # Make sure they don't download a playlist
        if url.lower().find("youtube") != -1 and url.find('&list=') != -1:
            logging.info("Youtube playlist detected. Removing playlist component from URL")
            url, sep, extra = url.partition('&list=')

        downloadFileName = self.downloadDir + os.sep + 'audiofile_' + str(uuid.uuid4())

        cmdVideoDownload = \
            '"' + self.conf.GetParam('paths','youtubedl') + '"' \
            + ' -v ' \
            + ' --ffmpeg-location "' + self.conf.GetParam('paths','ffmpeg') + '"' \
            + ' --restrict-filenames ' \
            + ' --no-check-certificate ' \
            + ' --newline ' \
            + ' -f bestaudio '  \
            + ' -o "' + downloadFileName + '"' \
            + '   "' + url + '"'
           #+ ' -o "' + self.downloadDir + os.sep + '%(title)s.%(ext)s"' \

        stdout, stderr = RunProcess(cmdVideoDownload, self.callback, True)

        # matches1 = re.findall('\[download\] (.+) has already been downloaded', stdout, re.MULTILINE)
        # matches2 = re.findall(' Destination: (.+)', stdout, re.MULTILINE)

        # if matches1:
        #     downloadFileName = matches1[0]
        # elif matches2:
        #     downloadFileName = matches2[0]

        if not os.path.exists(downloadFileName):
            logging.error("youtube-dl failed to download audio track")
            self.FatalError(errStr)

        return downloadFileName

    def DownloadVideo(self, url):
        downloadFileName = self.downloadDir + os.sep + 'videofile_' + str(uuid.uuid4())

        maxHeight = 360

        if self.downloadQuality   == 'Low':
            maxHeight = 240
        elif self.downloadQuality == 'Medium':
            maxHeight = 360
        elif self.downloadQuality == 'High':
            maxHeight = 720            
        elif self.downloadQuality == 'Highest':
            maxHeight = 1080

        # Make sure they don't download a playlist
        if url.lower().find("youtube") != -1 and url.find('&list=') != -1:
            logging.info("Youtube playlist detected. Removing playlist component from URL")
            url, sep, extra = url.partition('&list=')

        # Build format str
        fmtStr = '[height<=?' + str(maxHeight) +  '] '
        if self.downloadQuality == 'Highest':
            fmtStr = 'bestvideo'

        fmtStr = ' --format ' + fmtStr

        # Don't specify
        if self.downloadQuality == 'None':
            fmtStr = "" 

        cmdVideoDownload = \
            '"' + self.conf.GetParam('paths','youtubedl') + '"' \
            + ' -v -k ' \
            + ' --ffmpeg-location /dont/use ' \
            + ' --no-check-certificate ' \
            + ' --newline ' \
            + fmtStr \
            + ' -o "' + downloadFileName + '"' \
            + '   "' + url + '"'

        stdout, stderr = RunProcess(cmdVideoDownload, self.callback, True)

        if not os.path.exists(downloadFileName):
            # Video didn't download. Let's see what happened
            errStr = "Failed to download video\n\n"
            for line in stderr.splitlines(True):
                if 'ERROR' in line:
                    if 'This video does not exist' in line:
                        errStr += "Video was not found."
                    if 'Community Guidelines' in line:
                        errStr += 'Video removed because it broke the rules'
                    elif 'is not a valid URL' in line:
                        errStr += "This is an invalid video URL"
                    elif '10013' in line or '11001' or "CERTIFICATE_VERIFY_FAILED" in line:
                        errStr += "Unable to download video. Bad URL? Is it a private video? Is your firewall blocking Instagiffer?"
                    elif 'Signature extraction failed' in line or "HTTP Error 403" in line:
                        errStr += "There appears to be copyright protection on this video. This frequently occurs with music videos. Ask the Instagiffer devs to release a new version to get around this, or use the screen capture feature."
                    else:
                        errStr += line

            logging.error("youtube-dl failed to download video")
            logging.error(stdout)
            logging.error(stderr)
            self.FatalError(errStr)

        return downloadFileName

    def SourceIsVideo(self):
        if self.videoPath == None and len(self.imageSequence) <= 0:
            self.FatalError("Something is wrong. No video, and no image sequence!")
        return self.videoPath is not None

    def IsSameVideo(self, pathCheck, dlQuality):
        if self.SourceIsVideo() and self.isUrl and self.origURL == pathCheck and self.downloadQuality == dlQuality:
            return True
        else:
            return False

    def ExtractFrames(self):
        #self.DeleteResizedImages()
        self.DeleteExtractedImages()

        doDeglitch = False

        # Video source?
        if self.SourceIsVideo():

            startTimeStr = self.conf.GetParam('length','starttime')
            durationSec  = float(self.conf.GetParam('length','durationsec'))

            # User chose random start time
            if startTimeStr.lower() == 'random':
                vidLenMs = DurationStrToMillisec(self.videoLength)
                startTimeStr = MillisecToDurationStr(randrange(vidLenMs))
                logging.info("Pick random start time between 0 and %d ms -> %s" % (vidLenMs, startTimeStr))

            # Grab the previous second. This is where the error is found
            if self.conf.GetParamBool('settings', 'fixSlowdownGlitch'):
                startTimeMs = DurationStrToMillisec(startTimeStr)

                if startTimeMs > 2000:
                    startTimeMs  = startTimeMs - 2000
                    startTimeStr = MillisecToDurationStr(startTimeMs)
                    durationSec  = durationSec + 2.0
                    doDeglitch   = True
                    logging.info("Fixing FPS glitch. New start time: " + startTimeStr + "; New duration: " + str(durationSec))

            # FFMPEG options (order matters!):
            # -sn: disable subtitles?
            # -t:  duration
            # -ss: start time
            # -i:  video path
            # -r:  frame rate

            if not __release__:
                verbosityLevel = "verbose"
            else:
                verbosityLevel = "verbose" #error"

            cmdExtractImages = u'"%s" -v %s -sn -t %.1f -ss %s -i "%s" -r %s "%simage%%04d.png"' % \
                (
                    self.conf.GetParam('paths', 'ffmpeg'),
                    verbosityLevel,
                    durationSec,
                    startTimeStr,
                    self.videoPath,
                    self.conf.GetParam('rate',  'framerate'),
                    self.frameDir + os.sep
                )

            success = RunProcess(cmdExtractImages, self.callback)

            if not success:
                self.DeleteExtractedImages()

        else: # Sequence
            resizeArg = " -resize %dx%d!" % (self.GetVideoWidth(), self.GetVideoHeight())

            frameCount = 1
            for x in range(len(self.imageSequence)):
                if os.path.exists(self.imageSequence[x]):
                    cmdConvert = '"%s" -comment "Importing image seqeuence:%d" -comment "instagiffer" "%s" %s +set date:create +set date:modify "%s%s"' % \
                        (
                            self.conf.GetParam('paths','convert'),
                            x*100/len(self.imageSequence),
                            self.imageSequence[x],
                            resizeArg,
                            self.frameDir + os.sep,
                            "image%04d.png" % (frameCount)
                        )

                    if RunProcess(cmdConvert, self.callback, False, False):
                        frameCount += 1
                    else:
                        logging.error("Unable to convert image '" + os.path.basename(self.imageSequence[x]) + "' to png. Conversion failed.")
                else:
                    logging.error("Unable to convert image '" + os.path.basename(self.imageSequence[x]) + "' to png. File not found.")

            self.callback(True)

        # Verify we have at least one extracted frame
        if not os.path.exists(self.frameDir + os.sep + 'image0001.png'):
            if self.GetVideoLength() is not None:

                if DurationStrToMillisec(self.conf.GetParam('length','starttime')) > DurationStrToMillisec(self.GetVideoLength()):
                    self.FatalError("Start time specified is greater than " + self.GetVideoLength() + ".")
                else:
                    self.FatalError("Unsupported file type or DRM-protected.")
            else:
                self.FatalError("Unable to extract images. Your start time might be greater than the video's length, which is unknown.")

        # DEGLITCH
        # Delete the first second's worth of frames
        if doDeglitch:
            #self.callback(False, "De-glitch...")
            deleteCount = 2 * int(self.conf.GetParam('rate', 'framerate'))
            
            logging.info("Deglitch. Remove frames 1 to %d" % deleteCount )

            for x in range(1, deleteCount + 1):
                framePath  = self.frameDir + os.sep
                framePath += u'image%04d.png' % (x)

                if not os.path.exists(framePath):
                    self.FatalError("De-glitch failed. Frame not found: " + framePath)
                try:
                    os.remove(framePath)
                except: # WindowsError:
                    self.FatalError("De-glitch failed. Delete failed: " + framePath)

                self.callback(False)
                #logging.info("Deglitch: Removed " + framePath)

            # renumerate after de-glitch
            if not self.ReEnumerateExtractedFrames():
                self.FatalError("Failed to re-enumerate frames")

        # This command can take a while. Is it even neccesary?
        #self.CopyFramesToResizeFolder()
        return True


    def CheckDuplicates(self, cull = False):
        dupCount = 0
        hashes  = dict()

        for imgPath in self.GetExtractedImageList():
            self.callback(False)

            shahash = hashlib.sha256(open(imgPath, 'rb').read()).digest()

            if shahash in hashes:
                dupCount += 1
                hashes[shahash].append(imgPath)

                if cull == True:
                    try:
                        os.remove(imgPath)
                        logging.info("Removing duplicate frame: %s" % (imgPath))
                    except:
                        logging.error("Can't delete duplicate frame: %s" % (imgPath))

            else:
                hashes[shahash] = [imgPath]

        if cull and dupCount > 0:
            self.ReEnumerateExtractedFrames()

        self.callback(True)

        return dupCount

    def PositionToGravity(self, positionStr):
        # Positioning
        posMapping = \
        {
            'Top Left':     'NorthWest',
            'Top':          'North',
            'Top Right':    'NorthEast',
            'Middle Left':  'West',
            'Center':       'Center',
            'Middle Right': 'East',
            'Bottom Left':  'SouthWest',
            'Bottom':       'South',
            'Bottom Right': 'SouthEast'
        }

        if positionStr in posMapping:
            return posMapping[positionStr]
        else:
            raise ValueError("Invalid position to gravity value")


    # png is prefered
    def GetIntermediaryFrameFormat(self):
        return 'png'


    def GetFinalOutputFormat(self):
        fname, fext = os.path.splitext(self.gifOutPath)
        fext = str(fext).lower()

        fext = fext.strip('.')

        return fext




    def BlitImage(self, layerIdx, beforeFXchain):
        cmdProcImage = ""
        layerId      = "imagelayer%d" % (layerIdx)
        imgPath      = self.conf.GetParam(layerId, 'path')

        if self.conf.GetParamBool(layerId, 'applyFx') != beforeFXchain:
            return ""

        if imgPath is None or imgPath == "":
            return ""

        if not os.path.exists(imgPath):
            self.FatalError("Unable to find specified image file:\n%s" % (imgPath))

        gravity  = self.PositionToGravity(self.conf.GetParam(layerId, 'positioning'))
        resize   = self.conf.GetParam(layerId, 'resize')
        opacity  = self.conf.GetParam(layerId, 'opacity')
        xNudge   = int(self.conf.GetParam(layerId, 'xNudge'))
        yNudge   = int(self.conf.GetParam(layerId, 'yNudge'))

        #-compose dissolve -define compose:args=%d -composite 
        cmdProcImage += ' ( "%s"  -resize %d%% ) ' % (imgPath, resize)
        cmdProcImage += ' -gravity %s -geometry %+d%+d -compose dissolve -define compose:args=%d -composite ' % \
                          (gravity, xNudge, yNudge, opacity)

        return cmdProcImage


    def CaptionProcessing(self, captionIdx, frameIdx, beforeFXchain, borderOffset):
        captionId    = "caption%d" % (captionIdx)
        cmdProcImage = ""

        if len(self.conf.GetParam(captionId, 'text')) > 0:
            fromFrame = int(self.conf.GetParam(captionId, 'frameStart'))
            toFrame   = int(self.conf.GetParam(captionId, 'frameEnd'))
    
            if frameIdx < fromFrame or frameIdx > toFrame:
               return ""

        else:
            return ""

        # tricky please 
        if self.conf.GetParamBool(captionId, 'applyFx') != beforeFXchain:
            return ""


        opacity = float(self.conf.GetParam(captionId, 'opacity')) # Starting opacity
        # We need to nudge the font so it doesn't ride up against the edge
        positionAdjX = 0
        positionAdjY = 0
        #
        # Time-based effects
        #

        animationEnvelopeName = self.conf.GetParam(captionId, 'animationEnvelope').lower()

        if animationEnvelopeName != 'off':
            fps               = int(self.conf.GetParam('rate','framerate'))
            animationDuration = 1.0


            if "slow" in animationEnvelopeName:
                animationDuration = 2.0
            if "medium" in animationEnvelopeName:
                animationDuration = 1.0
            if "fast" in animationEnvelopeName:
                animationDuration = 0.5

            dutyCycle = float(fps) * animationDuration
            animStep  = int(round(100 / dutyCycle))

            if animStep == 0:
                animStep = 1

            saw = [x/100.0 for x in range(0, 101, animStep)]
            tri = [x/100.0 for x in range(0, 101, animStep)]
            squ = ([1.00] * int(dutyCycle)) + ([0.00] * int(dutyCycle))

            if saw[-1] != 1.0:
                saw.append(1.0)

            if tri[-1] != 1.0:
                tri.append(1.0)

            if len(squ) == 0:
                squ = [1.0, 0.0]

            tri = tri + tri[::-1][1:-1]
            rnd = []

            for x in range(0, 50):
                rnd.append(random.randint(0, 100) / 100.0)

            totalTextFrames = 1+toFrame-fromFrame

            patternEnv   = list()
            if "triangle" in animationEnvelopeName:
                patternEnv = tri
            elif "square" in animationEnvelopeName:
                patternEnv = squ
            elif "random" in animationEnvelopeName:
                patternEnv = rnd
            elif "sawtooth" in animationEnvelopeName:
                patternEnv = saw
            else:
                patternEnv = [1.0]

            # repeat pattern
            if totalTextFrames > 0:
                patternEnv = ([op for op in patternEnv * totalTextFrames])[0:totalTextFrames]

            if "fade" in animationEnvelopeName and "in" in animationEnvelopeName:
                for fx in range(0, min(len(saw), len(patternEnv))):
                    patternEnv[fx] *= saw[fx]

            if "fade" in animationEnvelopeName and "out" in animationEnvelopeName:
                si = 0
                for fx in range(len(patternEnv) -1, -1, -1):
                    patternEnv[fx] *= saw[si]
                    si += 1
                    if si >= len(saw):
                        break

            animationEnv = [0.0] * (fromFrame-1)
            animationEnv += patternEnv
            animationEnv += [0.0] * (self.GetNumFrames() - len(animationEnv))            

            # Animation type: Blink
            if self.conf.GetParam(captionId, 'animationType').lower() == 'blink':
                opacity *= animationEnv[frameIdx-1]

            if self.conf.GetParam(captionId, 'animationType').lower() == 'left-right':
                moveRange = 50
                positionAdjX += -moveRange/2 + (moveRange * animationEnv[frameIdx-1])

            if self.conf.GetParam(captionId, 'animationType').lower() == 'up-down':
                moveRange = 50
                positionAdjY += -moveRange/2 + (moveRange * animationEnv[frameIdx-1])

            if self.conf.GetParam(captionId, 'animationType').lower() == 'subtle change':
                moveRange     = 2
                moveAmount    = -moveRange/2 + (moveRange * animationEnv[frameIdx-1])
                positionAdjY += moveAmount
                positionAdjX += moveAmount
                opacity      *= ReScale(animationEnv[frameIdx-1], (0.0, 1.0), (0.8,1.0))

        if opacity <= 1:
            return ""

        captionText   = self.conf.GetParam(captionId, 'text')
        captionMargin = int(self.conf.GetParam('captiondefaults', 'margin'))
        gravity       = self.PositionToGravity(self.conf.GetParam(captionId, 'positioning'))

        if gravity.find("West") != -1 or gravity.find("East") != -1:
            positionAdjX += captionMargin + borderOffset

        if gravity.find("South") != -1 or gravity.find("North") != -1:
            positionAdjY += captionMargin + borderOffset

        # Escape captions
        captionText     = captionText.replace('[enter]', '\n')
        captionText     = captionText.replace('\\', '\\\\')
        captionText     = captionText.replace('"', '\\"')
        captionText     = captionText.replace('@', '\\@')

        fontFamily      = self.conf.GetParam(captionId, 'font')
        fontStyle       = self.conf.GetParam(captionId, 'style')

        fontId               = self.fonts.GetFontId(fontFamily, fontStyle)
        fontSize             = int(self.conf.GetParam(captionId, 'size').replace('pt',''))
        fontColor            = '"%s"' % (self.conf.GetParam(captionId, 'color'))
        fontOuterColor       = '"%s"' % (self.conf.GetParam(captionId, 'outlineColor'))
        fontOutlineThickness = self.conf.GetParam(captionId, 'outlineThickness')
        fontOpacity          = int(opacity)
        isSmooth             = False # int(self.conf.GetParam(captionId, 'smoothOutline'))
        hasShadow            = int(self.conf.GetParam(captionId, 'dropShadow'))

        fontBlur    = ""
        outlineBlur = ""

        if fontOutlineThickness >= 1:
            if isSmooth:
                outlineBlur = "-blur 0.1x1" # SigmaxRadius

            if fontSize > 13:
                fontOutlineThickness += 1
            else:
                fontOutlineThickness += 0
        try:
            int(fontSize)
        except:
            fontSize = 24

        if fontId == None:
            self.FatalError("Unable to find font: %s (%s) " % (fontFamily, fontStyle))

        cmdProcImage += "( +clone -alpha transparent -font %s -pointsize %d -gravity %s " % (fontId, fontSize, gravity)                        

        interlineSpacing=int(self.conf.GetParam(captionId, 'interlineSpacing'))

        if interlineSpacing != 0:
            cmdProcImage += ' -interline-spacing %d ' % (interlineSpacing)

        captionTweakX=[0, 0]
        captionTweakY=[0, 0]

        if "South" in gravity:
            captionTweakY[1]=1
        elif "North" in gravity:
            captionTweakY[1]=-1
        else:
            captionTweakY[1]=-1

        if  "West" in gravity:
            captionTweakX[0]=-1
        elif "East" in gravity:
            captionTweakX[0]=1
        else:
            captionTweakX[0]=-1

        if fontOutlineThickness >= 1:
            cmdProcImage += " -stroke %s -strokewidth %d -annotate %+d%+d \"%s\" %s "  % (fontOuterColor, fontOutlineThickness, positionAdjX+captionTweakX[0], positionAdjY+captionTweakY[0], captionText, outlineBlur)
            cmdProcImage += " -stroke %s -strokewidth %d -annotate %+d%+d \"%s\" %s "  % (fontOuterColor, fontOutlineThickness, positionAdjX+captionTweakX[1], positionAdjY+captionTweakY[1], captionText, outlineBlur)

        cmdProcImage += " -stroke none  -strokewidth %d -fill %s -annotate %+d%+d \"%s\" %s " % (fontOutlineThickness, fontColor, positionAdjX, positionAdjY, captionText, fontBlur)

        if hasShadow:
           cmdProcImage += " ( +clone -gravity none -background none -shadow 60x1-5-5 ) +swap -compose over -composite "

        cmdProcImage += ' ) -compose dissolve -define compose:args=%d -composite ' % (fontOpacity)
        return cmdProcImage


    def CropAndResize(self, argFrameIdx=None):
        files = glob.glob(self.frameDir + os.sep + '*.png')        
        files.sort()

        origWidth  = self.GetVideoWidth()
        origHeight = self.GetVideoHeight() 

        cinemagraphKeyFrame = int(self.conf.GetParam('blend', 'cinemagraphKeyFrameIdx'))
        keyframeFile = files[cinemagraphKeyFrame]

        if argFrameIdx is not None:
            files      = [ files[argFrameIdx] ]
            frameIdx   = argFrameIdx + 1
            logging.info("Crop, Resize and Blend frame %d" % (frameIdx))

        else:
            logging.info("Crop, Resize and Blend")
            self.DeleteResizedImages()
            frameIdx = 1

        for f in files:
            inputFileName  = f
            outputFileName = self.resizeDir + os.sep + os.path.basename(f)

            cmdResize  = '"%s" -comment "Crop and Resize:%d" -comment "instagiffer" "%s" -resize %dx%d! +repage ' % \
                            (
                                self.conf.GetParam('paths', 'convert'),
                                min(len(files),frameIdx-1)*100/len(files),
                                inputFileName,
                                origWidth,
                                origHeight
                            )
            cmdResize += "  -strip " # Get rid of weird gamma correction

            #
            # Blend: Cinemagraph
            #

            if frameIdx > 1 and self.conf.GetParamBool('blend', 'cinemagraph'):
                maskFile = self.GetMaskFileName(cinemagraphKeyFrame)

                negation = ""
                if self.conf.GetParamBool('blend', 'cinemagraphInvert'):
                    negation = " +negate "

                if os.path.exists(maskFile):
                    cmdResize += ' ( "%s" -resize %dx%d!  ( "%s" %s ) -alpha off -compose copy_opacity -composite ) -compose over -composite ' %  (keyframeFile, origWidth, origHeight, maskFile, negation)

                    # Transparent cinemagraphs
                    if self.conf.GetParamBool('blend', 'cinemagraphUseTransparency'):
                        cmdResize += ' ( ( "%s" %s ) -fill black -fuzz 0%% +opaque "#ffffff" -negate -transparent black -negate ) -compose copy_opacity -composite ' %  ( maskFile, negation)

            #
            # Crop
            #

            if self.conf.GetParam('size', 'cropenabled'):
                cmdResize += \
                    ' +repage ' + \
                    ' -crop ' + self.conf.GetParam('size','cropwidth')   + 'x' + self.conf.GetParam('size','cropheight')  + \
                    '+' +       self.conf.GetParam('size','cropoffsetx') + '+' + self.conf.GetParam('size','cropoffsety') + ' +repage'

            #
            # Resize
            #

            x,y = self.GetCroppedAndResizedDimensions()
            cmdResize += ' -resize %dx%d! ' % (x, y)
            cmdResize += ' "%s" ' % (outputFileName)

            if not RunProcess(cmdResize, self.callback, False, False):
                errMsg = "Image crop, resize, and blend failed or aborted"
                self.DeleteResizedImages()
                self.FatalError(errMsg)
                return False

            frameIdx += 1
        return True



    def ImageProcessing(self, previewFrameIdx=-1):
        # Dump the settings
        # if __release__ == False:
        #     self.conf.Dump()

        if previewFrameIdx >= 0:
            genPreview = True
            frameIdx   = previewFrameIdx + 1
            files      = [ self.GetResizedImageList(frameIdx) ] 
            logging.info("Processing frame %d" % (frameIdx))
        else:
            genPreview = False
            logging.info("Processing frames")
            files = glob.glob(self.resizeDir + os.sep + '*.png')
            self.DeleteProcessedImages()
            frameIdx = 1

        files.sort()
        for f in files:
            inputFileName  = f

            if genPreview:
                outputFileName = self.previewFile
            else:
                outputFileName = self.processedDir + os.sep + os.path.splitext(os.path.basename(f))[0] + '.' + self.GetIntermediaryFrameFormat()

            borderOffset = 0
            if self.conf.GetParamBool('effects', 'border'):
                thickness     = ReScale(int(self.conf.GetParam('effects','borderAmount')), (0,100), (1,40))
                borderOffset  = thickness

            cmdProcImage = '"%s" -comment "Applying Filters, Effects and Captions:%d" -comment "instagiffer" "%s" ' % \
                (
                    self.conf.GetParam('paths', 'convert'),
                    min(frameIdx-1, len(files))*100/len(files),
                    inputFileName
                )

            # Pre Filter fonts
            for x in range(1, 30):
                cmdProcImage += self.CaptionProcessing(x, frameIdx, True, borderOffset)
 
            # Pre Filter blits
            for x in range(1, 2): 
                cmdProcImage += self.BlitImage(x, True)

            #
            # Effects
            #

            # Brightness and contrast (not supported in older versions of Imagemagick)
            if self.conf.GetParam('effects','brightness') != "0" or self.conf.GetParam('effects','brightness')  != "0":
                cmdProcImage += '-brightness-contrast %sx%s ' % (self.conf.GetParam('effects','brightness'), self.conf.GetParam('effects','contrast'))

            if self.conf.GetParamBool('effects', 'sharpen'):
                cmdProcImage += '-sharpen 3 '

            if self.conf.GetParamBool('effects','oilPaint'):
                cmdProcImage +='-morphology OpenI Disk:1.75 '

            if self.conf.GetParam('color','saturation') != "0":
                scaledVal = 100 + ReScale(int(self.conf.GetParam('color','saturation')), (-100,100), (-80,80))
                cmdProcImage += '-modulate 100,%d ' % (scaledVal)

            if self.conf.GetParamBool('effects', 'nashville'):
                amt = ReScale(int(self.conf.GetParam('effects','nashvilleAmount')), (0,100), (10,65))

                cmdProcImage += ' ( -clone 0 -fill "#222b6d" -colorize %d%% ) ( -clone 0 -colorspace gray -negate ) -compose blend -define compose:args=50,0  -composite ' % (amt)
                cmdProcImage += ' ( -clone 0 -fill "#f7daae" -colorize %d%% ) ( -clone 0 -colorspace gray -negate ) -compose blend -define compose:args=120,1 -composite ' % (amt)
                cmdProcImage += ' -contrast -modulate 100,150,100 -auto-gamma '


            # Sepia
            if self.conf.GetParamBool('effects','sepiaTone'):
                scaledVal = ReScale(int(self.conf.GetParam('effects','sepiaToneAmount')), (0,100), (75,100))
                cmdProcImage += '-sepia-tone %d%% ' % (scaledVal)

            # Cartoon
            #cmdProcImage += '-edge 1 -negate -normalize -colorspace Gray -blur 0x.5 -contrast-stretch 0x50% '


            if self.conf.GetParamBool('effects','colorTint'):
                color = '"%s"' % (self.conf.GetParam('effects','colorTintColor'))
                amt   = ReScale(int(self.conf.GetParam('effects','colorTintAmount')), (0,100), (30,100))
                cmdProcImage +='-fill %s -tint %d ' % (color, amt)


            # Fade edges
            if self.conf.GetParamBool('effects', 'fadeEdges'):
                rad = 100 - int(self.conf.GetParam('effects','fadeEdgeAmount'))
                sig = 100 - int(self.conf.GetParam('effects','fadeEdgeAmount'))
                rad = ReScale(rad, (0,100), (20,60))
                sig = ReScale(sig, (0,100), (50,5000))
                vx  = -30
                vy  = -30
                cmdProcImage += '-background black -vignette %dx%d%d%d ' % (rad, sig, vx, vy)


            # Blur
            if int(self.conf.GetParam('effects', 'blur')) > 0:
                rad = 0
                sig = ReScale(int(self.conf.GetParam('effects','blur')), (0,100), (1,11))
                cmdProcImage += '-blur %dx%s ' % (rad,sig)


            # Border
            if borderOffset > 0:
                color         = self.conf.GetParam('effects', 'borderColor') 
                thickness     = borderOffset
                cmdProcImage += '-bordercolor "%s" -border %d ' % (color, thickness)     



            # Enhancement: Dithering

            # misc size optimization -normalize 
            if self.conf.GetParamBool('effects', 'sharpen'):
                sharpAmount = int(self.conf.GetParam('effects','sharpenAmount'))
                scaledVal   = ReScale(sharpAmount, (0,100), (0,5))
                ditherIdx   = 0

                if sharpAmount >= 60:
                    ditherIdx = 2
                elif sharpAmount >= 30:
                    ditherIdx = 1

                ditherType = [ "-ordered-dither checks,20", "-dither Riemersma", "-dither FloydSteinberg" ]

                cmdProcImage += '-sharpen %d %s ' % (scaledVal, ditherType[ditherIdx])
            else:
                cmdProcImage +="-dither none "

            # Post Filter captions
            for x in range(1, 30):
                cmdProcImage += self.CaptionProcessing(x, frameIdx, False, borderOffset)

            # Post Filter blits
            for x in range(1, 2): 
                cmdProcImage += self.BlitImage(x, False)

            #
            # Colorspace conversion
            #
            if self.conf.GetParam('color','colorspace') != "CMYK":
                cmdProcImage += '-colorspace %s ' % (self.conf.GetParam('color','colorspace'))   # -matte

            # Color palette - gif only
            if self.GetFinalOutputFormat() == 'gif':
                cmdProcImage += ' -depth 8 -colors %s ' % (self.conf.GetParam('color', 'numcolors'))


            cmdProcImage += ' -format %s ' % (self.GetIntermediaryFrameFormat()) 
            cmdProcImage += '"%s" ' % (outputFileName)

            if not RunProcess(cmdProcImage, self.callback, False, False):
                errMsg = "Image processing failed or aborted"
                self.DeleteProcessedImages()
                self.FatalError(errMsg)
                return False

            frameIdx += 1
        return True
 
    # Generate final output. Returns size of generated GIF in bytes
    def Generate(self, skipProcessing=False):
        err      = ""
        fileName = self.GetNextOutputPath()

        # Process all frames
        if not skipProcessing:
            self.ImageProcessing()

        #
        # Now what file format are we dealing with?
        #

        if self.GetFinalOutputFormat() == 'gif':
            # Using convert util
            cmdCreateGif = '"%s" '% (self.conf.GetParam('paths', 'convert'))
            # Playback rate and looping
            cmdCreateGif += ' -delay %d ' % (self.GetGifFrameDelay())
            cmdCreateGif += ' -loop %d ' % (int(self.conf.GetParam('rate', 'numLoops')))

            if self.conf.GetParamBool('blend', 'cinemagraphUseTransparency'):
                cmdCreateGif += ' -alpha set -dispose %d '  % (int(self.conf.GetParamBool('blend', 'cinemagraphKeyFrameIdx')))
            else:
                cmdCreateGif += '-layers optimizePlus '
            
            # Input files
            cmdCreateGif += '"' + self.processedDir + os.sep + '*.' + self.GetIntermediaryFrameFormat() + '" '
            cmdCreateGif += '"' + fileName + '"'

            (out, err) = RunProcess(cmdCreateGif, self.callback, returnOutput=True)

        elif self.GetFinalOutputFormat() in [ 'mp4', 'webm' ]:
            self.ExtractAudioClip()

            secPerFrame    = self.GetGifFrameDelay() * 10 / 1000.0
            fps            = 1.0/secPerFrame
            finalFps       = 30
            framesDir      = self.GetProcessedImagesDir()

            self.ReEnumeratePngFrames(self.GetProcessedImagesDir(), self.GetProcessedImageList())

            #
            # - vf Make width/height even
            # - shortest Finish encoding when the shortest input stream ends.
            # - h.264 format
            # - use null audio
            # 
            #"e:\ffmpeg\ffmpeg.exe" -r 1/5 -start_number 0 -i "E:\images\01\padlock%3d.png" -c:v libx264 -r 30 -pix_fmt yuv420p e:\out.mp4

            cmdConvertToVideo = u'"%s" -v verbose -y -r %.2f -start_number 0 -i "%simage%%04d.%s" ' % \
                (
                    self.conf.GetParam('paths', 'ffmpeg'),
                    fps,
                    framesDir,
                    self.GetIntermediaryFrameFormat()
                )

            # Audio
            if self.conf.GetParamBool('audio', 'audioEnabled'):
                if not os.path.exists(self.conf.GetParam('audio', 'path')):
                    self.FatalError("Could not find audio file")

                if self.GetFinalOutputFormat() in ['webm']:
                    audioCodec = " libvorbis "
                else:
                    audioCodec = "aac -strict experimental"

                volume = int(self.conf.GetParam('audio', 'volume'))/100.0

                cmdConvertToVideo += ' -ss "%s" -i "%s" -af "volume=%.f" -c:a %s -b:a 128k  ' % \
                    (
                        self.conf.GetParam    ('audio', 'startTime'),
                        self.conf.GetParam    ('audio', 'path'),
                        volume,
                        audioCodec
                    )
            else:
                cmdConvertToVideo += ' -f lavfi -i aevalsrc=0 '

            # video
            if self.GetFinalOutputFormat() in [ 'mp4' ]: 
                cmdConvertToVideo += ' -c:v libx264 -crf 18 -preset slow -vf "scale=trunc(in_w/2)*2:trunc(in_h/2)*2",setsar=1:1 -pix_fmt yuv420p '
            elif self.GetFinalOutputFormat() in ['webm']:
                cmdConvertToVideo += ' -c:v libvpx -crf 4 -b:v 312.5k -vf setsar=1:1 '
            else:
                cmdConvertToVideo += ' -vf setsar=1:1 '

            cmdConvertToVideo += ' -shortest  -r %d "%s"' % (finalFps, fileName)

            (out, err) = RunProcess(cmdConvertToVideo, self.callback, returnOutput=True)
        else:
            self.FatalError("I don't know how to create %s files" % (self.GetFinalOutputFormat()))

        if not os.path.exists(fileName) or os.path.getsize(fileName) == 0: 
            logging.error(err)
            self.FatalError("Failed to create %s :( " % (self.GetFinalOutputFormat()))
            return 0

        self.gifCreated       = True
        self.lastSavedGifPath = fileName

        # Run the gif optimizer
        if self.GetFinalOutputFormat() == 'gif':
            self.AlterGifFrameTiming(fileName)
            self.OptimizeGif(fileName)

        return self.GetSize()


    def AlterGifFrameTiming(self, fileName):
        frameTimingsStr = self.conf.GetParam('rate', 'customFrameTimingMs')

        if len(frameTimingsStr) == 0:
            return

        cmdChangeGifTiming  = '"%s" "%s" ' % (self.conf.GetParam('paths', 'convert'), fileName)

        for frameStr in frameTimingsStr.split(","):
            (frameIdx, frameMs) = frameStr.split(":")

            frameIdx = int(frameIdx)
            frameMs  = int(frameMs)

            cmdChangeGifTiming += ' ( -clone %d -set delay %d ) -swap %d,-1 +delete ' % (frameIdx, frameMs/10, frameIdx)
        
        cmdChangeGifTiming += ' "%s"' % (fileName)
        (out, err) = RunProcess(cmdChangeGifTiming, self.callback, returnOutput=True)


    def OptimizeGif(self, fileName):
        # Run optimizer
        if self.conf.GetParamBool('size', 'fileOptimizer') and os.path.exists(self.conf.GetParam('paths', 'gifsicle')):
            olevel = 3
            beforeSize = self.GetSize()

            cmdOptimizeGif = '"%s" -O%d --colors 256 "%s" -o "%s"' % (self.conf.GetParam('paths', 'gifsicle'), olevel, fileName, fileName)

            (out, err) = RunProcess(cmdOptimizeGif, self.callback, returnOutput=True)

            afterSize = self.GetSize()

            logging.info("Optimization shaved off %.1f kB" % (float(beforeSize-afterSize)/1024.0))


    def GenerateFramePreview(self, idx):
        idx -= 1
        self.CropAndResize(idx)
        self.ImageProcessing(idx)
        self.callback(True)
        return self.previewFile

    def GetPreviewImagePath(self):
        return self.previewFile

    def PreviewFileExists(self):
        return os.path.exists(self.GetPreviewImagePath())

    def GetPreviewLastModifiedTs(self):
        if self.PreviewFileExists():
            return os.stat(self.GetPreviewImagePath()).st_mtime
        else:
            return 0

    def GetTotalRuntimeSec(self):
        secPerFrame = (self.GetGifFrameDelay()*10)/1000.0
        totalSec    = secPerFrame * self.GetNumFrames()
        return totalSec

    def GetGifFrameDelay(self, modifyer = None):
        if modifyer is None:
            modifyer = int(self.conf.GetParam('rate','speedmodifier'))

        timePerFrame      = 100//int(self.conf.GetParam('rate','framerate')) 
        speedModification = modifyer
        normalizedMod     = 1 + (abs(speedModification)-0)*(timePerFrame-0)/(10-0)
        gifFrameDelay     = timePerFrame

        if speedModification < 0:
            gifFrameDelay += int(normalizedMod * 2) # Increase the effect when slowing down
        elif speedModification > 0:
            gifFrameDelay -= normalizedMod

        if gifFrameDelay < 2: # frame delay of 1 means realtime??
            gifFrameDelay = 2

        return gifFrameDelay

    def GetSize(self):
        sizeBytes = os.path.getsize(self.GetLastGifOutputPath())
        return sizeBytes

    def GetVideoWidth(self):
        return int(self.videoWidth)

    def GetVideoHeight(self):
        return int(self.videoHeight)

    def GetVideoLength(self):
        return self.videoLength

    def GetVideoLengthSec(self):
        vidLen = float("%.1f" % (DurationStrToMillisec(self.videoLength)/1000.0))
        return vidLen

    def GetVideoFps(self):
        if self.videoFps < 1:
            return 1
        else:
            return int(round(float(self.videoFps)))

    def CompatibilityWarningsEnabled(self):
        return self.conf.GetParamBool('warnings', 'socialMedia')

    def GetCroppedAndResizedDimensions(self):
        w, h = self.conf.GetParam('size', 'resizePostCrop').split('x')
        return int(w), int(h)

    def GetCompatibilityWarning(self):
        w, h = self.GetCroppedAndResizedDimensions()
        aspectRatio = w/float(h)

        warnings      = ""
        warnTwitter   = self.conf.GetParamBool('warnings', 'twitter')
        warnTumblr    = self.conf.GetParamBool('warnings', 'tumblr')
        warnImgur     = self.conf.GetParamBool('warnings', 'imgur')
        warnGPlus     = self.conf.GetParamBool('warnings', 'gplus')
        warnFacebook  = self.conf.GetParamBool('warnings', 'facebook')
        warnInstagram = self.conf.GetParamBool('warnings', 'instagram')
        warnVine      = self.conf.GetParamBool('warnings', 'vine')

        if warnTumblr:
            # TODO: Verify. is this still a thing?
            #if w > 400 and w <= 500 and self.GetSize() >= 1000 * 1024 and self.GetSize() < 2000 * 1024:
            #    warnings += "Tumblr Warning: If image width exceeds 400px, file size must be less than 1000kB\n\n" 

            if w > 540 or h > 750:
                warnings += "Tumblr Warning: Image dimensions (" + str(w) + "x" + str(h) + ") are larger than the 500x750 maximum.\n\n" 

            if self.GetSize() >= 2000 * 1024:
                warnings += "Tumblr Warning: File size of " + str(int(self.GetSize()/1024)) + "kB is too large. It must be less than 2000kB. Try reducing animation smoothness, viewable region, frame size, or quality.  You can also try enabling black & white mode.\n\n" 


        if warnImgur and self.GetSize() >= 2 * 1024 * 1024:
            warnings += "Imgur Warning: File size of " + str(int(self.GetSize()/1024)) + "kB is too large. It must be less than 2MB unless you have a premium account, in which case, the max upload limit is 5MB.\n\n" 


        if warnTwitter:
            twitWarn = 0
            if self.GetSize() >= 5 * 1024 * 1024:
                warnings += "Twitter Warning: File size of " + str(int(self.GetSize()/1024)) + "kB is too large. It must be less than 5MB.\n\n" 
                twitWarn += 1

            if self.GetNumFrames() > 350:
                warnings += "Twitter Warning: Number of frames must not exceed 350.\n\n"
                twitWarn += 1

            if twitWarn > 0:
                # might as well tell them about this too
                if w < 506 or aspectRatio != 1.0 or aspectRatio != 0.5:
                    warnings += "Twitter Warning: recommended dimensions are 506x506 or 506x253.\n\n"

        if warnGPlus and (w < 496 or h < 496 or aspectRatio != 1.0):
            warnings += "Google Plus Warning: Recommended dimensions are 496x496.\n\n" 

        if warnInstagram:
            if w != 600 or h != 600:
                warnings += "Instagram Warning: Recommended dimensions are 600x600.\n\n" 

            if self.GetTotalRuntimeSec() > 15:
                warnings += "Instagram Warning: Total runtime must not exceed 15 seconds.\n\n"

        if warnFacebook:
            if w != 504 or h != 283:
                warnings += "Facebook Warning: Recommended dimensions are 504x283.\n\n"

        if warnVine:
            if w != 480 or h != 480:
                warnings += "Vine Warning: Required dimensions are 480x480.\n\n"

            if self.GetTotalRuntimeSec() > 6:
                warnings += "Vine Warning: Total run time cannot exceed 6 seconds.\n\n"

            if self.GetSize() >= 1500 * 1024:
                warnings += "Vine Warning: Total file size must be under 1.5 MB\n\n"

        return warnings



#
#
# Tkinter widget that plays a gif
#
#

class GifPlayerWidget(Label):
    def __init__(self, master, processedImgList, frameDelayMs, resizable, soundPath=None):
        self.delay     = frameDelayMs
        self.images    = []
        self.frames    = []
        self.resizable = resizable
        self.imgList   = processedImgList
        self.audioPath = soundPath

        if self.delay < 2:
            self.delay = 100
        
        self.LoadImages(False)

        Label.__init__(self, master, image=self.frames[0], padx=10, pady=10)
        self.idx = 0
        self.cancel = self.after(self.delay, self.Play)

        if self.resizable:
            self.columnconfigure(0, weight=1)
            self.rowconfigure(0, weight=1)

        self.currW = self.winfo_width()
        self.currH = self.winfo_height()


    def GetInfo(self):
        width, height = self.images[0].size
        return "Dimensions: %dx%d" % (width, height)

    def Stop(self):
        AudioPlay(None)
        self.after_cancel(self.cancel)

    def LoadImages(self, resize):
        self.images = []
        self.frames = []

        for imagePath in self.imgList:
            f  = open(imagePath, 'rb')
            
            im = PIL.Image.open(f)

            if self.resizable and resize:
                im = im.resize((self.winfo_width(), self.winfo_height()), PIL.Image.ANTIALIAS)

            self.images.append(im)
            self.frames.append(ImageTk.PhotoImage(im))
           
            f.close()
            del im
            del f

    def Play(self):
        resizePause = 0

        if self.idx == 0:
            AudioPlay(self.audioPath)


        self.idx += 1
        if self.idx >= len(self.frames):
            self.idx = 0
       
        # window was resized
        if self.resizable and (self.winfo_width() != self.currW or self.winfo_height() != self.currH):
            logging.info("%s %s => %d %d" %(self.currW, self.currH, self.winfo_width(), self.winfo_height()))

            self.Stop()
            self.LoadImages(True)
            resizePause = 0
            self.currW  = self.winfo_width()
            self.currH  = self.winfo_height()

        self.config(image=self.frames[self.idx])
        self.cancel = self.after(self.delay + resizePause, self.Play)



class GifApp:

    def __init__(self, parent, cmdlineVideoPath):
        global __version__
        global __release__

        self.gif                  = None
        self.guiBusy              = False
        self.showPreviewFlag      = False
        self.parent               = parent
        self.thumbnailIdx         = 0
        self.timerHandle          = None
        self.cancelRequest        = False
        self.tempDir              = None
        self.captions             = dict()
        

        self.cropResizeChanges               = 0
        self.captionChanges                  = 0       
        self.miscGifChanges                  = 1
        self.frameTimingOrCompressionChanges = 0
        self.audioChanges                    = 0


        self.screenCapDlgGeometry = ""
        self.mainTimerValueMS     = 2000
        self.savePath             = None
        self.parent.withdraw()  # Hide. add components then show at the end
        self.thumbNailsUpdatedTs  = 0
        self.thumbNailCache       = dict()
        self.maskEventList        = None
        self.maskEdited           = False
        self.trackBarTs           = 0


        # self.cropWidth            = "0"
        # self.cropHeight           = "0"
        # self.cropStartX           = "0"
        # self.cropStartY           = "0"
        # self.finalSize            = "0x0"

        # DPI scaling
        defaultDpi = 96 # corresponds to Smaller 100%
        self.parent.tk.call('tk', 'scaling', '-displayof', '.', defaultDpi / 72.0)

        #
        # Child Dialog default values
        #

        self.OnCaptionConfigDefaults = dict()
        self.OnSetLogoDefaults       = dict()

        #
        # Load config 
        #

        binPath       = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.conf     = InstaConfig(binPath + os.sep + 'instagiffer.conf')
        self.savePath = None

        #
        # Initialize variables with configuration defaults
        #
        self.screenCapDlgGeometry = self.conf.GetParam('screencap', 'sizeandposition')
        timerMs = self.conf.GetParam('settings', 'idleProcessTimeoutMs')

        if timerMs != "" and timerMs.isdigit() and int(timerMs) > 1000:
            self.mainTimerValueMS  = timerMs

        self.CreateAppDataFolder()
        self.ForceSingleInstance()

        #
        # Debug version?
        #

        if self.conf.ParamExists("plugins", "debug"):
            __release__ = not self.conf.GetParamBool("plugins", "debug")

        #
        # Build GUI
        #
    
        if __release__ == False:
            self.parent.title("Instagiffer - DEBUG MODE *******")
        else:
            self.parent.title("Instagiffer")

        if ImAPC():
            self.parent.wm_iconbitmap('instagiffer.ico')

        frame = Frame(parent)
        frame.pack()
        self.mainFrame = frame

        self.parent.resizable(width=FALSE, height=FALSE)
        #self.parent.protocol("WM_DELETE_WINDOW", self.OnWindowClose)

        #
        # GUI config. OS-dependant
        #

        if ImAPC():
            # Warning: Don't make the GUI too big, or it may not present
            # correctly on netbooks

            # Font configuration
            self.defaultFont     = tkFont.nametofont("TkDefaultFont")
            self.defaultFont.configure        (family="Arial", size=8)
            self.defaultFontBig  = tkFont.Font(family="Arial", size=9)
            self.defaultFontTiny = tkFont.Font(family="Arial", size=7)

            self.guiConf                      = dict()
            self.guiConf['guiPadding']        = 7     # GUI padding.
            self.guiConf['timeSpinboxWidth']  = 2     # Width of the MM:HH:SS spinboxes
            self.guiConf['fileEntryWidth']    = 105   # URL/path text field
            self.guiConf['canvasWidth']       = 365   # Viewing area (note: height = width)
            self.guiConf['canvasSliderWidth'] = self.guiConf['canvasWidth'] - 33
            self.guiConf['mainSliderHeight']  = 13    # Left-hand slider height
            self.guiConf['mainSliderWidth']   = 310 - (self.guiConf['guiPadding']-3) * 2 # Left-hand slider width
        else: # Mac
            # Font configuration
            self.defaultFont     = tkFont.nametofont("TkDefaultFont")
            self.defaultFont.configure        (family="Arial", size=11)
            self.defaultFontBig  = tkFont.Font(family="Arial", size=11)
            self.defaultFontTiny = tkFont.Font(family="Arial", size=9)

            self.guiConf                      = dict()
            self.guiConf['guiPadding']        = 9
            self.guiConf['timeSpinboxWidth']  = 3
            self.guiConf['fileEntryWidth']    = 119
            self.guiConf['canvasWidth']       = 400
            self.guiConf['canvasSliderWidth'] = self.guiConf['canvasWidth'] - 63
            self.guiConf['mainSliderHeight']  = 16
            self.guiConf['mainSliderWidth']   = 400 - (self.guiConf['guiPadding']-3) * 2

        # Menu
        #######################################################################

        self.menubar = Menu(parent)

        # Override Apple menu
        if ImAMac():
            apple = Menu(self.menubar, name='apple')
            apple.add_command(label="About", command=self.About)           
            self.menubar.add_cascade(menu=apple)

        # File
        self.fileMenu = Menu(self.menubar, tearoff=0)        

        self.uploadMenu = Menu(self.fileMenu, tearoff=0)
        self.uploadMenu.add_command(label="Imgur", underline=0, command=self.OnImgurUpload)

        self.fileMenu.add_command(label="Download Video...",        underline=1, command=self.OnSaveVideoForLater)
        self.fileMenu.add_command(label="Change Save Location...",  underline=7, command=self.OnSetSaveLocation)
        self.fileMenu.add_cascade(label='Upload',                   underline=0, menu=self.uploadMenu)
        self.fileMenu.add_command(label="Delete Temporary Files",   underline=0, command=self.OnDeleteTemporaryFiles)
        self.fileMenu.add_command(label="Exit",                     underline=0, command=self.OnWindowClose)

        # Frame
        self.frameMenu = Menu(self.menubar, tearoff=0)

        if ImAPC():
            viewInExternalViewerLabel = "View Frames In Explorer..."
        else:
            viewInExternalViewerLabel = "Reveal Frames in Finder"

        self.frameMenu.add_command(label=viewInExternalViewerLabel, underline=0, command=self.OnViewImageStillsInExplorer)
        self.frameMenu.add_command(label="Delete Frames...",        underline=0, command=self.OnDeleteFrames)
        self.frameMenu.add_command(label="Export Frames...",        underline=0, command=self.OnExportFrames)
        self.frameMenu.add_command(label="Import Frames...",        underline=0, command=self.OnImportFrames)
        self.frameMenu.add_command(label="Manual Crop...",          underline=7, command=self.OnManualSizeAndCrop)
        #self.frameMenu.add_command(label="Edit Mask...",            underline=5, command=self.OnEditMask)
        self.frameEffectsMenu = Menu(self.frameMenu, tearoff=0)
        self.frameEffectsMenu.add_command(label="Make It Loop!",      underline=8, command=self.OnForwardReverseLoop)
        self.frameEffectsMenu.add_command(label="Reverse",            underline=8, command=self.OnReverseFrames)
        self.frameEffectsMenu.add_command(label="Crossfade...",       underline=8, command=self.OnCrossFade)
        self.frameMenu.add_cascade(label='Frame Effects',             underline=0, menu=self.frameEffectsMenu)

        self.frameMenuItemCount = 6


        # Settings
        self.settingsMenu    = Menu(self.menubar,      tearoff=0)
        self.qualityMenu     = Menu(self.settingsMenu, tearoff=0)
        self.downloadQuality = StringVar()

        #
        # Youtube download quality
        #

        defaultQuality     = self.conf.GetParam('settings', 'downloadQuality')
        youtubeQualityList = ['None', 'Low', 'Medium', 'High', 'Highest']

        if defaultQuality not in youtubeQualityList:
            defaultQuality = 'Medium'
            self.conf.SetParam('settings', 'downloadQuality', defaultQuality)

        for qual in youtubeQualityList:
            self.qualityMenu.add_radiobutton(label=qual, underline=0, variable=self.downloadQuality, command=self.OnChangeMenuSetting)
        #

        self.socialMediaWarningsEnabled = StringVar()
        self.overwriteOutputGif         = StringVar()
        self.fileSizeOptimize           = StringVar()

        self.settingsMenu.add_checkbutton(label="Overwrite Output GIF",      underline=0, variable=self.overwriteOutputGif,         command=self.OnChangeMenuSetting)
        self.settingsMenu.add_checkbutton(label="Social Media Warnings",     underline=0, variable=self.socialMediaWarningsEnabled, command=self.OnChangeMenuSetting)
        self.settingsMenu.add_cascade    (label='Youtube Download Quality',  underline=0, menu=self.qualityMenu)
        self.settingsMenu.add_command    (label="Configure Your Logo...",    underline=0, command=self.OnSetLogo)

        if ImAPC():
            self.settingsMenu.add_checkbutton(label="Extra GIF Compression", underline=0, variable=self.fileSizeOptimize, command=self.OnChangeMenuSetting)

        # Help
        self.helpMenu = Menu(self.menubar, tearoff=0)
        self.helpMenu.add_command(label="About",                      underline=0, command=self.About)              
        self.helpMenu.add_command(label="Check For Updates",          underline=0, command=self.CheckForUpdates)
        self.helpMenu.add_command(label="Frequently Asked Questions", underline=0, command=self.OpenFAQ)
        self.helpMenu.add_separator()
        self.helpMenu.add_command(label="Generate Bug Report",        underline=0, command=self.ViewLog)

        # Top-level
        self.menubar.add_cascade(label="File",     underline=0, menu=self.fileMenu)
        self.menubar.add_cascade(label="Frame",    underline=0, menu=self.frameMenu)
        self.menubar.add_cascade(label="Settings", underline=0, menu=self.settingsMenu)
        self.menubar.add_cascade(label="Help",     underline=0, menu=self.helpMenu)
        parent.config(menu=self.menubar)

        # Status Bar
        #######################################################################

        padding = 2

        self.status = Label(parent, text="", bd=1, relief=SUNKEN, anchor=W)
        self.status.pack(side=BOTTOM, fill=X)

        # Progress bar
        #######################################################################

        # s = ttk.Style()
        # s.theme_use()
        # s.configure("red.Horizontal.TProgressbar", foreground='#395976', background='#395976')


        self.progressBar = ttk.Progressbar(parent, orient=HORIZONTAL, maximum=100, mode='determinate', name='progressBar') #, style="red.Horizontal.TProgressbar")
        self.progressBar.pack(side=BOTTOM, fill=X)
        self.showProgress = False
        self.progressBarPosition = IntVar()
        self.progressBar['variable'] = self.progressBarPosition

        # Top area (colspan = 2)
        #######################################################################

        # Row 1
        rowIdx  = 0

        # Top Box
        self.boxOpen   = LabelFrame(frame, text=" Step 1: Click 'Load Video' to browse for a file, paste a Youtube URL, or click 'Capture Screen' ")
        self.boxOpen.grid(row=rowIdx, column=0, columnspan=12, sticky="NS", padx=padding, pady=padding, ipadx=padding, ipady=padding)

        rowIdx += 1

        self.txtFname     = Entry(self.boxOpen, font=self.defaultFont, width=self.guiConf['fileEntryWidth'])
        self.btnFopen     = Button(self.boxOpen, text="Load Video", command=self.OnLoadVideo)
        self.btnScreenCap = Button(self.boxOpen, text="Capture Screen", command=self.OnScreenCapture)
        self.txtFname.grid    (row=rowIdx, column=0,  columnspan=5, sticky=W, padx=padding, pady=padding)
        self.btnFopen.grid    (row=rowIdx, column=11, columnspan=2, sticky=W, padx=padding, pady=padding)
        self.btnScreenCap.grid(row=rowIdx, column=13, columnspan=2, sticky=W, padx=padding, pady=padding)

        # 
        self.txtFname.bind('<Return>', self.OnLoadVideoEnterPressed)

        # Bind context menu (cut & paste) action to video URL text field

        if ImAMac():
            whichRclickMouseButton        = '<Button-2>'
            whichRclickReleaseMouseButton = '<ButtonRelease-2>'
        else:
            whichRclickMouseButton        = '<Button-3>'
            whichRclickReleaseMouseButton = '<ButtonRelease-3>'

        # right-click open  for multi-select mode
        self.btnFopen.bind(whichRclickMouseButton, self.OnShiftLoadVideo)

        self.txtFname.bind(whichRclickMouseButton, self.OnRClickPopup, add='')

        # Top-level left column, where all of the settings sliders are
        #######################################################################

        rowIdx += 1
        self.boxTweaks   = LabelFrame(frame, text=" Step 2: Video Extraction & GIF Settings ")
        self.boxTweaks.grid(row=rowIdx, column=0, columnspan=3, rowspan=10, sticky="NS", padx=padding, pady=padding, ipadx=padding, ipady=padding)

        # Top-level right column. Cropping tool
        #######################################################################

        self.boxCropping   = LabelFrame(frame, text=" Step 3: Trim edges. Right-Click to preview. Double-Click to delete ")
        self.boxCropping.grid(row=rowIdx, column=4, columnspan=2, rowspan=10, sticky="NS", padx=padding, pady=padding, ipadx=padding, ipady=padding)

        # Cropping tool
        #######################################################################
        
        rowIdx += 1

        self.canvasSize         = self.guiConf['canvasWidth']
        self.cropSizerSize      = 9 # Size of crop sizer handle

        self.btnTrackbarLeft    = Button(self.boxCropping, text="<", font=self.defaultFontTiny, command=self.OnTrackbarLeft, repeatinterval=1, repeatdelay=200)
        self.btnTrackbarRight   = Button(self.boxCropping, text=">", font=self.defaultFontTiny, command=self.OnTrackbarRight, repeatinterval=1, repeatdelay=200)
        self.sclFrameTrackbar   = Scale(self.boxCropping,  from_=1, to=1, resolution=1, tickinterval=0, showvalue=0, orient=HORIZONTAL, sliderlength=20, width=15, length=self.guiConf['canvasSliderWidth'], command=self.OnFrameTrackbarMove)
        self.canCropTool        = Canvas(self.boxCropping, width=self.canvasSize + 1, height=self.canvasSize + 1, background="black", borderwidth=0, highlightthickness=0)
        self.frameCounterStr    = StringVar()
        self.frameDimensionsStr = StringVar()
        self.lblFrameCtr        = Label(self.boxCropping, textvariable=self.frameCounterStr)
        self.lblFrameDimensions = Label(self.boxCropping, textvariable=self.frameDimensionsStr)


        self.canCropTool.grid       (row=rowIdx,    column=4, rowspan=9, columnspan=4, sticky=W,    padx=padding, pady=padding)
        self.btnTrackbarLeft.grid   (row=rowIdx+9,  column=4,            columnspan=1, sticky="E",  padx=0,       pady=0)
        self.sclFrameTrackbar.grid  (row=rowIdx+9,  column=5,            columnspan=2, sticky="EW", padx=0,       pady=0)
        self.btnTrackbarRight.grid  (row=rowIdx+9,  column=7,            columnspan=1, sticky="W",  padx=0,       pady=0)
        self.lblFrameCtr.grid       (row=rowIdx+10, column=4,            columnspan=2, sticky="w",  padx=padding, pady=0)
        self.lblFrameDimensions.grid(row=rowIdx+10, column=6,            columnspan=2, sticky="E",  padx=padding, pady=0)

        self.canCropTool.bind(whichRclickMouseButton,        self.OnShowPreview, add='')
        self.canCropTool.bind(whichRclickReleaseMouseButton, self.OnStopPreview, add='')


        # Settings sliders and checkboxes
        #######################################################################

        # Time

        padding = self.guiConf['guiPadding']
        rowIdx += 1
        self.lblStart       = Label(self.boxTweaks, text="Start Time")
        self.lblStart2      = Label(self.boxTweaks, text="")


        self.startTimeHour  = StringVar()
        self.startTimeMin   = StringVar()
        self.startTimeSec   = StringVar()
        self.startTimeMilli = StringVar()
        self.startTimeHour.set(0)
        self.startTimeMin.set("00")
        self.startTimeSec.set("00")
        self.startTimeMilli.set(0)

        timeValues = [ "%02d" % (x) for x in range(0, 60)]
        timeValues = " ".join(timeValues)

        self.sclStart          = Scale(self.boxTweaks, from_=1, to=1, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=self.guiConf['mainSliderHeight'], length=self.guiConf['mainSliderWidth'], showvalue=0, command=self.OnStartSliderUpdated)
        self.spnStartTimeHour  = Spinbox(self.boxTweaks, font=self.defaultFont, from_=0, to=9,  values="0 1 2 3 4 5 6 7 8 9", increment=1, width=self.guiConf['timeSpinboxWidth'], textvariable=self.startTimeHour,  validate=ALL, wrap=True, command=self.OnStartChanged, name="startHour",  repeatdelay=200, repeatinterval=150)
        self.lblHourSep        = Label(self.boxTweaks,  text=":")
        self.spnStartTimeMin   = Spinbox(self.boxTweaks, font=self.defaultFont, from_=0, to=59, values=timeValues,            increment=1, width=self.guiConf['timeSpinboxWidth'], textvariable=self.startTimeMin,   validate=ALL, wrap=True, command=self.OnStartChanged, name="startMin",   repeatdelay=250, repeatinterval=50)
        self.lblMinSep         = Label(self.boxTweaks,  text=":")
        self.spnStartTimeSec   = Spinbox(self.boxTweaks, font=self.defaultFont, from_=0, to=59, values=timeValues,            increment=1, width=self.guiConf['timeSpinboxWidth'], textvariable=self.startTimeSec,   validate=ALL, wrap=True, command=self.OnStartChanged, name="startSec",   repeatdelay=250, repeatinterval=50)
        self.lblSecSep         = Label(self.boxTweaks,  text=".")
        self.spnStartTimeMilli = Spinbox(self.boxTweaks, font=self.defaultFont, from_=0, to=9,  values="0 1 2 3 4 5 6 7 8 9", increment=1, width=self.guiConf['timeSpinboxWidth'], textvariable=self.startTimeMilli, validate=ALL, wrap=True, command=self.OnStartChanged, name="startMilli", repeatdelay=200, repeatinterval=150)

        self.lblStart.grid         (row=rowIdx, column=0,  columnspan=1, sticky=W,  padx=padding-3, pady=padding-3)
        self.sclStart.grid         (row=rowIdx, column=1,  columnspan=15, sticky=W, padx=padding-3, pady=padding-3)
        rowIdx += 1
        self.lblStart2.grid        (row=rowIdx, column=0,  columnspan=1, sticky=W,  padx=padding, pady=padding)
        self.spnStartTimeHour.grid (row=rowIdx, column=1,  columnspan=1, sticky=EW, padx=padding, pady=padding)
        self.lblHourSep.grid       (row=rowIdx, column=2,  columnspan=1, sticky=EW, padx=padding, pady=padding)
        self.spnStartTimeMin.grid  (row=rowIdx, column=3,  columnspan=1, sticky=EW, padx=padding, pady=padding)
        self.lblMinSep.grid        (row=rowIdx, column=4,  columnspan=1, sticky=EW, padx=padding, pady=padding)
        self.spnStartTimeSec.grid  (row=rowIdx, column=5,  columnspan=1, sticky=EW, padx=padding, pady=padding)
        self.lblSecSep.grid        (row=rowIdx, column=6,  columnspan=1, sticky=EW, padx=padding, pady=padding)
        self.spnStartTimeMilli.grid(row=rowIdx, column=7,  columnspan=1, sticky=EW, padx=padding, pady=padding)

        rowIdx += 1
        self.duration = StringVar()
        self.lblDuration = Label(self.boxTweaks, text="Length (sec)")
        self.spnDuration = Spinbox(self.boxTweaks, font=self.defaultFont, from_=0.1, to=120, increment=.1, width=5, textvariable=self.duration, command=self.OnDurationChanged, repeatdelay=300, repeatinterval=25, wrap=True)
        self.lblDuration.grid (row=rowIdx, column=0, columnspan=1, sticky=W, padx=padding, pady=padding)
        self.spnDuration.grid (row=rowIdx, column=1, columnspan=2, sticky=W, padx=padding, pady=padding)

        self.duration.set(0.1)

        if ImAPC():
            self.spnDuration.bind("<MouseWheel>", self.OnDurationMouseWheel)

        valueFontColor = "#353535"

        maxFps = self.conf.GetParam('rate', 'maxFrameRate')

        rowIdx += 1
        self.lblFps = Label(self.boxTweaks, text="Smoothness (fps)")
        self.sclFps = Scale(self.boxTweaks, from_=1, to=maxFps, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=self.guiConf['mainSliderHeight'], length=self.guiConf['mainSliderWidth'], font=self.defaultFontTiny, fg=valueFontColor, showvalue=1, command=self.OnFpsChanged)
        self.lblFps.grid(row=rowIdx, column=0, sticky=W, padx=padding, pady=padding)
        self.sclFps.grid(row=rowIdx, column=1, columnspan=15, sticky=W, padx=padding-3, pady=padding-3)

        rowIdx +=1
        self.lblBlankLine = Label(self.boxTweaks, text=" ", font=self.defaultFontTiny)
        self.lblBlankLine.grid(row=rowIdx, column=0, sticky=W, padx=0, pady=0)


        rowIdx += 1
        self.lblResize = Label(self.boxTweaks, text="Frame Size")
        self.sclResize = Scale(self.boxTweaks, from_=5, to=100, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=self.guiConf['mainSliderHeight'], length=self.guiConf['mainSliderWidth'], font=self.defaultFontTiny, fg=valueFontColor, showvalue=1, command=self.OnCropUpdate)
        self.lblResize.grid(row=rowIdx, column=0, sticky=W, padx=padding, pady=padding)
        self.sclResize.grid(row=rowIdx, column=1, columnspan=15, sticky=W, padx=padding-3, pady=padding-3)

        rowIdx += 1
        self.lblNumColors = Label(self.boxTweaks, text="Quality")
        self.sclNumColors = Scale(self.boxTweaks, from_=1, to=100, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=self.guiConf['mainSliderHeight'], length=self.guiConf['mainSliderWidth'], font=self.defaultFontTiny, fg=valueFontColor, showvalue=1)
        self.lblNumColors.grid(row=rowIdx, column=0, sticky=W, padx=padding, pady=padding)
        self.sclNumColors.grid(row=rowIdx, column=1, columnspan=15, sticky=W, padx=padding-3, pady=padding-3)

        rowIdx += 1
        self.lblBright = Label(self.boxTweaks, text="Brightness")
        self.sclBright = Scale(self.boxTweaks, from_=-9, to=9, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=self.guiConf['mainSliderHeight'], length=self.guiConf['mainSliderWidth'], font=self.defaultFontTiny, fg=valueFontColor, showvalue=1)
        #self.sclBright.bind('<Double-Button-1>', self.SnapResetBrightness)

        self.lblBright.grid(row=rowIdx, column=0, sticky=W, padx=padding, pady=padding)
        self.sclBright.grid(row=rowIdx, column=1, columnspan=15, sticky=W, padx=padding-3, pady=padding-3)

        rowIdx += 1
        self.lblSpeedModifier = Label(self.boxTweaks, text="Playback Rate")
        self.sclSpeedModifier = Scale(self.boxTweaks, from_=-10, to=10, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=self.guiConf['mainSliderHeight'], length=self.guiConf['mainSliderWidth'], font=self.defaultFontTiny, fg=valueFontColor,  showvalue=1)
        self.lblSpeedModifier.grid(row=rowIdx, column=0, sticky=W, padx=padding, pady=padding)
        self.sclSpeedModifier.grid(row=rowIdx, column=1, columnspan=16, sticky=W, padx=padding-3, pady=padding-3)

        rowIdx += 1
        self.lblCaption     = Label(self.boxTweaks, text="Captions")
        self.currentCaption = StringVar()    
        self.cbxCaptionList = ttk.Combobox(self.boxTweaks, textvariable=self.currentCaption)
        self.captionTracer  = None

        self.lblCaption.grid          (row=rowIdx, column=0, columnspan=1, rowspan=1, sticky=W,  padx=padding, pady=padding)
        self.cbxCaptionList.grid      (row=rowIdx, column=1, columnspan=8, rowspan=1, sticky=EW, padx=padding, pady=padding)

        rowIdx += 1

        self.isGrayScale        = IntVar()
        self.isSharpened        = IntVar()
        self.sharpenedAmount    = IntVar()
        self.isDesaturated      = IntVar()
        self.desaturatedAmount  = IntVar()
        self.isSepia            = IntVar()
        self.sepiaAmount        = IntVar()
        self.isColorTint        = IntVar()
        self.colorTintAmount    = IntVar()
        self.colorTintColor     = StringVar()
        self.isFadedEdges       = IntVar()
        self.fadedEdgeAmount    = IntVar()
        self.isNashville        = IntVar()
        self.nashvilleAmount    = IntVar()
        self.isBlurred          = IntVar()
        self.blurredAmount      = IntVar()
        self.isBordered         = IntVar()
        self.borderAmount       = IntVar()
        self.borderColor        = StringVar()
        self.isCinemagraph      = IntVar()
        self.invertCinemagraph  = IntVar()
        self.isAudioEnabled     = IntVar()

        self.sepiaAmount.set(100)
        self.desaturatedAmount.set(100)
        self.sharpenedAmount.set(100)
        self.fadedEdgeAmount.set(100)
        self.colorTintAmount.set(100)
        self.borderAmount.set(100)
        self.colorTintColor.set("#0000FF")
        self.borderColor.set("#000000")
        self.nashvilleAmount.set(100)
        self.blurredAmount.set(100)

        self.isSharpened.trace       ("w", self.OnEffectsChange)
        self.sharpenedAmount.trace   ("w", self.OnEffectsChange)
        self.isDesaturated.trace     ("w", self.OnEffectsChange)
        self.desaturatedAmount.trace ("w", self.OnEffectsChange)
        self.isSepia.trace           ("w", self.OnEffectsChange)
        self.sepiaAmount.trace       ("w", self.OnEffectsChange)        
        self.isColorTint.trace       ("w", self.OnEffectsChange)
        self.colorTintAmount.trace   ("w", self.OnEffectsChange)
        self.colorTintColor.trace    ("w", self.OnEffectsChange)
        self.isFadedEdges.trace      ("w", self.OnEffectsChange)
        self.fadedEdgeAmount.trace   ("w", self.OnEffectsChange)
        self.isGrayScale.trace       ("w", self.OnEffectsChange)
        self.isBordered.trace        ("w", self.OnEffectsChange)
        self.borderAmount.trace      ("w", self.OnEffectsChange)
        self.borderColor.trace       ("w", self.OnEffectsChange)
        self.isCinemagraph.trace     ("w", self.OnEffectsChange)
        self.isNashville.trace       ("w", self.OnEffectsChange)
        self.nashvilleAmount.trace   ("w", self.OnEffectsChange)
        self.isBlurred.trace         ("w", self.OnEffectsChange)
        self.blurredAmount.trace     ("w", self.OnEffectsChange)
        self.invertCinemagraph.trace ("w", self.OnEffectsChange)
        self.isAudioEnabled.trace    ("w", self.OnEffectsChange)

        self.lblEffects     = Label(self.boxTweaks, text="FX & Filters")
        self.btnEditEffects = Button(self.boxTweaks, text="Open Effects Panel...", font=self.defaultFontTiny, command=self.OnEditEffects)
        self.lblEffects.grid     (row=rowIdx, column=0, sticky=W, padx=padding, pady=padding)
        self.btnEditEffects.grid (row=rowIdx, column=1, columnspan=4, sticky="EW", padx=padding, pady=padding)

        #padding =  # Restore padding

        rowIdx += 1


        self.btnGenerateGif = Button(frame, text="Create GIF!", height=2, font=self.defaultFontBig, command=self.OnCreateGif)
        self.btnGenerateGif.grid(row=rowIdx, column=0, columnspan=8, sticky="EW", padx=padding, pady=padding)

        self.ResetInputs()

        # Show window
        self.parent.update()
        self.parent.deiconify()

        self.CenterWindow(self.parent)
        self.EnableInputs(False, True)

        #
        # Set default boolean menu settings
        #

        self.qualityMenu.invoke(youtubeQualityList.index(defaultQuality))


        if self.conf.GetParamBool("settings", "overwriteGif"):
            self.settingsMenu.invoke(0) # Argument refers to menu index

        if self.conf.GetParamBool("warnings", "socialMedia"):
            self.settingsMenu.invoke(1)

        if self.conf.GetParamBool("size", "fileOptimizer"):
            self.settingsMenu.invoke(4)

        # Load button gets focus
        self.btnFopen.focus()

        # Start timer
        self.RestartTimer()

        self.parent.bind("<Escape>", self.OnCancel)

        # Screen Capture Dialog variables
        #######################################################################

        self.screenCapDurationSec = StringVar()
        self.screenCapLowerFps    = IntVar()
        self.screenCapRetina      = IntVar()
        self.screenCapShowCursor  = IntVar()
        self.screenCapDurationSec.set(5.0)


        #
        # Tool Tips
        #

        tooltips = {   
            self.txtFname:          "",
            self.btnFopen:          "You can paste almost any website address containing a video. Otherwise leave the text field empty and click this button to browse your computer for a video. RIGHT-CLICK on this button if you want to multi-select images.",
            self.btnScreenCap:      "Want to record your screen? Use this feature to record game playback, Kodi, or whatever else.",

            self.sclStart:          'Use this slider to configure the time in the video where you want the GIF to begin. After a few seconds, Instagiffer will grab frames starting from here and put them in the preview area to the right.',
            self.spnStartTimeHour:  "Video extraction start time: Hour",
            self.spnStartTimeMin:   "Video extraction start time: Minute",
            self.spnStartTimeSec:   "Video extraction start time: Second",
            self.spnStartTimeMilli: "Video extraction start time: Sub-second",
    
            self.sclFps:            "Choppy/Smooth: Use this slider to control the frame rate of your GIF. Increasing this setting will include more frames making the file size larger. This feature is disabled in Screen Capture mode.",
            self.sclResize:         "Tiny/Big: Use this slider to control the image size from 5% (for ants!) to 100%. Note: increasing this setting will make the file size larger.",
            self.sclNumColors:      "Low Quality/High Quality: Use this slider to control the images color quality.",
            self.sclBright:         "Dark/Bright: Control the image brightness. This setting does not normally affect the GIF file size.",
            self.sclSpeedModifier:  "Slowmo/Superfast: Slow down or speed up the playback rate. Does not affect the GIF file size.",
            self.btnEditEffects:    "All of the effects have been moved and improved. Click here to access.",
            self.cbxCaptionList:    "", #"Click here to add some text to your GIF",

            self.btnTrackbarLeft:   "View the previous frame. If you hold this button down, it will animate at the correct speed, but in reverse.",
            self.btnTrackbarRight:  "View the next frame. If you hold this button down, it will animate at the correct speed.",
        }

        # Bind tool tips
        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        logging.info("Instagiffer main window has been created")

        if cmdlineVideoPath is not None:
            self.txtFname.insert(0, cmdlineVideoPath)
            self.OnLoadVideoEnterPressed(None)

    def CreateAppDataFolder(self):
        self.tempDir = CreateWorkingDir(self.conf)

        if self.tempDir == "":
            self.Alert("Failed to create working folder", "Unable to create working directory")
            raise SystemExit

    def ForceSingleInstance(self):
        # Enforced by plist setting in Mac
        if ImAPC():
            import win32api
            from   win32event import CreateMutex
            from   winerror   import ERROR_ALREADY_EXISTS

            self.singleInstanceMutex = CreateMutex(None, False, "instagiffer_single_instance_mutex")
            if (win32api.GetLastError() == ERROR_ALREADY_EXISTS):
                self.Alert("Instagiffer is already running!",
                           "It looks like Instagiffer is already running. Please close it first.")
                raise SystemExit


    def OnDeleteTemporaryFiles(self, prompt = True):
        deleteConfirmed = False
        if prompt:
            deleteConfirmed = tkMessageBox.askyesno("Are You Sure?", "This will delete all downloads as well as the session currently in progress. Are you sure? The following directory will be deleted:\n\n" + self.tempDir)
        else:
            deleteConfirmed = True            

        if deleteConfirmed:
            if self.gif is not None:
                self.gif = None
                self.ResetInputs()
                self.EnableInputs(False, True)
            try:
                if os.path.exists(self.tempDir):
                    shutil.rmtree(self.tempDir)
            except Exception as e:
                self.Alert("Delete Failed", "I was unable to delete Instagiffer's temporary files. Please delete the following folder manually:\n\n" + self.tempDir)
                return False

        logging.info("Temporary files deleted")
        return True

    def ReadConfig(self):
        # Read config
        self.conf.ReloadFromFile()

        # Menu config items
        if self.savePath != None:
            self.conf.SetParam('paths', 'gifOutputPath', self.savePath)

        # Read menu settings
        self.OnChangeMenuSetting()

    def ChangeFileFormat(self, newFormat):
        if self.gif is None:
            return False

        if len(newFormat) == 0:
            newFormat = 'gif'

        fname, fext = os.path.splitext(self.gif.GetNextOutputPath())
        return self.OnSetSaveLocation(fname + '.' + newFormat)

    def OnSetSaveLocation(self, location=None):
        if location is None:
            formatList = [("Supported formats", ("*.gif", "*.webm", "*.mp4"))]

            if self.savePath is not None:
                default = self.savePath
            else:
                default = "insta.gif"

            savePath = asksaveasfilename(filetypes=formatList, initialfile=default)

            if savePath == "":
                return
        else:
            savePath = location

        if not GetFileExtension(savePath) in [ 'gif', 'webm', 'mp4' ]:
            savePath += '.gif'

        if self.savePath != savePath:
            self.miscGifChanges += 1

        self.savePath = savePath

        self.conf.SetParam('paths', 'gifOutputPath', self.savePath)

        if self.gif != None:
            self.gif.SetSavePath(self.savePath)

        self.SetStatus("Updated save location to " + self.savePath)

    def OnImgurUpload(self):
        ret = None
        imgurErrorTitle      = "Imgur Upload Failed"
        imgurUploadSizeLimit = 2 * 1024 * 1024
        imgurFormat          = 'gif'

        if self.gif is None or not self.gif.GifExists():
            self.Alert(imgurErrorTitle, "You haven't created your GIF yet. Just go ahead and click 'Create Gif' then try this again.")
            return False
        elif self.gif.GetFinalOutputFormat() != imgurFormat:
            self.Alert(imgurErrorTitle, "File format must be %s!" % (imgurFormat))
            return False
        elif self.gif.GetSize() >= imgurUploadSizeLimit:
            self.Alert(imgurErrorTitle, "File size must be under %d MB!" % (imgurUploadSizeLimit/(1024*1024)))
            return False

        self.SetStatus("Uploading GIF to Imgur... During this time, Instagiffer will appear frozen. Patience, K?")
        ret = self.gif.UploadGifToImgur()
        self.SetStatus("Gif uploaded to Imgur. URL: %s" % (ret))            

        if ret is None:
            self.Alert(imgurErrorTitle, "Failed to upload GIF to Imgur. Grrrrr...")
            return False
        else:
            self.Alert("Imgur Upload Succeeded!", "Your GIF has been uploaded. The following address has been copied to your clipboard:\n\n%s" % (ret))
            return True


    def OnSaveVideoForLater(self):
        if self.gif == None:
            return False

        title = self.gif.GetVideoFileName()

        if not len(title):
            self.Alert("Not a Video File", "Source media is not in video format. This feature is for video files only!")
        else:
            savePath = asksaveasfilename(filetypes=[("All files", "*.*")], initialfile=title)
            if len(savePath):
                self.gif.SaveOriginalVideoAs(savePath)

        return False


    # This is the UI handler for all checkbox menu items
    def OnChangeMenuSetting(self):

        # Warning settings

        if len(self.socialMediaWarningsEnabled.get()):
            self.conf.SetParam('Warnings', 'socialMedia', bool(int(self.socialMediaWarningsEnabled.get()) == 1))

         # Overwrite setting 

        if len(self.overwriteOutputGif.get()):
            overwriteFlag = bool(int(self.overwriteOutputGif.get()) == 1)
            
            # Update the configuration object
            self.conf.SetParam('Settings', 'overwriteGif', overwriteFlag)

            # Update the GIF object with the new settings too

            if self.gif:
                self.gif.OverwriteOutputGif(overwriteFlag)

        # Download quality setting
        self.conf.SetParam('settings', 'downloadQuality',  self.downloadQuality.get())

        # File size optimize
        if len(self.fileSizeOptimize.get()):
            self.frameTimingOrCompressionChanges += self.conf.SetParam('size', 'fileOptimizer', bool(int(self.fileSizeOptimize.get()) == 1))

    def OnCancel(self, event):
        if self.guiBusy:
            if tkMessageBox.askyesno("Cancel Request", "Are you sure you want to cancel the current operation?"):
                logging.info("Cancel Event")
                self.cancelRequest = True

    def OnFpsChanged(self, event):
        self.RestartTimer()


    def OnDurationMouseWheel(self, event):
        duration = float(self.duration.get())
        max_dur  = float(self.spnDuration.cget("to"))
        min_dur  = float(self.spnDuration.cget("from"))

        if event.num == 5 or event.delta == -120:
            duration -= 0.1
        if event.num == 4 or event.delta == 120:
            duration += 0.1

        if duration < min_dur:
            duration = max_dur
        elif duration > max_dur:
            duration = min_dur

        self.duration.set("%.1f"%(duration))
        self.OnDurationChanged()



    def OnDurationChanged(self):
        self.RestartTimer()

        retVal = True

        try:
            duration = float(self.duration.get())
            if duration < 0.1:
                retVal = False
        except ValueError:
            retVal = False

        return True

    def TrackbarToTimeFields(self):
        positionSec = self.sclStart.get()
        positionComponents = MillisecToDurationComponents(positionSec * 1000)

        self.spnStartTimeHour.delete(0,"end")
        self.spnStartTimeHour.insert(0, "%d" % positionComponents[0])

        self.spnStartTimeMin.delete(0,"end")
        self.spnStartTimeMin.insert(0, "%02d" % positionComponents[1])

        self.spnStartTimeSec.delete(0,"end") 
        self.spnStartTimeSec.insert(0, "%02d" % positionComponents[2])

        self.spnStartTimeMilli.delete(0,"end")
        self.spnStartTimeMilli.insert(0, "0")

    def OnStartSliderUpdated(self, unknown):
        # if self.gif is not None:
        #     if self.gif.GetThumbAge() > 0.9:
        #         self.gif.GetVideoThumb(self.GetStartTimeString(), self.canvasSize)
        #         if self.gif.ThumbFileExists():
        #             self.ShowImageOnCanvas(self.gif.GetThumbImagePath())

        self.TrackbarToTimeFields()
        self.OnStartChanged()
        return True

    def OnStartChanged(self, widget_name = '', prior_value = ''):
        trackbarPosSec = DurationStrToSec("%02d:%02d:%02d:%03d" % (int(self.spnStartTimeHour.get()), int(self.spnStartTimeMin.get()), int(self.spnStartTimeSec.get()), 100*int(self.spnStartTimeMilli.get())))

        maxTrackbarPos = 0

        if self.gif is not None:
            maxTrackbarPos = int(self.gif.GetVideoLengthSec()) - 2
            if maxTrackbarPos < 0:
                maxTrackbarPos = 0

        if maxTrackbarPos != 0 and trackbarPosSec > maxTrackbarPos:
            trackbarPosSec = maxTrackbarPos
            self.TrackbarToTimeFields()


        self.sclStart.set(trackbarPosSec)

        self.RestartTimer()

    def SetStatus(self, status):
        if self.status.cget("text") != status:
            logging.info("SetStatus: '" + status + "'")            
            self.status.config(text=status)
            self.status.update_idletasks()

    def CenterWindow(self, widget):
        widget.update_idletasks()
        width  = widget.winfo_width()
        height = widget.winfo_height()
        x      = (widget.winfo_screenwidth() / 2) - (width / 2)
        y      = (widget.winfo_screenheight() / 2) - (height / 2)
        widget.geometry('{0}x{1}+{2}+{3}'.format(width, height, x, y))

    def InitializeCropTool(self):
        if not self.gif:
            return False

        #logging.info("Initialize Cropper")
        videoWidth  = self.gif.GetVideoWidth()
        videoHeight = self.gif.GetVideoHeight()
        scaleFactor = self.canvasSize / float(max(videoWidth, videoHeight))
        newWidth    = videoWidth  * scaleFactor
        newHeight   = videoHeight * scaleFactor
        previewX    = 0
        previewY    = 0
        previewX2   = 0
        previewY2   = 0

        # Set the resize value to match the scaled preview
        self.sclResize.set(scaleFactor*100)

        if newWidth < self.canvasSize:
            previewX = int((self.canvasSize - newWidth) / 2) - 1

        if newHeight < self.canvasSize:
            previewY = int((self.canvasSize - newHeight) / 2) - 1

        previewX2 = previewX + newWidth
        previewY2 = previewY + newHeight

        self.frameCounterStr.set("")
        self.canCropTool.delete('all')
        self.canCropTool.create_rectangle(previewX, previewY, previewX2, previewY2, outline="black", fill="gray13", width=1, tag='videoScale')
        self.canCropTool.create_rectangle(previewX, previewY, previewX2, previewY2, width=1, outline="red", tag='cropRect')
        self.canCropTool.create_rectangle(0, 0, 0, 0, outline="black", fill="red",   width=1, tag='cropSizeTL')
        self.canCropTool.create_rectangle(0, 0, 0, 0, outline="black", fill="red",   width=1, tag='cropSizeBR')
        self.canCropTool.create_rectangle(0, 0, 0, 0, outline="red",   fill="black", width=1, tag='cropMove')

        if ImAMac():
            whichRMouseEvent = '<B2-Motion>'
        else:
            whichRMouseEvent = '<B3-Motion>'

        self.canCropTool.tag_bind('cropMove',   '<B1-Motion>', self.OnCropMove)
        self.canCropTool.tag_bind('cropSizeTL', '<B1-Motion>', self.OnCropSizeTL)
        self.canCropTool.tag_bind('cropSizeBR', '<B1-Motion>', self.OnCropSizeBR)
        self.canCropTool.tag_bind('cropSizeTL', whichRMouseEvent, self.OnCropSizeTLRestrictAxis)
        self.canCropTool.tag_bind('cropSizeBR', whichRMouseEvent, self.OnCropSizeBRRestrictAxis)

        self.canCropTool.bind("<Double-Button-1>", self.OnDoubleClickDelete)
        self.OnCropUpdate()


    # This function needs to be re-entrant!!
    def UpdateThumbnailPreview(self):
        if self.gif == None:
            return

        self.canCropTool.delete('previewBG')
        self.canCropTool.delete('preview')

        imgList = self.gif.GetExtractedImageList()

        if len(imgList) <= 0:
            self.canCropTool.delete('thumbnail')
            return

        arrayIdx = self.GetThumbNailIndex() - 1

        try:
            imgPath = imgList[arrayIdx]
        except IndexError:
            logging.error("Error. %d out of range" % (arrayIdx))
            return

        (px, py, px2, py2) = self.canCropTool.coords('videoScale')

        img = None

        # Cached thumbnail mode
        if self.conf.GetParamBool('settings', 'cacheThumbs'):
            # Update thumbnail memory cache
            framesOnDiskTs = self.gif.GetExtractedImagesLastModifiedTs()
            if self.thumbNailsUpdatedTs < framesOnDiskTs:
                logging.info("Thumbnail cache is stale (%d < %d)" % (self.thumbNailsUpdatedTs, framesOnDiskTs))
                self.thumbNailsUpdatedTs = -1
                newThumbCache            = dict()
                self.thumbNailCache      = dict() # erase cache

                self.SetStatus("Updating thumbnail previews...")

                for thumbPath in imgList:
                    self.OnShowProgress(False)
                    try:
                        newThumbCache[thumbPath] = PIL.Image.open(thumbPath)
                        newThumbCache[thumbPath] = newThumbCache[thumbPath].resize((int(px2-px) + 1, int(py2-py) + 1), PIL.Image.NEAREST)
                    except IOError:
                        logging.error("Unable to generate thumbnail for %s. Image does not exist" % (thumbPath))
                        self.thumbNailsUpdatedTs = -2
                        return

                self.SetStatus("")
                self.OnShowProgress(True)

                self.thumbNailCache      = newThumbCache
                self.thumbNailsUpdatedTs = time.time()

            try:
                img = self.thumbNailCache[imgPath]
            except:
                logging.error("Thumbnail cache miss: %s. Marking thumbnail cache as stale" % imgPath)
                self.thumbNailsUpdatedTs = -3
                return
        #
        # Direct-from-disk thumbnail mode
        #       
        else:
            img = PIL.Image.open(imgPath)
            img = img.resize((int(px2-px) + 1, int(py2-py) + 1), PIL.Image.ANTIALIAS)
    
        self.thumbnailPreview = PIL.ImageTk.PhotoImage(img)
        self.canCropTool.delete('thumbnail')
        self.canCropTool.create_image(px, py, image=self.thumbnailPreview, tag="thumbnail", anchor=NW)
        self.canCropTool.tag_lower("videoScale")
        self.canCropTool.tag_raise("cropRect")
        self.canCropTool.tag_raise("cropMove")
        self.canCropTool.tag_raise("cropSizeTL")
        self.canCropTool.tag_raise("cropSizeBR")

        # Update frame counter and track bar
        if len(imgList):
            self.frameCounterStr.set("Frame  %d / %d" % (self.thumbnailIdx, len(imgList)))
            self.sclFrameTrackbar.configure(to = len(imgList)) # This can recurse?


    def TrackbarCanPlay(self):
        since = (time.time() - self.trackBarTs) * 1000

        frameDelayMs = 100
        if self.gif:
            frameDelayMs = self.gif.GetGifFrameDelay(self.sclSpeedModifier.get()) * 10

        lateByMs = since - frameDelayMs
        if lateByMs < 80 and lateByMs > frameDelayMs:
            skipFrame = 1 + int(round(lateByMs/float(frameDelayMs)))
            self.trackBarTs = time.time()
            #logging.info("late by %d ms (frame delay %d) frames %f" %(lateByMs, frameDelayMs, skipFrame))
            return skipFrame
        elif since < 0 or since > frameDelayMs:
            self.trackBarTs = time.time()
            return 1
        else:
            return 0


    def OnTrackbarLeft(self):
        framesCount = self.TrackbarCanPlay()

        if framesCount >= 1:
            self.SetThumbNailIndex(self.GetThumbNailIndex() - framesCount) 
            self.UpdateThumbnailPreview()
            self.parent.update_idletasks()
        return True

    def OnTrackbarRight(self):
        framesCount = self.TrackbarCanPlay()

        if framesCount >= 1:
            self.SetThumbNailIndex(self.GetThumbNailIndex() + framesCount)
            self.UpdateThumbnailPreview()
            self.parent.update_idletasks()
        return True

    def OnFrameTrackbarMove(self, newVal):
        self.SetThumbNailIndex(int(newVal))
        self.UpdateThumbnailPreview()
        return True

    def ResetFrameTrackbar(self):
        self.sclFrameTrackbar.set("1")

    def GetThumbNailIndex(self):
        return self.thumbnailIdx

    def SetThumbNailIndex(self, idx = None):
        trackBarPos = 0

        if idx == None:
            idx = self.thumbnailIdx

        if self.gif == None:
            idx = 1
        else:
            if idx <= 0:
                idx = self.gif.GetNumFrames()
            elif idx > self.gif.GetNumFrames():
                idx = 1

        self.sclFrameTrackbar.set(idx)
        self.thumbnailIdx = idx

    def OnDoubleClickDelete(self, event):
        if self.gif == None or self.guiBusy:
            return

        # last frame currently selected
        isLastFrame = False
        if self.gif.GetNumFrames() == self.thumbnailIdx:
            isLastFrame = True

        ret = self.DeleteFrame(self.thumbnailIdx, self.thumbnailIdx)

        #  Issue #157
        if isLastFrame and self.gif.GetNumFrames() > 0:
            self.SetThumbNailIndex(self.gif.GetNumFrames())


    def DeleteFrame(self, fromIdx, toIdx, evenOnly = 0):
        frameList         = self.gif.GetExtractedImageList()
        countBeforeDelete = len(frameList)

        # Out of range
        if fromIdx > countBeforeDelete:
            return True

        if evenOnly:
            stepSize = 2
        else:
            stepSize = 1

        # Do we have frames to delete
        if countBeforeDelete > 1:
            for x in range(fromIdx - 1, toIdx, stepSize):
                try:
                    os.remove(frameList[x])
                except IndexError:
                    break

                self.SetStatus("Deleted frame %d '%s' from animation sequence" % (x+1, os.path.basename(frameList[x])))

        # Tell cache not to update. Deletes are OK
        self.thumbNailsUpdatedTs = time.time()

        self.SetThumbNailIndex()

        # Update the frame counter
        if len(frameList) > 0:
            self.UpdateThumbnailPreview()
        else:
            self.frameCounterStr.set("")

        return True


    def TranslateToCanvas(self, val):
        if self.gif is None:
            return 0

        frameScale       = self.sclResize.get()/100.0
        videoWidth       = self.gif.GetVideoWidth()
        videoHeight      = self.gif.GetVideoHeight()
        scaleFactor      = float(self.canvasSize) / (frameScale*max(videoWidth, videoHeight))

        ret = val * scaleFactor
        return ret


    def GetCropSettingsFromCanvas(self, isScaled=True, doRounding=True):
        if len(self.canCropTool.find_withtag("cropRect")) <= 0:
            raise Exception("Cropper has not been initialized yet")

        if len(self.canCropTool.find_withtag("preview")) > 0:
            raise Exception("Preview being displayed. Wait..")


        (cx, cy, cx2, cy2) = self.canCropTool.coords('cropRect')
        (px, py, px2, py2) = self.canCropTool.coords('videoScale')

        videoWidth       = self.gif.GetVideoWidth()
        videoHeight      = self.gif.GetVideoHeight()
        scaleFactor      = max(videoWidth, videoHeight) / float(self.canvasSize)

        if isScaled:
            frameScale = self.sclResize.get()/100.0
        else:
            frameScale = 1.0

        rw     = (cx2 - cx)  * scaleFactor * frameScale
        rh     = (cy2 - cy)  * scaleFactor * frameScale
        ratio  = rw/rh
        rw     = rw
        rh     = rh

        rx     = (cx - px)   * scaleFactor * frameScale
        ry     = (cy - py)   * scaleFactor * frameScale
        rwmax  = videoWidth  * frameScale
        rhmax  = videoHeight * frameScale

        if doRounding:
            return int(round(rx)), int(round(ry)), int(round(rw)), int(round(rh)), int(round(rwmax)), int(round(rhmax)), ratio
        else:
            return rx, ry, rw, rh, rwmax, rhmax, ratio

    def SnapCropperHandles(self):
        if len(self.canCropTool.find_withtag("cropRect")) <= 0:
            return

        (cx, cy, cx2, cy2) = self.canCropTool.coords('cropRect')
        (px, py, px2, py2) = self.canCropTool.coords('videoScale')

        if cx < px:
            cx = px
        if cy < py:
            cy = py
        if cx2 > px2:
            cx2 = px2
        if cy2 > py2:
            cy2 = py2

        # Correct cropper rect
        self.canCropTool.coords('cropRect',
            cx,
            cy,
            cx2,
            cy2)

        # Move sizer and mover handles
        self.canCropTool.coords('cropSizeTL',
            cx,
            cy,
            cx + self.cropSizerSize,
            cy + self.cropSizerSize)

        self.canCropTool.coords('cropSizeBR',
            cx2 - self.cropSizerSize,
            cy2 - self.cropSizerSize,
            cx2,
            cy2)

        self.canCropTool.coords('cropMove',
            cx  + (cx2 - cx)/2 - self.cropSizerSize/2,
            cy  + (cy2 - cy)/2 - self.cropSizerSize/2,
            cx  + (cx2 - cx)/2 + self.cropSizerSize/2,
            cy  + (cy2 - cy)/2 + self.cropSizerSize/2)



    def OnCropUpdate(self, unused = None):
        try:
            sx, sy, sw, sh, smaxw, smaxh, sratio = self.GetCropSettingsFromCanvas(True)
            x,  y,  w,  h,  maxw,  maxh,  ratio  = self.GetCropSettingsFromCanvas(False)
        except:
            return

        self.SnapCropperHandles()

        self.cropWidth   = str(w)
        self.cropHeight  = str(h)
        self.cropStartX  = str(x)
        self.cropStartY  = str(y)
        self.finalSize   = '%dx%d'%(sw, sh)

        self.frameDimensionsStr.set(self.finalSize + ", ratio: %.3f:1" % (sratio))

    def OnCropMove(self, event):
        (cx, cy, cx2, cy2) = self.canCropTool.coords('cropRect')
        (px, py, px2, py2) = self.canCropTool.coords('videoScale')
        (mx, my, mx2, my2) = self.canCropTool.coords('cropMove')

        deltaX = (event.x - mx) - self.cropSizerSize/2
        deltaY = (event.y - my) - self.cropSizerSize/2

        if cy + deltaY < py:
            deltaY = (cy - py) * -1
        if cy2 + deltaY > py2:
            deltaY = (cy2 - py2) * -1
        if cx + deltaX < px:
            deltaX = (cx - px) * -1
        if cx2 + deltaX > px2:
            deltaX = (cx2 - px2) * -1

        self.canCropTool.coords('cropRect', cx + deltaX, cy + deltaY, cx2 + deltaX, cy2 + deltaY)
        self.OnCropUpdate()


    def OnCropSizeTL(self, event):
        self.OnCropSizeTLImpl(False, event)

    def OnCropSizeTLRestrictAxis(self, event):
        self.OnCropSizeTLImpl(True, event)

    def OnCropSizeTLImpl(self, freezeX, event):
        (cx, cy, cx2, cy2) = self.canCropTool.coords('cropRect')
        (px, py, px2, py2) = self.canCropTool.coords('videoScale')
        (sx, sy, sx2, sy2) = self.canCropTool.coords('cropSizeTL')

        deltaX = event.x - sx
        deltaY = event.y - sy

        if freezeX:
            deltaX = 0

        if sx + deltaX < px:
            deltaX = (sx - px) * -1
        if sy + deltaY < py:
            deltaY = (sy - py) * -1
        if sy2 + deltaY > cy2:
            deltaY = cy2 - sy2
        if sx2 + deltaX > cx2:
            deltaX = cx2 - sx2

        self.canCropTool.coords('cropRect', cx + deltaX, cy + deltaY, cx2, cy2)
        self.OnCropUpdate()

    def OnCropSizeBR(self, event):
        self.OnCropSizeBRImpl(False, event)

    def OnCropSizeBRRestrictAxis(self, event):
        self.OnCropSizeBRImpl(True, event)

    def OnCropSizeBRImpl(self, freezeY, event):
        (cx, cy, cx2, cy2) = self.canCropTool.coords('cropRect')
        (px, py, px2, py2) = self.canCropTool.coords('videoScale')
        (sx, sy, sx2, sy2) = self.canCropTool.coords('cropSizeBR')

        deltaX = event.x - sx
        deltaY = event.y - sy

        if freezeY:
            deltaY = 0

        if sx2 + deltaX > px2:
            deltaX = px2 - sx2
        if sy2 + deltaY > py2:
            deltaY = py2 - sy2
        if sy + deltaY < cy:
            deltaY = (sy - cy) * -1
        if sx + deltaX < cx:
            deltaX = (sx - cx) * -1

        self.canCropTool.coords('cropRect', cx, cy, cx2 + deltaX, cy2 + deltaY)
        self.OnCropUpdate()

    def OnShowProgress(self, doneFlag, statusBarOutput=None):

        if type(doneFlag) == bool and doneFlag:
            self.progressBarPosition.set(0)
            self.guiBusy = False
        else:
            if statusBarOutput is not None:
                self.SetStatus(statusBarOutput.replace('\n', '').replace('\r', ''))

            if type(doneFlag) == int:
                self.progressBarPosition.set(doneFlag)
            else:
                self.progressBar.step(1) # indefinite

            self.guiBusy = True

        self.parent.update_idletasks()
        self.parent.update()

        if self.cancelRequest:
            self.progressBarPosition.set(0)            
            self.cancelRequest = False
            return False
        else:
            return True

    def OnWindowClose(self):
        # Cancel any actions in progress
        self.OnCancel(None)

        if self.conf:
            if self.conf.GetParamBool('settings', 'deleteTempFilesOnClose'):
                self.OnDeleteTemporaryFiles(False) # Don't prompt

        self.parent.quit()

    def RestartTimer(self):
        if self.timerHandle is not None:
            self.parent.after_cancel(self.timerHandle)
        self.timerHandle = self.parent.after(self.mainTimerValueMS, self.OnTimer)


    def OnTimer(self):
        if not self.guiBusy:
            if self.conf.GetParamBool('settings', 'autoExtract'):        
                self.ProcessImage(1)

        self.RestartTimer()

    def OnViewImageStillsInExplorer(self):
        self.ProcessImage(1)

        openExplorerCmd = ""

        if ImAPC():
            openExplorerCmd = 'explorer '
        elif ImAMac():
            openExplorerCmd = 'open '
        else:
            openExplorerCmd = 'xdg-open '

        openExplorerCmd += '"' + self.gif.GetExtractedImagesDir() + '"'
        logging.info("Open in explorer command: " + openExplorerCmd)

        if not ImAPC():
            openExplorerCmd = shlex.split(openExplorerCmd)

        subprocess.Popen(openExplorerCmd)

    def Alert(self, title, message):
        logging.info("Alert: title: [%s], message: [%s]" % (title, message.strip()))
        tkMessageBox.showinfo(title, message)
    
    def OnRClickPopup(self, event):
        def RClickPaste(event):
            if ImAMac():
                pasteAction = '<<Paste>>'
            else:
                pasteAction = '<Control-v>'

            event.widget.event_generate(pasteAction)

        def RClickClear(event):
            event.widget.delete(0, END)

        event.widget.focus()
        popUp = Menu(None, tearoff=0, takefocus=0)
        popUp.add_command(label='Paste', command=lambda event=event: RClickPaste(event))
        popUp.add_command(label='Clear', command=lambda event=event: RClickClear(event))
        popUp.tk_popup(event.x_root+40, event.y_root+10, entry="0")

    def About(self, event = None):
        global __version__
        self.Alert("About Instagiffer",
                   "You are running Instagiffer " + __version__ + "!\nFollow us on Tumblr for updates, tips and tricks: www.instagiffer.com")

    def ViewLog(self):
        numLines = sum(1 for line in open(GetLogPath()))

        if numLines <= 7:
            tkMessageBox.showinfo("Bug Report", "It looks like the bug report is currently empty. Please try to reproduce the bug first, and then generate the report")

        OpenFileWithDefaultApp(GetLogPath())

    def OpenFAQ(self):
        OpenFileWithDefaultApp(__faqUrl__)

    def CheckForUpdates(self):
        OpenFileWithDefaultApp(__changelogUrl__)

    def ResetInputs(self):
        self.canCropTool.delete('all')  # Clear off the crop tool
        #if not self.gif.ExtractedImagesExist():
        self.InitializeCropTool()

        self.maskEventList = [] # Remove all mask edits

        if self.captionTracer is not None:
            self.currentCaption.trace_vdelete("w", self.captionTracer)
            self.captionTracer = None       

        self.cbxCaptionList["values"] = ('[Click here to add a new caption]',)
        self.cbxCaptionList.current(0)
        self.captionTracer = self.currentCaption.trace("w", self.OnCaptionSelect)

        for strVar in [ self.startTimeHour, self.startTimeMilli ]:
            strVar.set(0)

        for strVar in [ self.startTimeMin, self.startTimeSec ]:
            strVar.set("00")

        for scales in [ self.sclNumColors, self.sclBright, self.sclSpeedModifier, self.sclResize, self.sclFps]: # self.sclSaturation,
            scales.set(-1000)

        #
        # Set the maximum slider value for smoothness (FPS). Should not be able to set greater than the source material's fps
        #
        fps = self.conf.GetParam('rate', 'maxFrameRate')

        if self.gif is not None and self.gif.GetVideoFps() < fps:
            fps = self.gif.GetVideoFps()

        self.sclFps.config(to = fps)
        self.sclStart.set(0)

    def ValidateInputs(self):
        retVal = True

        if not self.startTimeHour.get().isdigit() or int(self.startTimeHour.get()) < 0 or int(self.startTimeHour.get()) > 9:
            retVal = False
        if not self.startTimeMin.get().isdigit() or int(self.startTimeMin.get()) < 0 or int(self.startTimeMin.get()) > 59:
            retVal = False
        if not self.startTimeSec.get().isdigit() or int(self.startTimeSec.get()) < 0 or int(self.startTimeSec.get()) > 59:
            retVal = False
        if not self.startTimeMilli.get().isdigit() or int(self.startTimeMilli.get()) < 0 or int(self.startTimeMilli.get()) > 9:
            retVal = False

        # try:
        #     duration = float(self.duration.get())
        #     if duration < 0.1:
        #         retVal = False
        # except ValueError:
        #     retVal = False

        return retVal

    #
    # otherOptions: 
    def EnableInputs(self, optionsRequiringLoadedVideo, otherOptions, forceEnable = False):
       
        if self.gif == None:
            optionsRequiringLoadedVideo = False

        # I need to reword the arguments or clean this up somehow. It's very confusing... the whole function. On the plus side, it works
        timeBasedOptionsAllowed = True
        if self.gif:
            if not forceEnable and not self.gif.SourceIsVideo():
                timeBasedOptionsAllowed = False

        for inputs in [ self.spnStartTimeHour, self.spnStartTimeMin, self.spnStartTimeSec, self.spnStartTimeMilli, self.spnDuration ]:
            if timeBasedOptionsAllowed and optionsRequiringLoadedVideo:
                inputs.configure(state="normal")
            else:
                inputs.configure(state="disabled")

        for inputs in [self.btnGenerateGif, self.sclFrameTrackbar, self.btnTrackbarRight, self.btnTrackbarLeft]:
            if optionsRequiringLoadedVideo:
                inputs.configure(state="normal")
            else:
                inputs.configure(state="disabled")

        if optionsRequiringLoadedVideo:
            if timeBasedOptionsAllowed:
                self.sclFps.configure(state="normal")

            self.cbxCaptionList.configure(state="readonly")
            self.sclNumColors.configure(state="normal")
            self.sclBright.configure(state="normal")
            self.sclResize.configure(state="normal")
            self.sclSpeedModifier.configure(state="normal")
            self.btnEditEffects.configure(state="normal")

            self.fileMenu.entryconfigure(2, state="normal") # imgur

            if self.gif.IsDownloadedVideo():
                self.fileMenu.entryconfigure(0, state="normal") # save for later

            for x in range(0, self.frameMenuItemCount):
               self.frameMenu.entryconfigure(x, state="normal")
         
        else:
            self.fileMenu.entryconfigure(0, state="disabled") # save for later
            self.fileMenu.entryconfigure(2, state="disabled") # imgur

            self.cbxCaptionList.configure(state="disabled")
            self.sclFps.configure(state="disabled")
            self.sclNumColors.configure(state="disabled")
            self.sclBright.configure(state="disabled")
            self.sclResize.configure(state="disabled")
            self.sclSpeedModifier.configure(state="disabled")          
            self.btnEditEffects.configure(state="disabled")


            for x in range(2, 3):
                self.fileMenu.entryconfigure(x, state="disabled")
            for x in range(0, self.frameMenuItemCount):
               self.frameMenu.entryconfigure(x, state="disabled")

        if otherOptions:
            self.btnFopen.configure(state="normal")
            self.btnScreenCap.configure(state="normal")

            for x in (1, 3, 5):
                self.fileMenu.entryconfigure(x, state="normal")
            for x in range(0, 3):
                self.settingsMenu.entryconfigure(x, state="normal") # Doesn't work
            for x in range(0, 3):
                self.qualityMenu.entryconfigure(x, state="normal")
        else:
            self.btnFopen.configure(state="disabled")
            self.btnScreenCap.configure(state="disabled")            

            for x in range(0, 2, 3):
                self.fileMenu.entryconfigure(x, state="disabled")
            for x in range(0, 3):
                self.settingsMenu.entryconfigure(x, state="normal") # Doesn't work
            for x in range(0, 3):
                self.qualityMenu.entryconfigure(x, state="normal")


    def LoadDefaultEntryValues(self, videoLen):
        self.guiBusy = True

        self.lastProcessTsByLevel = [0, 0, 0, 0]

        # The following settings engine -> App

        duration = float(self.gif.GetConfig().GetParam('length',  'durationSec'))

        if duration == 0.0 or (videoLen > 0.0 and videoLen < duration):
            duration = videoLen
        
        self.duration.set(duration)

        if self.gif.SourceIsVideo():
            fps = int(self.gif.GetConfig().GetParam('rate',    'frameRate'))
        else:
            fps = self.gif.GetVideoFps()

        self.sclFps.set(fps)
        self.sclResize.set(          int(self.gif.GetConfig().GetParam('size',    'resizePostCrop')))
        self.sclSpeedModifier.set(   int(self.gif.GetConfig().GetParam('rate',    'speedModifier')))
        self.sclNumColors.set(       int(self.gif.GetConfig().GetParam('color',   'numColors')) / 2.55)
        self.sclBright.set(          int(self.gif.GetConfig().GetParam('effects', 'brightness')) / 10.0)
        self.isGrayScale.set        (    self.gif.GetConfig().GetParam('color',   'colorSpace') == 'Gray')
        self.isDesaturated.set      (int(self.gif.GetConfig().GetParam('color',   'saturation')) < 0)
        self.isBlurred.set          (int(self.gif.GetConfig().GetParam('effects', 'blur')) > 0)
        self.isSharpened.set        (self.gif.GetConfig().GetParamBool('effects', 'sharpen'))
        self.isSepia.set            (self.gif.GetConfig().GetParamBool('effects', 'sepia'))
        self.isFadedEdges.set       (self.gif.GetConfig().GetParamBool('effects', 'fadeEdges'))
        self.isColorTint.set        (self.gif.GetConfig().GetParamBool('effects', 'colorTint'))
        self.isNashville.set        (self.gif.GetConfig().GetParamBool('effects', 'nashville'))
        self.isBordered.set         (self.gif.GetConfig().GetParamBool('effects', 'border'))
        self.isCinemagraph.set      (self.gif.GetConfig().GetParamBool('blend',   'cinemagraph'))
        self.invertCinemagraph.set  (self.gif.GetConfig().GetParamBool('blend',   'cinemagraphInvert'))
        self.isAudioEnabled.set     (self.gif.GetConfig().GetParamBool('audio',   'audioEnabled'))

        self.InitializeCropTool()
        self.guiBusy = False


    def ShowImageOnCanvas(self, fileName):

        if not os.path.exists(fileName):
            return False

        canvasSz = int(self.canvasSize)

        img = PIL.Image.open(fileName)

        #thumbAreaSize = (int(self.canvasSize)+1, int(self.canvasSize)+1)
        #img.thumbnail((canvasSz, canvasSz), PIL.Image.ANTIALIAS)


        w,h = img.size

        if w <= 0 or h <= 0:
            return

        scaleFactor = canvasSz/float(max(w, h))
        img = img.resize((int(scaleFactor * w) + 1, int(scaleFactor * h)+1), PIL.Image.ANTIALIAS)
        w,h = img.size


        x = abs(int((w - canvasSz) / 2)) -1
        y = abs(int((h - canvasSz) / 2)) -1

        if x < 0:
            x = 0
        if y < 0:
            y = 0

        self.thumbnailPreview = PIL.ImageTk.PhotoImage(img)
        self.canCropTool.delete('previewBG')
        self.canCropTool.delete('preview')
        self.canCropTool.create_rectangle(0, 0, canvasSz, canvasSz, outline="black", fill="black", width=1, tag='previewBG')
        self.canCropTool.create_image(x, y, image=self.thumbnailPreview, tag="preview", anchor=NW)


    def OnShowPreview(self, event):
        if self.gif == None:
            return False

        # Right mouse clicks
        if event is not None and (self.guiBusy or self.showPreviewFlag):
            return False

        self.showPreviewFlag = True

        self.ProcessImage(3, True)

        if self.showPreviewFlag == False:
            return False
        
        if self.gif.PreviewFileExists():
            self.ShowImageOnCanvas(self.gif.GetPreviewImagePath())

        return True


    def OnStopPreview(self, event):

        if self.gif == None or self.showPreviewFlag == False:
            return False

        self.UpdateThumbnailPreview()
        self.showPreviewFlag = False

    def OnCreateGif(self):
        self.ProcessImage(3)

    def GetStartTimeString(self):
        return "%02d:%02d:%02d.%03d" % (int(self.spnStartTimeHour.get()), int(self.spnStartTimeMin.get()), int(self.spnStartTimeSec.get()), 100*int(self.spnStartTimeMilli.get()))

    def ProcessImage(self, processStages, preview=False):
        errorMsg = ""
        doUpdateThumbs = False

        if not self.ValidateInputs():
            return False, "Invalid input detected"

        if self.gif == None:
            return False

        timeOrRateSettingChanges = 0
        sizeSettingChanges       = 0
        gifSettingChanges        = 0
        fileFormatSettingChanges = 0

        if processStages >= 1:
            startTime = self.GetStartTimeString()

            timeOrRateSettingChanges += self.gif.GetConfig().SetParam('rate',    'frameRate',   str(self.sclFps.get()))
            timeOrRateSettingChanges += self.gif.GetConfig().SetParam('length',  'startTime',   startTime)
            timeOrRateSettingChanges += self.gif.GetConfig().SetParam('length',  'durationSec', self.spnDuration.get())

            # Sanity checks
            if timeOrRateSettingChanges > 0:
                totalFrames = int(float(self.spnDuration.get())*int(self.sclFps.get()))
                if totalFrames > 9999:
                    return False, "Instagiffer only supports up to 10000 frames per GIF internally"

                if totalFrames > int(self.conf.GetParam('settings', 'largeGif')):
                    if not tkMessageBox.askyesno("Be careful!", "You're about to make a really long GIF. Are you sure you want to continue?"):
                        return False, "User chose not to make a really long GIF"

        if processStages >= 2:
            if self.isCinemagraph.get():
                if self.maskEdited:
                    sizeSettingChanges += 1
                    self.maskEdited     = 0

            sizeSettingChanges += self.cropResizeChanges
            sizeSettingChanges += self.gif.GetConfig().SetParamBool('blend',   'cinemaGraph',        self.isCinemagraph.get())
            sizeSettingChanges += self.gif.GetConfig().SetParamBool('blend',   'cinemaGraphInvert',  self.invertCinemagraph.get())
            sizeSettingChanges += self.gif.GetConfig().SetParam    ('size',    'cropOffsetX',        self.cropStartX)
            sizeSettingChanges += self.gif.GetConfig().SetParam    ('size',    'cropOffsetY',        self.cropStartY)
            sizeSettingChanges += self.gif.GetConfig().SetParam    ('size',    'cropWidth',          self.cropWidth)
            sizeSettingChanges += self.gif.GetConfig().SetParam    ('size',    'cropHeight',         self.cropHeight)
            sizeSettingChanges += self.gif.GetConfig().SetParam    ('size',    'resizePostCrop',     self.finalSize)    #str(self.sclResize.get()))

            if not preview:
                self.cropResizeChanges = 0
            else:
                self.cropResizeChanges += sizeSettingChanges



        if processStages >= 3:
            colorSpace    = "CMYK"
            saturation    = 0
            blur          = 0

            if self.isGrayScale.get():
                colorSpace = "Gray"
            if self.isDesaturated.get():
                saturation -= (self.desaturatedAmount.get())
            if self.isBlurred.get():
                blur = self.blurredAmount.get()

            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'brightness',      str(self.sclBright.get()*10))
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'contrast',        str(self.sclBright.get()*10))
            gifSettingChanges += self.gif.GetConfig().SetParam    ('color',   'saturation',      str(saturation))
            gifSettingChanges += self.gif.GetConfig().SetParamBool('effects', 'sharpen',         self.isSharpened.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'sharpenAmount',   self.sharpenedAmount.get())
            gifSettingChanges += self.gif.GetConfig().SetParamBool('effects', 'sepiaTone',       self.isSepia.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'sepiaToneAmount', self.sepiaAmount.get())
            gifSettingChanges += self.gif.GetConfig().SetParamBool('effects', 'colorTint',       self.isColorTint.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'colorTintAmount', self.colorTintAmount.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'colorTintColor',  self.colorTintColor.get())
            gifSettingChanges += self.gif.GetConfig().SetParamBool('effects', 'fadeEdges',       self.isFadedEdges.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'fadeEdgeAmount',  self.fadedEdgeAmount.get())
            gifSettingChanges += self.gif.GetConfig().SetParamBool('effects', 'border',          self.isBordered.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'borderAmount',    self.borderAmount.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'borderColor',     self.borderColor.get())
            gifSettingChanges += self.gif.GetConfig().SetParamBool('effects', 'nashville',       self.isNashville.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'nashvilleAmount', self.nashvilleAmount.get())
            gifSettingChanges += self.gif.GetConfig().SetParam    ('effects', 'blur',            str(blur))
            gifSettingChanges += self.gif.GetConfig().SetParam    ('color',   'numColors',       str(int(self.sclNumColors.get()*2.55)))
            gifSettingChanges += self.gif.GetConfig().SetParam    ('color',   'colorSpace',      colorSpace)
            gifSettingChanges += self.gif.GetConfig().SetParamBool('audio',   'audioEnabled',    self.isAudioEnabled.get())

            # Make sure we catch any caption and/or image blitting changes
            gifSettingChanges  += self.captionChanges
            gifSettingChanges  += self.miscGifChanges


            # Settings that only affect final file format
            fileFormatSettingChanges += self.audioChanges
            fileFormatSettingChanges += self.frameTimingOrCompressionChanges
            fileFormatSettingChanges += self.gif.GetConfig().SetParam('rate',    'speedModifier',   str(self.sclSpeedModifier.get()))


            # We are assuming we are going to process these settings. Reset change counters
            if not preview:
                self.captionChanges = 0
                self.miscGifChanges = 0
                self.audioChanges   = 0
            else:
                self.miscGifChanges += gifSettingChanges # for now, just store these here


        # This code is too complicated

        # Keep track of the last time edits were made

        if self.lastProcessTsByLevel[1] == 0:
            timeOrRateSettingChanges += 1
        if self.lastProcessTsByLevel[2] == 0 or (self.lastProcessTsByLevel[1] > self.lastProcessTsByLevel[2]) or (self.gif.GetExtractedImagesLastModifiedTs() > self.gif.GetResizedImagesLastModifiedTs()):
            sizeSettingChanges += 1
        if self.lastProcessTsByLevel[3] == 0 or (self.lastProcessTsByLevel[2] > self.lastProcessTsByLevel[3]) or (self.gif.GetResizedImagesLastModifiedTs() > self.gif.GetGifLastModifiedTs()) or len(self.gif.GetProcessedImageList()) == 0:
            gifSettingChanges += 1

        # Conflict. They changed form settings that will generate new stills, but they also made manual edits in explorer
        if self.lastProcessTsByLevel[1] > 0 and self.lastProcessTsByLevel[1] < self.gif.GetExtractedImagesLastModifiedTs() and timeOrRateSettingChanges:

            logging.info("Edits detected. Prompt user. TimestampLastProcess: %d ; TimestampImagesLastModified: %d", self.lastProcessTsByLevel[1], self.gif.GetExtractedImagesLastModifiedTs())

            if tkMessageBox.askyesno("I just noticed something!",
                                    "It looks like you imported frames, deleted frames, or made image edits in another program. " +
                                    "Making changes to animation smoothness, duration or start time will generate a new sequence of " +
                                    "images, overwriting your changes. Would you like to generate a new sequence of images based your updated settings?"):
                timeOrRateSettingChanges = 1
            else:
                timeOrRateSettingChanges = 0

        processOk     = True
        inputDisabled = False

        try:
            if processStages >= 1 and timeOrRateSettingChanges > 0:
                self.ResetFrameTrackbar()
                self.EnableInputs(False, False)
                inputDisabled = True
                self.SetStatus("(1/" + str(processStages) + ") Extracting frames...")
                self.gif.ExtractFrames()

                #
                # Dup detection and removal
                #

                frameCount = self.gif.GetNumFrames()
                deleteDupFrames = self.conf.GetParamBool('settings', 'autoDeleteDuplicateFrames')

                self.SetStatus("(1/" + str(processStages) + ") Checking for duplicate frames...")
                numDups = self.gif.CheckDuplicates(deleteDupFrames)

                if numDups > 0 and deleteDupFrames:
                    self.SetStatus("%d/%d were duplicates. Delete: %s" % (numDups, frameCount, str(deleteDupFrames)))

                if not self.gif.SourceIsVideo() and frameCount > 20 and frameCount-1 == numDups:
                    raise Exception("How boring! All of your frames are exactly the same! Note: If you're looking a black/blank image, try screen capturing on your other monitor - it's a known issue.")

                self.lastProcessTsByLevel[1] = time.time()

                doUpdateThumbs = True

            if processStages >= 2 and (timeOrRateSettingChanges or sizeSettingChanges):
                self.EnableInputs(False, False)
                inputDisabled = True

                if preview:
                    self.SetStatus("Generating Preview... First preview takes a few secs to generate. Subsequent previews will be quicker...")
                else:
                    self.SetStatus("(2/" + str(processStages) + ") Cropping and resizing...")
                
                if not preview:
                    self.gif.CropAndResize()
                    self.lastProcessTsByLevel[2] = time.time()

            imageProcessingRequired = (timeOrRateSettingChanges or sizeSettingChanges or gifSettingChanges)
            if processStages >= 3 and ((imageProcessingRequired or fileFormatSettingChanges) or preview):
                self.EnableInputs(False, False)
                inputDisabled = True

                if preview:
                    self.SetStatus("Generating preview")
                    self.gif.GenerateFramePreview(self.GetThumbNailIndex())
                else:
                    self.SetStatus("(3/" + str(processStages) + ") Applying effects and generating %s (%s)..." % (self.gif.GetFinalOutputFormat(), self.gif.GetNextOutputPath()))
                    self.gif.Generate(not imageProcessingRequired)
                    self.lastProcessTsByLevel[3] = time.time()
                
                self.SetStatus("Done")

        except Exception, e:
            self.guiBusy  = True
            errorMsg = str(e)
            logging.error(errorMsg)

            # Yuck. We get this if user kills the app with the X while the GUI is busy.
            # Intercept the nasty error message and avoid awkward app shutdown by forcing the app to close now
            if "invalid command name" in errorMsg:
                #self.parent.quit()
                raise SystemExit

            processOk = False

            processStageNames = ["Unknown", "frame extraction" , "cropping and resizing", "%s creation" % (self.gif.GetFinalOutputFormat()) ]

            self.Alert("A problem occurred during %s" % processStageNames[processStages], "%s" % errorMsg)

            #logging.error(traceback.format_exception(*sys.exc_info()))
            self.guiBusy  = False

        if processOk and processStages >= 3 and not preview:
            self.EnableInputs(False, False)
            inputDisabled = True

            # Check for Tumblr warnings
            if not self.gif.GifExists():
                 self.Alert("GIF not found!", "I Can't find the GIF %s" % (self.gif.GetLastGifOutputPath()))
            elif len(self.gif.GetProcessedImageList()) == 0:
                 self.Alert("Frames Not Found", "Processed %s frames not found" % (self.GetIntermediaryFrameFormat()))
            else:
                if self.gif.GetCompatibilityWarning() and self.gif.CompatibilityWarningsEnabled():
                    self.Alert("Wait! This won't display properly on some social media sites!!",  self.gif.GetCompatibilityWarning())

                self.SetStatus("GIF saved. GIF size: " + str(self.gif.GetSize()/1024) + "kB. Path: " + self.gif.GetLastGifOutputPath())

                self.PlayGif(self.gif.GetProcessedImageList(), self.gif.GetGifFrameDelay())

        if doUpdateThumbs:
            self.SetThumbNailIndex(1)
            self.UpdateThumbnailPreview()    

        if inputDisabled:
            self.EnableInputs(True, True)

        return processOk, errorMsg

    def ParseVideoPathInput(self, videoPath):
        if videoPath is None:
            return ""

        if type(videoPath) is list:
            fileList = list()    
            for f in videoPath:
                if len(f) > 0:
                    fileList.append(f)
            fileList.sort()
        else:
            fileList = videoPath.split("|")

        imgCount   = 0
        otherCount = 0
        for f in fileList:
            f = f.replace( u'/', os.sep )
            logging.info(u'Filename: "' + f + '"')
            if IsPictureFile(f):
                imgCount += 1
            else:
                otherCount += 1

        totalCount = imgCount + otherCount

        logging.info("Total file count %d (Images: %d; Other: %d)" % (totalCount, imgCount, otherCount))

        if totalCount == 0:
            return ""

        if (imgCount > 0 and otherCount > 0) or (otherCount > 1):
            self.Alert("Multiple Files", "You can only select multiple pictures. Only one video/GIF can be loaded at a time - e-mail us if you'd like us to add this feature.")
            return ""

        if imgCount > 1:
            returnStr = u"|".join(fileList)
        else:
            returnStr = fileList[0]

        return returnStr


    def OnShiftLoadVideo(self, event):
        self.OnLoadVideo(False, True)

    def OnLoadVideoEnterPressed(self, event):
        self.OnLoadVideo(True)

    def OnLoadVideo(self, enterPressed=False, multiSelect=False):
        multiSelectMode = multiSelect
        rc              = True
        errStr          = "Unknown error"
        urlPatterns     = re.compile('^(www\.|https://|http://)')
        capPattern      = re.compile('^::capture ([\.0-9]+) ([\.0-9]+) ([0-9]+)x([0-9]+)\+(\-?[0-9]+)\+(\-?[0-9]+) cursor=(\d) retina=(\d) web=(\d)$')
        fileName        = self.txtFname.get().strip()

        # Check same URL?
        if self.gif is not None and self.gif.IsSameVideo(fileName, self.downloadQuality.get()):
            logging.info("URL present in textfield. Show Open dialog")
            fileName = ""

        if fileName == "random":
            fileName = "http://www.petittube.com/" # random url
            self.txtFname.delete(0, END)

        if urlPatterns.match(fileName):
            self.SetStatus("Downloading video information. Please wait...")
            logging.info("Download " + fileName)
        elif capPattern.match(fileName):
            self.SetStatus("Capturing screen...")
        elif enterPressed:
            self.SetStatus("Loading manually-specified path...")
            logging.info("User entered " + fileName)

            fileName = self.ParseVideoPathInput(fileName)

            if len(fileName) == 0:
                return False

        else:
            fileNames = ()
            if ImAPC():
                fileNames = askopenfilename(multiple=multiSelectMode, filetypes=[("Media files", "*.*")], parent=self.parent, title="Find a video or images to GIF")
            else:
                fileNames = askopenfilename(multiple=multiSelectMode)

            try:
                logging.info("Open returned: " + str(fileNames) + " (%s)" % (type(fileNames)))
            except:
                logging.info("Failed to decode value returned by Open dialog")

            if fileNames is None:
                return False

            if type(fileNames) is not tuple:
                fileList = [fileNames]
            else:
                fileList = list(fileNames)

            fileName = self.ParseVideoPathInput(fileList)

            # Populate text field with user's choice
            if len(fileName):
                self.SetStatus("Loading video, please wait...")
                self.txtFname.delete(0, END)
                self.txtFname.insert(0, fileName)
            else:
                return False

        # Delete ::capture text from textbox
        if capPattern.match(fileName):
            self.txtFname.delete(0, END)

        # Load configuration defaults from file
        self.ReadConfig()
        self.SetLogoDefaults() # Needs to be persistent over their session

        self.EnableInputs(False, False)

        # Attempt to open the video for processing
        if len(fileName):
            try:
                self.gif = AnimatedGif(self.conf, fileName, self.tempDir, self.OnShowProgress, self.parent)

            except Exception, e:
                self.gif = None
                rc       = False
                errStr   = str(e)

                # If we're in debug mode, show a stack trace
                if not __release__:
                    tb      = traceback.format_exc()
                    errStr += "\n\n" + str(tb)

        # Allow inputs enabled on all inputs... so that we can load default values
        self.EnableInputs(True, True, True)
        self.ResetInputs()

        if rc:
            self.LoadDefaultEntryValues(videoLen=self.gif.GetVideoLengthSec())
            rc, estr = self.ProcessImage(1)
            errStr = estr

        # Turn off forceEnable
        self.EnableInputs(True, True, False)

        if rc:
            if self.gif.GetVideoLength() == None:
                self.SetStatus("Video loaded. Total runtime is unknown; " + str(self.gif.GetVideoFps()) + " fps")
                self.spnDuration.config(wrap=False)

            else:
                self.SetStatus("Video loaded. Total runtime: " + self.gif.GetVideoLength() + "; " + str(self.gif.GetVideoFps()) + " fps")

                # Set the trackbar properties
                trackbarTo  = 1
                durationMax = 1

                if self.gif.GetVideoLengthSec() > 1.0:
                    trackbarTo  = int(self.gif.GetVideoLengthSec())
                    durationMax = int(self.gif.GetVideoLengthSec())

                self.spnDuration.config(to=trackbarTo)
                self.spnDuration.config(wrap=True)
                self.sclStart.config(resolution=1, to=trackbarTo)

        else:
            self.gif = None
            self.txtFname.delete(0, END)
            self.EnableInputs(False, True)

            if "ordinal not in range" in errStr: # fix this particularly ugly error that keeps showing up
                self.Alert("Language Issue Detected", "Instagiffer is having trouble with your language. Please generate a bug report and send it to instagiffer@gmail.com. This issue is a top priority! Sorry for the inconvenience!")
                logging.error(errStr)
            else:
                self.Alert("A Problem Occurred", "Error: %s\n\nIf you think this is a bug, please generate a bug report and send it to instagiffer@gmail.com." % errStr)

            self.SetStatus("Failed to load video!")
            self.ResetInputs()

        return rc

    def CreateChildDialog(self, title, resizable=False, parent=None):
        if parent is None:
            parent = self.parent
        
        popupWindow = Toplevel(parent)
        popupWindow.withdraw()
        popupWindow.title(title)
        popupWindow.wm_iconbitmap('instagiffer.ico')
        #popupWindow.transient(self.mainFrame)         # 

        if not resizable:
            popupWindow.resizable(0,0)

        self.guiBusy = True
        return popupWindow

    def ReModalDialog(self, dlg):
        dlg.update()
        dlg.deiconify()
        dlg.lift()
        dlg.focus()
        dlg.grab_set()
        #self.guiBusy = True        

    def WaitForChildDialog(self, dlg, dlgGeometry=None):
        dlg.update()
        dlg.deiconify()
        dlg.lift()
        dlg.focus()

        # Get current geometry
        width  = dlg.winfo_width()
        height = dlg.winfo_height()
        x      = self.mainFrame.winfo_rootx()
        y      = self.mainFrame.winfo_rooty()
        geom   = '{0}x{1}+{2}+{3}'.format(width, height, x, y)


        if dlgGeometry == "center":
            self.CenterWindow(dlg)
            geom = dlg.geometry()


        # Restore geometry
        if dlgGeometry is not None and len(dlgGeometry) and dlgGeometry != "center":
            geom = dlgGeometry

        # Set window geometry
        dlg.geometry(geom)
        # Send mouse and key events to child window
        dlg.grab_set()

        # Block until window is destroyed
        self.parent.wait_window(dlg)

        self.guiBusy = False
        return True

    def PlayGif(self, filename, frameDelay):
        if not self.gif:
            self.Alert("Gif Player", "Internal error. Unable to play!")
            return

        popupWindow = self.CreateChildDialog("Instagiffer GIF Preview")
        
        isResizable = self.conf.GetParamBool('settings', 'resizablePlayer')

        if isResizable:
            popupWindow.resizable(width=TRUE, height=TRUE)
            popupWindow.columnconfigure(0, weight=1)
            popupWindow.rowconfigure(0, weight=1)
        else:
            popupWindow.resizable(width=FALSE, height=FALSE)

        try:
            # Should the audio be previewed
            soundPath = None
            if ImAPC() and self.isAudioEnabled.get() and self.HaveAudioPath() and self.gif.GetFinalOutputFormat() != 'gif':
                soundPath = self.gif.GetAudioClipPath()
    
            anim = GifPlayerWidget(popupWindow, filename, frameDelay * 10, isResizable, soundPath)
        except MemoryError:
            self.Alert("Gif Player", "Unable to show preview. Your GIF is too big.")
            return


        def OnDeletePlayer():
            try:
                anim.Stop()
            except:
                pass

            popupWindow.destroy()

        lbl = "Location: " + self.gif.GetLastGifOutputPath()
        if ImAMac() and self.isAudioEnabled and self.HaveAudioPath():
            lbl += " \n(Sound not available in this player)"

        # Build form componets
        lblInfo  = Label(popupWindow,  text=lbl)
        btnClose = Button(popupWindow, text='Close', padx=10, pady=10)

        # Place items on dialog
        anim.grid    (row=0, column=0, padx=5, pady=5, sticky=NSEW)
        lblInfo.grid (row=1, column=0, padx=5, pady=5, sticky=NSEW)
        btnClose.grid(row=2, column=0, padx=5, pady=5, sticky=NSEW)

        # Attach handlers
        popupWindow.protocol("WM_DELETE_WINDOW", OnDeletePlayer)
        btnClose.configure (command=OnDeletePlayer)

        return self.WaitForChildDialog(popupWindow)

    def OnCaptionSelect(self, *args):
        if not self.guiBusy:
            self.OnCaptionConfig()

    def GetFamilyList(self):
        return self.fonts.keys()

    def GetFontAttributeList(self, fontFamily):
        return self.fonts[fontFamily].keys()

    def GetFontId(self, fontFamily, fontStyle):
        return self.fonts[fontFamily][fontStyle]

    def OnScreenCapture(self):
        resizable    = True
        popupWindow  = self.CreateChildDialog("Screen Capture Configuration", resizable)

        # Set always-on-top and transparent
        popupWindow.wm_attributes('-alpha', 0.7)
        popupWindow.wm_attributes('-topmost', True)


        lblDuration     = Label(popupWindow, font=self.defaultFont, text="Length (s)")
        spnDuration     = Spinbox(popupWindow, font=self.defaultFont, from_=1, to=60, increment=0.5, width=4, textvariable=self.screenCapDurationSec)
        chkLowFps       = Checkbutton(popupWindow, font=self.defaultFont, text="Web-optimized", variable=self.screenCapLowerFps)
        chkRetina       = Checkbutton(popupWindow, font=self.defaultFont, text="Retina Display", variable=self.screenCapRetina)
        chkCursor       = Checkbutton(popupWindow, font=self.defaultFont, text="Show Cursor", variable=self.screenCapShowCursor)       
        lblResizeWindow = Label(popupWindow, text="",  background="#A2DEF2")
        btnStartCap     = Button(popupWindow, text='Start')

        # Place items on grid

        columns = 1
        btnStartCap.grid     (row=1, column=columns, padx=2, pady=5)
        columns += 1
        lblDuration.grid     (row=1, column=columns, padx=2, pady=2)
        columns += 1
        spnDuration.grid     (row=1, column=columns, padx=2, pady=2)
        columns += 1
        chkLowFps.grid       (row=1, column=columns, padx=2, pady=2)
        columns += 1

        if ImAMac():
            chkRetina.grid   (row=1, column=columns, padx=2, pady=2)
            columns += 1
        else:
            chkCursor.grid   (row=1, column=columns, padx=2, pady=2)
            columns += 1

        lblResizeWindow.grid (row=0, column=0, columnspan=columns + 1, padx=2, pady=5, sticky="NSEW")
        popupWindow.rowconfigure(0, weight=1)
        popupWindow.columnconfigure(0, weight=1)

        tooltips = {   
            spnDuration:  "Choose how long you wish to capture for. A reasonable value here is from 5-15 seconds.",
            chkRetina:    "Check this if your Mac has a retina display. If you don't check this, your capture region will not match what actually gets recorded.",
            chkLowFps:    "Select this option if you plan on posting the GIF online. A lower frame rate and smaller image size provides you some budget to increase image quality.",
            chkCursor:    "If you want the cursor to be visible as a small dot, select this option.",
            btnStartCap:  "Click here to start recording. If you CTRL-CLICK, a 5 second count-down will occur",
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)


        def GetCaptureDimensions():
            ww = popupWindow.winfo_width()
            wh = popupWindow.winfo_height()

            h = lblResizeWindow.winfo_height()
            w = lblResizeWindow.winfo_width()

            #print ww,wh,h,w

            if ww < w:
                w = ww - 2

                if w <= 0:
                    w = 1

            if wh < h:
                h = wh - 2
                if h <= 0:
                    h = 1

            return w, h, ww, wh

        def OnResize(event):
            w,h,ww,wh = GetCaptureDimensions()
            
            dimensionStr = "%dx%d" % (w,h)

            lblResizeWindow.config(text = dimensionStr)

        def OnMouseWheel(event, freezeX=False, freezeY=False):
            w, h, ww, wh = GetCaptureDimensions()

            modification = 0
            if event.delta < 0: # down
                modification = -10
            if event.delta > 0: # up
                modification = 10

            newW = ww
            newH = wh

            if not freezeX and w > 15:
                newW += modification
            if not freezeY and h > 15:
                newH += modification

            popupWindow.wm_geometry("%dx%d" % (newW, newH))

        def OnMouseWheelX(event):
            OnMouseWheel(event, freezeX=False, freezeY=True)

        def OnMouseWheelY(event):
            OnMouseWheel(event, freezeX=True, freezeY=False)      

        def StartMove(event):
            self._screencapXgbl = event.x
            self._screencapYgbl = event.y

        def StopMove(event):
            self._screencapXgbl = None
            self._screencapYgbl = None

        def OnMotion(event):
            deltax = event.x - self._screencapXgbl
            deltay = event.y - self._screencapYgbl
            x      = popupWindow.winfo_x() + deltax
            y      = popupWindow.winfo_y() + deltay
            popupWindow.geometry("+%s+%s" % (x, y))

        def OnCloseScreenCapDlg():
            # Save window position
            self.screenCapDlgGeometry = popupWindow.geometry()
            popupWindow.destroy()

        def OnStartClicked(doCountdown=False):
            fps = self.conf.GetParam('screencap', 'frameRateLimit')

            try:
                float(self.screenCapDurationSec.get())
            except ValueError:
                self.Alert("Invalid Duration", "The duration specified is invalid")
                return False

            if float(self.screenCapDurationSec.get()) < 1.0:
                self.Alert("Invalid Duration", "Duration must be at least 1 second")
                return False

            w, h, ww, wh = GetCaptureDimensions()
            x = lblResizeWindow.winfo_rootx()
            y = lblResizeWindow.winfo_rooty()

            self.txtFname.delete(0, END)
            self.txtFname.insert(0, "::capture %s %s %dx%d+%d+%d cursor=%d retina=%d web=%d" % (
                                    self.screenCapDurationSec.get(),
                                    fps,
                                    w,
                                    h,
                                    x,
                                    y,
                                    self.screenCapShowCursor.get(),
                                    self.screenCapRetina.get(),
                                    self.screenCapLowerFps.get()
                                ))

            OnCloseScreenCapDlg()

            # Show an on screen alert
            if doCountdown:
                captureWarning = Toplevel(self.parent)
                captureWarning.wm_attributes('-topmost', True)
                captureWarning.wm_attributes('-alpha', 0.5)
                captureWarning.wm_overrideredirect(1)
                lnlCaptureCountdown = Label(captureWarning, text="", justify=CENTER, background="white", relief=SOLID, borderwidth=3, font=("Arial", "25", "normal"))
                lnlCaptureCountdown.pack(expand=1, fill="both")
                captureWarning.wm_geometry("200x75+0+0") # % (w, h, x, y))

                countDownStr     = [ "Go!"]
                countDownTimeSec = [ 0.15]
                countDownValSecs = int(self.conf.GetParam('screencap', 'countDownSeconds'))

                for x in range(1, countDownValSecs + 1):
                    countDownStr.insert(0, "Capture in %d" % (x))
                    countDownTimeSec.insert(0,1)

                for i in range(0, len(countDownStr)):
                    self.SetStatus(countDownStr[i])
                    lnlCaptureCountdown.configure(text=countDownStr[i])
                    self.OnShowProgress(False)
                    time.sleep(countDownTimeSec[i])

                captureWarning.destroy()

            # Make progress bar move
            self.OnShowProgress(True)
            self.OnLoadVideo()

        def OnCtrlStartClicked(event):
            OnStartClicked(True)

        # Attach handlers
        popupWindow.protocol("WM_DELETE_WINDOW", OnCloseScreenCapDlg)
        btnStartCap.configure(command=OnStartClicked)
        btnStartCap.bind("<Control-Button-1>", OnCtrlStartClicked)

        lblResizeWindow.bind("<ButtonPress-1>",   StartMove)
        lblResizeWindow.bind("<ButtonRelease-1>", StopMove)
        lblResizeWindow.bind("<B1-Motion>",       OnMotion)
        popupWindow.bind("<Configure>",       OnResize)

        popupWindow.bind("<Control-MouseWheel>", OnMouseWheelX)
        popupWindow.bind("<Shift-MouseWheel>", OnMouseWheelY)
        popupWindow.bind("<MouseWheel>", OnMouseWheel)

        # Block until dialog closes
        self.WaitForChildDialog(popupWindow, self.screenCapDlgGeometry)


    def SetLogoDefaults(self):
        if len(self.OnSetLogoDefaults) > 0:
            self.miscGifChanges += self.conf.SetParamBool('imagelayer1', 'applyFx',     self.OnSetLogoDefaults["logoApplyFx"])
            self.miscGifChanges += self.conf.SetParam(    'imagelayer1', 'path',        self.OnSetLogoDefaults["logoPath"])
            self.miscGifChanges += self.conf.SetParam(    'imagelayer1', 'positioning', self.OnSetLogoDefaults["logoPositioning"])            
            self.miscGifChanges += self.conf.SetParam(    'imagelayer1', 'resize',      self.OnSetLogoDefaults["logoResize"])
            self.miscGifChanges += self.conf.SetParam(    'imagelayer1', 'opacity',     self.OnSetLogoDefaults["logoOpacity"])
            self.miscGifChanges += self.conf.SetParam(    'imagelayer1', 'xNudge',      self.OnSetLogoDefaults["logoXoffset"])
            self.miscGifChanges += self.conf.SetParam(    'imagelayer1', 'yNudge',      self.OnSetLogoDefaults["logoYoffset"])

    def OnSetLogo(self):
        # Default form values
        if len(self.OnSetLogoDefaults) == 0:
            self.OnSetLogoDefaults["logoApplyFx"]     = self.conf.GetParamBool('imagelayer1', 'applyFx')
            self.OnSetLogoDefaults["logoPath"]        = self.conf.GetParam(    'imagelayer1', 'path')
            self.OnSetLogoDefaults["logoPositioning"] = self.conf.GetParam(    'imagelayer1', 'positioning')
            self.OnSetLogoDefaults["logoResize"]      = self.conf.GetParam(    'imagelayer1', 'resize')
            self.OnSetLogoDefaults["logoOpacity"]     = self.conf.GetParam(    'imagelayer1', 'opacity')
            self.OnSetLogoDefaults["logoXoffset"]     = self.conf.GetParam(    'imagelayer1', 'xNudge')
            self.OnSetLogoDefaults["logoYoffset"]     = self.conf.GetParam(    'imagelayer1', 'yNudge')

        dlg  = self.CreateChildDialog("Configure Logo")

        if dlg is None:
            return False

        lblPath           = Label(dlg, font=self.defaultFont, text="Image path")
        txtPath           = Entry(dlg, font=self.defaultFont, width=40)
        btnChooseFile     = Button(dlg, text='Browse...', padx=4, pady=4, width=15, font=self.defaultFontTiny)
        lblPos            = Label(dlg, font=self.defaultFont, text="Positioning")
        positioning       = StringVar()
        cbxPosition       = ttk.Combobox(dlg, textvariable=positioning, state='readonly', width=15, values=('Top Left', 'Top', 'Top Right', 'Middle Left', 'Center', 'Middle Right', 'Bottom Left', 'Bottom', 'Bottom Right'))
        lblFilters        = Label(dlg, font=self.defaultFont, text="Apply Filters")
        applyFxToLogo     = IntVar()
        chkApplyFxToLogo  = Checkbutton(dlg, text="", variable=applyFxToLogo)

        lblResize         = Label(dlg, font=self.defaultFont, text="Size Percentage")
        resizePercent     = IntVar()
        spnResizePercent  = Spinbox(dlg, font=self.defaultFont, from_=1, to=100, increment=1, width=5, textvariable=resizePercent, repeatdelay=300, repeatinterval=30, state='readonly', wrap=True) 

        lblOpacity        = Label(dlg, font=self.defaultFont, text="Opacity")
        opacity           = IntVar()
        spnOpacityPercent = Spinbox(dlg, font=self.defaultFont, from_=1, to=100, increment=1, width=5, textvariable=opacity, repeatdelay=300, repeatinterval=30, state='readonly', wrap=True) 

        lblXOffset        = Label(dlg, font=self.defaultFont, text="X Offset")
        xoffset           = IntVar()
        spnX              = Spinbox(dlg, font=self.defaultFont, from_=-500, to=500, increment=1, width=5, textvariable=xoffset, repeatdelay=300, repeatinterval=30, state='readonly')

        lblYOffset        = Label(dlg, font=self.defaultFont, text="Y Offset")
        yoffset           = IntVar()
        spnY              = Spinbox(dlg, font=self.defaultFont, from_=-500, to=500, increment=1, width=5, textvariable=yoffset, repeatdelay=300, repeatinterval=30, state='readonly') 

        btnOk             = Button(dlg, text='OK', padx=4, pady=4)

        # Populate
        cbxPosition.set(self.OnSetLogoDefaults["logoPositioning"]) # Bottom
        txtPath.insert(0, self.OnSetLogoDefaults["logoPath"])
        applyFxToLogo.set(self.OnSetLogoDefaults["logoApplyFx"])
        resizePercent.set(self.OnSetLogoDefaults["logoResize"])
        opacity.set(self.OnSetLogoDefaults["logoOpacity"])
        xoffset.set(self.OnSetLogoDefaults["logoXoffset"])
        yoffset.set(self.OnSetLogoDefaults["logoYoffset"])


        # Place elements on grid
        rowIdx = -1

        rowIdx += 1
        lblPath.grid              (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        txtPath.grid              (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)
        btnChooseFile.grid        (row=rowIdx, column=2, sticky=EW, padx=4, pady=4)

        rowIdx += 1
        lblPos.grid               (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        cbxPosition.grid          (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        lblFilters.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        chkApplyFxToLogo.grid     (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        lblResize.grid            (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnResizePercent.grid     (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        lblOpacity.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnOpacityPercent.grid    (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        lblXOffset.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnX.grid                 (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        lblYOffset.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnY.grid                 (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        btnOk.grid                (row=rowIdx, column=0, sticky=EW, padx=4, pady=4, columnspan=3)

        tooltips = {   
            btnChooseFile:     "Choose a logo image in .gif format. Your logo can contain transparency.",
            cbxPosition:       "Select where you wish the logo to be positioned on your GIF",
            chkApplyFxToLogo:  "If unchecked, your logo will appear on top of all of the effects, unprocessed",
            spnResizePercent:  "Scale down your logo if it is too large.",
            spnOpacityPercent: "Control how transparent your logo is.",
            spnX:              "Shift logo this many pixels in the horizontal direction.",
            spnY:              "Shift logo this many pixels in the vertical direction."
        }

        # Populate 
        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        def OnChooseFileClicked():
            logoPath = askopenfilename(filetypes=[("Graphics Interchange Format", ("*.jpg", "*.gif", "*.bmp", "*.png") )])
            txtPath.delete(0, END)
            self.OnSetLogoDefaults["logoPath"] = ""
            if logoPath is not None:
                txtPath.insert(0, logoPath)
                self.OnSetLogoDefaults["logoPath"] = logoPath

            return True

        def OnOkClicked():
            # Update defaults
            self.OnSetLogoDefaults["logoPath"]        = txtPath.get()
            self.OnSetLogoDefaults["logoPositioning"] = positioning.get()
            self.OnSetLogoDefaults["logoApplyFx"]     = applyFxToLogo.get()
            self.OnSetLogoDefaults["logoResize"]      = resizePercent.get()
            self.OnSetLogoDefaults["logoOpacity"]     = opacity.get()
            self.OnSetLogoDefaults["logoXoffset"]     = xoffset.get()
            self.OnSetLogoDefaults["logoYoffset"]     = yoffset.get()
            self.SetLogoDefaults()
            dlg.destroy()

        btnChooseFile.configure (command=OnChooseFileClicked)
        btnOk.configure         (command=OnOkClicked)

        return self.WaitForChildDialog(dlg)



    def OnDeleteFrames(self):
        dlg  = self.CreateChildDialog("Delete Frames")

        if dlg is None:
            return False

        numFrames         = self.gif.GetNumFrames()
        lblStartFrame     = Label(dlg, font=self.defaultFont, text="Start Frame")
        sclStartFrame     = Scale(dlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)

        lblEndFrame       = Label(dlg, font=self.defaultFont, text="End Frame")
        sclEndFrame       = Scale(dlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)
        sclEndFrame.set(numFrames)

        deleteEvenOnly    = IntVar()
        lblDeleteEvenOnly = Label(dlg, font=self.defaultFont, text="Delete Even Frames Only")
        chkDeleteEvenOnly = Checkbutton(dlg, text="", variable=deleteEvenOnly)       

        btnDelete         = Button(dlg, text='Delete', padx=4, pady=4)

        lblStartFrame.grid       (row=0, column=0, sticky=W,  padx=4, pady=4)
        sclStartFrame.grid       (row=0, column=1, sticky=W,  padx=4, pady=4)
        lblEndFrame.grid         (row=1, column=0, sticky=W,  padx=4, pady=4)
        sclEndFrame.grid         (row=1, column=1, sticky=W,  padx=4, pady=4)
        lblDeleteEvenOnly.grid   (row=2, column=0, sticky=W,  padx=4, pady=4)
        chkDeleteEvenOnly.grid   (row=2, column=1, sticky=W,  padx=4, pady=4)        
        btnDelete.grid           (row=3, column=0, sticky=EW, padx=4, pady=4, columnspan=2)

        tooltips = {   
            sclStartFrame:     "Start deleting from this frame.",
            sclEndFrame:       "Delete up-to-and-including this frame",
            chkDeleteEvenOnly: "Delete even numbered frames only. This is handy if you want to thin out your frames to reduce framerate and overall GIF file size. You can perform this over-and-over again in order to keep reducing frame rate."
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        def OnDeleteClicked():
            start = int(sclStartFrame.get())
            end   = int(sclEndFrame.get())

            btnDelete.configure(state="disabled")

            if start == 1 and end == numFrames and deleteEvenOnly.get() == 0:
                tkMessageBox.showinfo("You're trying to delete every frame", "You can't delete every frame. Please re-adjust your start and end position")
                dlg.lift()
                return False

            self.DeleteFrame(start, end, deleteEvenOnly.get())
            dlg.destroy()
            return True

        def OnSetFramePosition(newIdx):
            self.SetThumbNailIndex(int(newIdx))
            self.UpdateThumbnailPreview()

            start = int(sclStartFrame.get())
            end   = int(sclEndFrame.get())

            if start > end:
                sclStartFrame.set(end)
            return True

        btnDelete.configure     (command=OnDeleteClicked)
        sclStartFrame.configure (command=OnSetFramePosition)
        sclEndFrame.configure   (command=OnSetFramePosition)

        return self.WaitForChildDialog(dlg)

    def OnExportFrames(self):
        dlg = self.CreateChildDialog("Export Frames")

        if dlg is None:
            return False

        lblPrefix      = Label(dlg, font=self.defaultFont, text="Prefix")
        txtPrefix      = Entry(dlg, font=self.defaultFont, width=10)

        rotationDegs         = StringVar()
        includeCropAndResize = IntVar()
        includeCropAndResize.set(0)
        lblCropResize = Label(dlg, font=self.defaultFont, text="Resize & Crop")
        chkCropResize = Checkbutton(dlg, text="", variable=includeCropAndResize)

        txtPrefix.delete(0, END)
        txtPrefix.insert(0, "img_")

        numFrames      = self.gif.GetNumFrames()
        lblStartFrame  = Label(dlg, font=self.defaultFont, text="Start Frame")
        sclStartFrame  = Scale(dlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)
        lblEndFrame    = Label(dlg, font=self.defaultFont, text="End Frame")
        sclEndFrame    = Scale(dlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)
        sclEndFrame.set(numFrames)
        lblRotation    = Label(dlg, font=self.defaultFont, text="Rotation")
        spnRotation    = Spinbox(dlg, font=self.defaultFont, from_=0, to=359, increment=1, width=5, textvariable=rotationDegs, repeatdelay=300, repeatinterval=60, wrap=True)

        btnExport      = Button(dlg, text='Select directory and export frames', padx=4, pady=4)

        rowNum = 0
        lblPrefix.grid         (row=rowNum, column=0, sticky=W,  padx=4, pady=4)
        txtPrefix.grid         (row=rowNum, column=1, sticky=W,  padx=4, pady=4)
        rowNum += 1
        lblRotation.grid       (row=rowNum, column=0, sticky=W,  padx=4, pady=4)
        spnRotation.grid       (row=rowNum, column=1, sticky=W,  padx=4, pady=4)
        rowNum +=1
        lblCropResize.grid     (row=rowNum, column=0, sticky=W,  padx=4, pady=4)
        chkCropResize.grid     (row=rowNum, column=1, sticky=W,  padx=4, pady=4, columnspan=2)
        rowNum +=1
        lblStartFrame.grid     (row=rowNum, column=0, sticky=W,  padx=4, pady=4)
        sclStartFrame.grid     (row=rowNum, column=1, sticky=W,  padx=4, pady=4)
        rowNum +=1
        lblEndFrame.grid       (row=rowNum, column=0, sticky=W,  padx=4, pady=4)
        sclEndFrame.grid       (row=rowNum, column=1, sticky=W,  padx=4, pady=4)
        rowNum +=1
        btnExport.grid         (row=rowNum, column=0, sticky=EW, padx=4, pady=4, columnspan=2)

        tooltips = {   
            txtPrefix:     "All exported frames will start with this pattern. A sequential number will be appended to the end.",
            chkCropResize: "Apply resize and crop settings to exported frames.",
            sclStartFrame: "Start exporting from this frame.",
            sclEndFrame:   "Export up-to-and-including this frame",
            spnRotation:   "Rotate frames by this many degrees. 0 means no rotation"
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)


        def OnSetFramePosition(newIdx):
            self.SetThumbNailIndex(int(newIdx))
            self.UpdateThumbnailPreview()

            start = int(sclStartFrame.get())
            end   = int(sclEndFrame.get())

            if start > end:
                sclStartFrame.set(end)

            return True

        def OnExportClicked():
            start     = int(sclStartFrame.get())
            end       = int(sclEndFrame.get())
            prefix    = txtPrefix.get()
            rotation  = int(rotationDegs.get())
            outputDir = askdirectory(parent=dlg, title="Choose directory for exported images", mustexist=True, initialdir='/')

            btnExport.configure(state="disabled")

            logging.info("Output folder: %s. Write access: %d" % (outputDir, os.access(outputDir, os.W_OK)))

            if outputDir == "":
                btnExport.configure(state="normal")
                return False

            if includeCropAndResize.get():
                # They want crop settings. Apply cropping and resizing before exporting
                self.ProcessImage(2)

            if self.gif.ExportFrames(start, end, prefix, includeCropAndResize.get(), rotation, outputDir):
                self.SetStatus("Frames %d to %d exported to %s" % (start, end, outputDir))
            else:
                # assume that this is the error.
                tkMessageBox.showinfo("Export Failed", "Failed to export frames!")
                btnExport.configure(state="normal")
                return False

            dlg.destroy()
            return True

        # Attach handlers
        btnExport.configure     (command=OnExportClicked)
        sclStartFrame.configure (command=OnSetFramePosition)
        sclEndFrame.configure   (command=OnSetFramePosition)

        return self.WaitForChildDialog(dlg)

    def OnImportFrames(self):
        dlg  = self.CreateChildDialog("Import Frames")

        buttonTitle = [ 'Browse for images to import', 'Insert blank frames' ]

        if dlg is None:
            return False

       # Forward declare
        sclStartFrame = None

        numFrames         = self.gif.GetNumFrames()
        lblStartFrame     = Label(dlg, font=self.defaultFont, text="Insert after Frame")
        sclStartFrame     = Scale(dlg, font=self.defaultFontTiny, from_=0, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)

        importReversed    = IntVar()
        lblImportReversed = Label(dlg, font=self.defaultFont, text="Reverse frames")
        chkImportReversed = Checkbutton(dlg, text="", variable=importReversed)

        riffleShuffle    = IntVar()
        lblRiffleShuffle = Label(dlg, font=self.defaultFont, text="Riffle shuffle")
        chkRiffleShuffle = Checkbutton(dlg, text="", variable=riffleShuffle)

        stretch          = IntVar()
        lblStretch       = Label(dlg, font=self.defaultFont, text="Stretch-to-Fit")
        chkStretch      = Checkbutton(dlg, text="", variable=stretch)

        blankFrame       = IntVar()
        lblBlankFrame    = Label(dlg, font=self.defaultFont, text="Insert Blank Frames")
        chkBlankFrame    = Checkbutton(dlg, text="", variable=blankFrame)

        numBlanks        = IntVar()
        spnBlanks        = Spinbox(dlg, font=self.defaultFont, from_=1, to=100, increment=1, width=5, textvariable=numBlanks, repeatdelay=300, repeatinterval=30, state='readonly') 
        numBlanks.set(1)

        btnImport        = Button(dlg, text=buttonTitle[blankFrame.get()], padx=4, pady=4)

        # Place elements on grid
        rowIdx = -1

        rowIdx += 1
        lblStartFrame.grid        (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        sclStartFrame.grid        (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)
        
        rowIdx += 1
        lblImportReversed.grid    (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        chkImportReversed.grid    (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1        
        lblRiffleShuffle.grid     (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        chkRiffleShuffle.grid     (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1        
        lblStretch.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        chkStretch.grid           (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1        
        lblBlankFrame.grid        (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        chkBlankFrame.grid        (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)
        spnBlanks.grid            (row=rowIdx, column=2, sticky=W,  padx=4, pady=4)

        rowIdx += 1
        btnImport.grid            (row=rowIdx, column=0, sticky=EW, padx=4, pady=4, columnspan=3)


        tooltips = {   
            sclStartFrame:     "Set the position in your GIF where you want the frames to be imported. Importing at frame 0 will import frames before the first frame.",
            chkImportReversed: "Import frames in reverse order. Handy for making bouncing loops (a->b->a). Also known as patrol loops, forward-reverse loops, boomerangs or symmetric loops.",
            chkRiffleShuffle:  "Interleave imported frames with existing frames.",
            chkStretch:        "Stretch to fit. Otherwise maintain aspect ratio. You may end up with black bars if your images don't have similar sizes.",
            chkBlankFrame:     "Import blank (black) frames.", 
            spnBlanks:         "Number of blank frames to insert.",
            btnImport:         "Once you click this button, a dialog will appear where you can multi-select files to be imported multiple files. Note: They will be resized to match your current GIF dimensions.",
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        #
        # Handlers
        #

        def OnSetFramePosition(newIdx):
            newIdx    = int(newIdx)
            numFrames = self.gif.GetNumFrames()

            if newIdx == 0:
                newIdx = 1
            elif newIdx > numFrames:
                newIdx = numFrames

            self.SetThumbNailIndex(newIdx)
            self.UpdateThumbnailPreview()
            return True


        def OnToggleBlankFrame(*args):
            btnImport.configure(text=buttonTitle[blankFrame.get()])



        def OnImportClicked():
            start         = int(sclStartFrame.get())
            
            if start == 0:
                insertAfter = False
                start       = 1
            else:
                insertAfter = True

            reverseImport = importReversed.get()
            riffle        = riffleShuffle.get()


            if blankFrame.get():
                imgList  = [ "<black>" ] * numBlanks.get()
            else:
                filesStr = askopenfilename(parent=dlg, title="Choose images to import", multiple=True, filetypes= [('Image Files', ("*.jpg", "*.gif", "*.bmp", "*.png"))])
                imgList  = list(self.parent.tk.splitlist(filesStr))

            self.SetStatus("Import %d images" % (len(imgList)))

            if len(imgList) <= 0:
                return False

            # Disable import button
            btnImport.configure(state="disabled")

            self.miscGifChanges += 1
            if self.gif.ImportFrames(start, imgList, reverseImport, insertAfter, riffle, stretch.get() == 0 ):
                self.SetStatus("Imported images starting at frame %d" % (start))

            self.UpdateThumbnailPreview() # We have new frames

            dlg.destroy()
            return True

        # Attach handlers
        btnImport.configure     (command=OnImportClicked)
        sclStartFrame.configure (command=OnSetFramePosition)
        blankFrame.trace        ("w", OnToggleBlankFrame)

        return self.WaitForChildDialog(dlg)



    # Manual Size and Crop
    def OnManualSizeAndCrop(self):
        dlg  = self.CreateChildDialog("Crop Settings")
        
        if dlg is None:
            return False

        try:
            sx, sy, sw, sh, smaxw, smaxh, sratio = self.GetCropSettingsFromCanvas(True)
        except:
            return False

        cropX        = StringVar()
        cropY        = StringVar()
        cropWidth    = StringVar()
        cropHeight   = StringVar()
        aspectLock   = IntVar()

        cropX.set(sx)
        cropY.set(sy)
        cropWidth.set(sw)
        cropHeight.set(sh)

        lblStartX     = Label(dlg, font=self.defaultFont, text="Horizontal Start Position")
        lblStartY     = Label(dlg, font=self.defaultFont, text="Vertical Start Position")
        lblAspectLock = Label(dlg, font=self.defaultFont, text="Maintain crop aspect ratio")
        lblWidth      = Label(dlg, font=self.defaultFont, text="GIF Width")
        lblHeight     = Label(dlg, font=self.defaultFont, text="GIF Height")
        lblAspectLock = Label(dlg, font=self.defaultFont, text="Maintain crop aspect ratio")

        spnX          = Spinbox(dlg, font=self.defaultFont, from_=0, to=smaxw-1, increment=1, width=5, textvariable=cropX,      repeatdelay=300, repeatinterval=14, state='readonly')
        spnY          = Spinbox(dlg, font=self.defaultFont, from_=0, to=smaxh-1, increment=1, width=5, textvariable=cropY,      repeatdelay=300, repeatinterval=14, state='readonly')
        spnWidth      = Spinbox(dlg, font=self.defaultFont, from_=1, to=smaxw,   increment=1, width=5, textvariable=cropWidth,  repeatdelay=300, repeatinterval=14, state='readonly')
        spnHeight     = Spinbox(dlg, font=self.defaultFont, from_=1, to=smaxh,   increment=1, width=5, textvariable=cropHeight, repeatdelay=300, repeatinterval=14, state='readonly')
        chkAspectLock = Checkbutton(dlg, text="", variable=aspectLock)
        btnOK         = Button(dlg, text='Done', padx=4, pady=4)

        # Place elements on grid

        rowIdx = -1

        # rowIdx += 1
        # lblAspectLock.grid  (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        # chkAspectLock.grid  (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)

        rowIdx += 1
        lblStartX.grid      (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnX.grid           (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)

        rowIdx += 1
        lblStartY.grid      (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnY.grid           (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        lblWidth.grid       (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnWidth.grid       (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)
        
        rowIdx += 1
        lblHeight.grid      (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnHeight.grid      (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)
        
        rowIdx += 1
        btnOK.grid          (row=rowIdx, column=0, sticky=EW, padx=4, pady=4, columnspan=2)

        tooltips = {
            chkAspectLock: "Maintain aspect ratio when adjusting width and height",
            spnWidth:      "Gif width in pixels",
            spnHeight:     "Gif height in pixels",
            spnX:          "Start coordinate X (horizontal)",
            spnY:          "Start coordinate Y (vertical)",
            btnOK:         "All done!",
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        #
        # Handlers
        #

        def OnOK():
            self.UpdateThumbnailPreview() # We have new frames
            dlg.destroy()
            return True

        def OnCropChange(*args):
            try:
                sx, sy, sw, sh, smaxw, smaxh, sratio = self.GetCropSettingsFromCanvas(True, False)
            except:
                logging.error("Failed to get cropper settings from canvas")
                return False

            # Video port coords
            (px, py, px2, py2) = self.canCropTool.coords('videoScale')

            # Boundary checks
            iw = float(cropWidth.get())
            ih = float(cropHeight.get())
            ix = float(cropX.get())
            iy = float(cropY.get())

            if iw < self.cropSizerSize:
                iw = self.cropSizerSize

            if ih < self.cropSizerSize:
                ih = self.cropSizerSize

            if ix + iw > smaxw:
                iw = smaxw - sx

            if iy + ih > smaxh:
                ih = smaxh - sy

            # Update GUI elements
            cropWidth.set(int(iw))
            cropHeight.set(int(ih))

            # Update cropper GUI

            # Translate coordinates to canvas port
            nx  = px + self.TranslateToCanvas(ix)
            ny  = py + self.TranslateToCanvas(iy)
            nx2 = px + self.TranslateToCanvas(ix + iw)
            ny2 = py + self.TranslateToCanvas(iy + ih)

            self.canCropTool.coords('cropRect', nx, ny, nx2, ny2)
            self.OnCropUpdate()

            return True


        # Attach handlers
        btnOK.configure  (command=OnOK)

        cropX.trace      ("w", OnCropChange)
        cropY.trace      ("w", OnCropChange)
        cropWidth.trace  ("w", OnCropChange)
        cropHeight.trace ("w", OnCropChange)
        aspectLock.trace ("w", OnCropChange)

        OnCropChange(None)
        return self.WaitForChildDialog(dlg)

    # Bouncing Loop
    def OnForwardReverseLoop(self):
        if self.gif is None or self.gif.GetNumFrames() <= 2:
            self.Alert("Unable to Make Loop", "You don't have enough frames to do this")
            return False

        self.gif.ReEnumerateExtractedFrames()
        if self.gif.ImportFrames(self.gif.GetNumFrames(), self.gif.GetExtractedImageList()[1:-1], True, True, False, False):
            self.SetStatus("Generated forward-reverse loop")
            self.UpdateThumbnailPreview() # We have new frames
        else:
            self.Alert("Unable to Make Loop", "Something weird happened. I couldn't loop this thing :(")

        return True


    def OnReverseFrames(self):
        if self.gif is None or self.gif.GetNumFrames() < 2:
            return False

        if self.gif.ReverseFrames():
            self.miscGifChanges += 1
            self.SetStatus("Reversed frames")
            self.UpdateThumbnailPreview() # We have new frames
            return True
        else:
            self.Alert("Unable to reverse frames", "Something weird happened. I couldn't reverse this thing :(")


    def OnCrossFade(self):
        if self.gif is None or self.gif.GetNumFrames() <= 2:
            return False

        dlg  = self.CreateChildDialog("Cross Fader")

        if dlg is None:
            return False

        numFrames      = self.gif.GetNumFrames()
        lblStartFrame  = Label(dlg, font=self.defaultFont, text="Start Frame")
        sclStartFrame  = Scale(dlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)
        lblEndFrame    = Label(dlg, font=self.defaultFont, text="End Frame")
        sclEndFrame    = Scale(dlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)
        sclEndFrame.set(numFrames)
        btnCreateFade  = Button(dlg, text='Generate Crossfade', padx=4, pady=4)

        lblStartFrame.grid       (row=0, column=0, sticky=W,  padx=4, pady=4)
        sclStartFrame.grid       (row=0, column=1, sticky=W,  padx=4, pady=4)
        lblEndFrame.grid         (row=1, column=0, sticky=W,  padx=4, pady=4)
        sclEndFrame.grid         (row=1, column=1, sticky=W,  padx=4, pady=4)
        btnCreateFade.grid       (row=2, column=0, sticky=EW, padx=4, pady=4, columnspan=2)

        tooltips = { 
            sclStartFrame:  "Frame to start crossfade. If greater than end frame, crossfade will loop around. To make cross fade effective, make sure you include an equal number of frames on either side of the transition point.",
            sclEndFrame:    "Frame to end crossfade",
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        def OnCreateFadeClicked():
            start = int(sclStartFrame.get())
            end   = int(sclEndFrame.get())

            btnCreateFade.configure(state="disabled")

            if not self.gif.CreateCrossFade(start, end):
                self.Alert("Cross-fade Error", "Make sure your range spans at least 3 frames")
                btnCreateFade.configure(state="normal")
                return False

            self.SetStatus("Added crossfade")
            self.UpdateThumbnailPreview() # We have new frames

            dlg.destroy()
            return True

        def OnSetFramePosition(newIdx):
            self.SetThumbNailIndex(int(newIdx))
            self.UpdateThumbnailPreview()
            start = int(sclStartFrame.get())
            end   = int(sclEndFrame.get())
            return True

        btnCreateFade.configure (command=OnCreateFadeClicked)
        sclStartFrame.configure (command=OnSetFramePosition)
        sclEndFrame.configure   (command=OnSetFramePosition)

        return self.WaitForChildDialog(dlg)


    #
    def OnEditAudioSettings(self, parentDlg):
        if self.gif is None:
            return False 

        dlg  = self.CreateChildDialog("Configure Audio", parent=parentDlg)

        if dlg is None:
            return False

        audioChanged          = True
        lblPath               = Label(dlg, font=self.defaultFont, text="Audio path")
        txtPath               = Entry(dlg, font=self.defaultFont, width=33)
        btnChooseFile         = Button(dlg, text='Load Audio', padx=4, pady=4, width=12, font=self.defaultFontTiny)

        lblStart              = Label(dlg, font=self.defaultFont, text="Start time")
 
        timeValues = [ "%02d" % (x) for x in range(0, 60)]
        timeValues = " ".join(timeValues)

        audioStartTimeMin   = StringVar()
        audioStartTimeSec   = StringVar()
        audioStartTimeMilli = StringVar()

        spnAudioStartTimeMin   = Spinbox(dlg, font=self.defaultFont, from_=0, to=59, values=timeValues,            increment=1, width=self.guiConf['timeSpinboxWidth'], textvariable=audioStartTimeMin,   validate=ALL, wrap=True, name="audioStartMin",   repeatdelay=250, repeatinterval=35, state='readonly')
        lblAudioMinSep         = Label(dlg,  text=":")
        spnAudioStartTimeSec   = Spinbox(dlg, font=self.defaultFont, from_=0, to=59, values=timeValues,            increment=1, width=self.guiConf['timeSpinboxWidth'], textvariable=audioStartTimeSec,   validate=ALL, wrap=True, name="audioStartSec",   repeatdelay=250, repeatinterval=35, state='readonly')
        lblAudioSecSep         = Label(dlg,  text=".")
        spnAudioStartTimeMilli = Spinbox(dlg, font=self.defaultFont, from_=0, to=9,  values="0 1 2 3 4 5 6 7 8 9", increment=1, width=self.guiConf['timeSpinboxWidth'], textvariable=audioStartTimeMilli, validate=ALL, wrap=True, name="audioStartMilli", repeatdelay=200, repeatinterval=100, state='readonly')

        lblVolume             = Label(dlg, font=self.defaultFont, text="Volume %")
        volume                = IntVar()
        spnVolume             = Spinbox(dlg, font=self.defaultFont, from_=0, to=300, increment=1, width=5, textvariable=volume, repeatdelay=300, repeatinterval=15, state='readonly') 

        btnPreview             = Button(dlg, text='Play', padx=4, pady=4, width=12, font=self.defaultFontTiny)
        btnOk                  = Button(dlg, text='OK', padx=4, pady=4)

        # # Load default values
        txtPath.insert(0, self.conf.GetParam('audio', 'path'))
        secs = float(self.conf.GetParam('audio', 'startTime'))        
        h, m, s, ms = MillisecToDurationComponents(secs * 1000.0)
        audioStartTimeMin.set("%02d" % m)
        audioStartTimeSec.set("%02d" % s)
        audioStartTimeMilli.set(ms/100)
        volume.set(int(self.conf.GetParam('audio', 'volume')))

        btnPreview.configure(state="disabled")

        # Place elements on grid
        rowIdx = -1

        rowIdx += 1
        lblPath.grid                (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        txtPath.grid                (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=5)
        btnChooseFile.grid          (row=rowIdx, column=6, sticky=EW, padx=4, pady=4)

        rowIdx += 1
        lblStart.grid               (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)

        spnAudioStartTimeMin.grid   (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)
        lblAudioMinSep.grid         (row=rowIdx, column=2, sticky=W,  padx=4, pady=4)
        spnAudioStartTimeSec.grid   (row=rowIdx, column=3, sticky=W,  padx=4, pady=4)
        lblAudioSecSep.grid         (row=rowIdx, column=4, sticky=W,  padx=4, pady=4)
        spnAudioStartTimeMilli.grid (row=rowIdx, column=5, sticky=W,  padx=4, pady=4)
        btnPreview.grid             (row=rowIdx, column=6, sticky=EW, padx=4, pady=4)

        rowIdx += 1
        lblVolume.grid               (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnVolume.grid               (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=2)

        rowIdx += 1
        btnOk.grid                  (row=rowIdx, column=0, sticky=EW, padx=4, pady=4, columnspan=7)

        tooltips = {   
            btnChooseFile:  "Click to start download of a URL, or to browse for a local file",
            txtPath:        "Hint: video URLs are supported in addition to local files",
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        def OnTimeChanged():
            audioChanged = True
            return True

        def OnChooseFileClicked():
            audioChanged = True

            if IsUrl(txtPath.get()):
                try:
                    downloadedFileName = self.gif.DownloadAudio(txtPath.get())
                except:
                    self.Alert("Audio Download", "Failed to download audio file")
                    return False

                txtPath.delete(0, "end")
                txtPath.insert(0, downloadedFileName)
            else:
                # They're selecting a file
                audioPath = askopenfilename(parent=dlg, filetypes=[("Audio file", ("*.mp3", "*.aac", "*.wav", "*.ogg", "*.m4a") )])
                txtPath.delete(0, END)
                if audioPath is not None:
                    txtPath.insert(0, audioPath)
                PrepareAudio()

            return True

        def AudioFileExists():
            return os.path.exists(txtPath.get())    

        def GetStartTime():
            timeStart = float(spnAudioStartTimeMin.get())*60 + float(spnAudioStartTimeSec.get()) + float(spnAudioStartTimeMilli.get())/10.0
            return timeStart

        def PrepareAudio():
            if len(txtPath.get()) == 0:
                return False

            if AudioFileExists():
                self.audioChanges += self.conf.SetParam('audio', 'path',      txtPath.get())
                self.audioChanges += self.conf.SetParam('audio', 'startTime', str(GetStartTime())) 
                self.audioChanges += self.conf.SetParam('audio', 'volume',    str(volume.get())) 

                audioChanged = False
                btnPreview.configure(state="normal")
                return True
            else:
                self.Alert("Audio", "Can't find the audio file")
                return False

        def OnPlay():
            if audioChanged:
                if not PrepareAudio() or not self.gif.ExtractAudioClip():
                    self.Alert("Audio", "Failed to extract clip from audio file")
                    return False

            AudioPlay(self.gif.GetAudioClipPath())
            self.parent.update_idletasks()

        def OnOkClicked():
            closeDialog = False

            if len(txtPath.get()) == 0:
                closeDialog = True
            elif PrepareAudio():
                # Do it automatically
                if self.gif.GetFinalOutputFormat() == 'gif':
                    self.ChangeFileFormat("mp4")

                closeDialog = True
            else:
                self.Alert('Audio Problems', "Something is wrong with your audio settings")

            # Should we close the audio dialog?
            if closeDialog:
                AudioPlay(None)
                dlg.destroy()

        btnChooseFile.configure          (command=OnChooseFileClicked)
        btnOk.configure                  (command=OnOkClicked)
        btnPreview.configure             (command=OnPlay)
        spnAudioStartTimeMin.configure   (command=OnTimeChanged)
        spnAudioStartTimeSec.configure   (command=OnTimeChanged)
        spnAudioStartTimeMilli.configure (command=OnTimeChanged)

        PrepareAudio()
        return self.WaitForChildDialog(dlg)

    # Edit mask
    def OnEditMask(self, parentDlg):
        if self.gif is None:
            return False

        dlg  = self.CreateChildDialog("Edit Mask", parent=parentDlg)
        
        if dlg is None:
            return False

        maxX = self.parent.winfo_screenwidth()  - 100
        maxY = self.parent.winfo_screenheight() - 250

        scaleFactor = 1.0

        if maxX < self.gif.GetVideoWidth() or maxY < self.gif.GetVideoHeight():
            scaleFactor = min( 
                        float(maxX)/float(self.gif.GetVideoWidth()),
                        float(maxY)/float(self.gif.GetVideoHeight())
                        )


        brushSize    = IntVar()
        maxSize      = max(self.gif.GetVideoWidth(), self.gif.GetVideoHeight())
        defBrushSize = ReScale(maxSize, (1, 1920),   (1, 100))
        blurRadius   = ReScale(maxSize, (200, 1920), (3, 15))
        brushSize.set(defBrushSize)

        # Create elements
        canvasContainer = LabelFrame(dlg, text=" Paint the area you want to unfreeze ")
        paintCanvas     = Canvas(canvasContainer, width=int(self.gif.GetVideoWidth() * scaleFactor), height=int(self.gif.GetVideoHeight() * scaleFactor),  background="black", borderwidth=0, highlightthickness=0)
        btnOK           = Button(dlg, text='Done',  padx=4, pady=4)
        btnReset        = Button(dlg, text='Reset', width=5, padx=4, pady=4)
        btnUndo         = Button(dlg, text='Undo',  width=5, padx=4, pady=4)


        lblBrushSize    = Label(dlg, text="Brush Size")
        spnBrushSize    = Spinbox(dlg, font=self.defaultFont, from_=1, to=100, increment=1, width=5, textvariable=brushSize, repeatdelay=300, repeatinterval=30, state='readonly')
        img             = PIL.Image.open(self.gif.GetExtractedImageList()[self.GetThumbNailIndex()-1])
        img             = img.resize((int(self.gif.GetVideoWidth() * scaleFactor), int(self.gif.GetVideoHeight() * scaleFactor) ), PIL.Image.ANTIALIAS)

        photoImg        = PIL.ImageTk.PhotoImage(img)

        # Place elements on grid
        rowIdx = -1

        rowIdx += 1
        lblBrushSize.grid       (row=rowIdx, column=0, sticky=W, padx=4, pady=4)
        spnBrushSize.grid       (row=rowIdx, column=1, sticky=W, padx=4, pady=4)
        btnUndo.grid            (row=rowIdx, column=2, sticky=EW, padx=4, pady=4)
        btnReset.grid           (row=rowIdx, column=3, sticky=EW, padx=4, pady=4)

        rowIdx += 1
        canvasContainer.grid    (row=rowIdx, column=0, columnspan=4, sticky=W, padx=4, pady=4)
        paintCanvas.grid        (row=0, column=0, sticky=W, padx=4, pady=4)

        rowIdx += 1
        btnOK.grid              (row=rowIdx, column=0, columnspan=4, sticky=EW, padx=4, pady=4)

        tooltips = {
            btnOK:         "All done!",
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)


        def DoDraw(x, y, brushSize, toCanvas=True):
            if toCanvas:
                brushColor = "red"
                halfpb = brushSize / 2
                x1, y1 = ( x - halfpb ), ( y - halfpb )
                x2, y2 = ( x + halfpb ), ( y + halfpb )
                paintCanvas.create_oval( x1, y1, x2, y2, fill=brushColor, outline=brushColor, tag="paint" )
            else:
                # Scale everything 
                invScaleFactor = 1.0/scaleFactor
                x         *= invScaleFactor
                y         *= invScaleFactor
                brushSize *= invScaleFactor

                halfpb = brushSize / 2
                x1, y1 = ( x - halfpb ), ( y - halfpb )
                x2, y2 = ( x + halfpb ), ( y + halfpb )
                self.maskDraw.ellipse( (x1, y1, x2, y2), outline='#000000', fill='#000000')

        def WriteToCanvas():
            if self.maskEventList is None:
                self.maskEventList = list()
            else:
                for e in self.maskEventList:
                    DoDraw(e[0], e[1], e[2], True)

        #
        # Handlers
        #

        def OnUndo():
            paintCanvas.delete('paint')

            deleteChunk = 20

            if len(self.maskEventList) <= deleteChunk:
                self.maskEventList = []
            elif len(self.maskEventList) > deleteChunk:
                for x in range(0, deleteChunk):
                    del self.maskEventList[-1]

            WriteToCanvas()

        def OnPaint( event ):
            paintBrushSize = brushSize.get() * 2
            saveEvent       = [event.x, event.y, brushSize.get()]
            self.maskEdited = True # To let GUI know
            self.maskEventList.append(saveEvent)
            DoDraw(saveEvent[0], saveEvent[1], saveEvent[2], True)

        def OnReset(onDialogLoad=False):
            if not onDialogLoad:
                self.maskEventList = []
                self.maskEdited    = True 

            paintCanvas.delete('paint')
            paintCanvas.create_image(0, 0, image=photoImg, tag="frame", anchor=NW)

            return True

        def OnOK():
            if self.HaveMask():
                self.maskImage  = PIL.Image.new("RGB", (self.gif.GetVideoWidth(), self.gif.GetVideoHeight()), '#ffffff')
                self.maskDraw   = PIL.ImageDraw.Draw(self.maskImage)

                for e in self.maskEventList:
                    DoDraw(e[0], e[1], e[2], False)

                self.maskImage  = self.maskImage.filter(ImageFilter.GaussianBlur(blurRadius))
                self.maskImage.save(self.gif.GetMaskFileName(0))
            else:
                try:
                    os.remove(self.gif.GetMaskFileName(0))
                except:
                    pass

            dlg.destroy()
            return True


        # Attach handlers
        dlg.protocol       ("WM_DELETE_WINDOW", OnOK)
        btnOK.configure    (command=OnOK)
        btnReset.configure (command=OnReset)
        btnUndo.configure  (command=OnUndo)
        paintCanvas.bind   ("<B1-Motion>", OnPaint)
        paintCanvas.bind   ("<Button-1>", OnPaint)

        OnReset(True)
        WriteToCanvas()

        return self.WaitForChildDialog(dlg, "center")


    #
    #
    # Effects Configuration
    #
    #
    def OnEffectsChange(self, *args):

        # Add new fx to this list
        allFx = [self.isGrayScale, self.isSharpened, self.isDesaturated, self.isSepia, self.isColorTint, self.isFadedEdges,
                 self.desaturatedAmount, self.sepiaAmount, self.sharpenedAmount, self.fadedEdgeAmount, self.colorTintAmount,
                 self.colorTintColor, self.isBordered, self.borderAmount, self.borderColor, self.nashvilleAmount, self.isNashville,
                 self.isBlurred, self.blurredAmount, self.isCinemagraph, self.invertCinemagraph, self.isAudioEnabled ]

        newFxHash = ""
        for param in allFx:
            newFxHash += str(param.get())
            # if args[0] == str(param):
            #     logging.info("Effect Change. New value: " + str(param.get()) )

        if not self.guiBusy and (newFxHash != self.fxHash or self.maskEdited):
            self.fxHash = newFxHash

            if self.conf.GetParamBool('settings', 'autoPreview'):
                self.OnShowPreview(None)
                self.parent.update_idletasks()


    def HaveMask(self):
        if self.maskEventList is None or len(self.maskEventList) == 0:
            return False
        else:
            return True


    def HaveAudioPath(self):
        audiofile = self.conf.GetParam('audio', 'path')
        return len(audiofile) and os.path.exists(audiofile)


    def OnEditEffects(self):
        self.fxHash = ""

        dlg  = self.CreateChildDialog("Filters")
        
        if dlg is None:
            return False

        lblHeadingCol1 = Label(dlg, text="Name")
        lblHeadingCol2 = Label(dlg, text="Value")
        lblHeadingCol3 = Label(dlg, text="Customize")


        if self.HaveMask():
            cinemagraphState = 'normal'
        else:
            cinemagraphState = 'disabled'

        if self.HaveAudioPath():
            audioState = 'normal'
        else:
            audioState = 'disabled'


        chkGrayScale        = Checkbutton(dlg, text="Black & White", variable=self.isGrayScale)
        chkSharpen          = Checkbutton(dlg, text="Enhance",       variable=self.isSharpened)
        chkDesaturate       = Checkbutton(dlg, text="Color Fade",    variable=self.isDesaturated)
        chkSepia            = Checkbutton(dlg, text="Sepia Tone",    variable=self.isSepia)
        chkColorTint        = Checkbutton(dlg, text="Colorize",      variable=self.isColorTint)
        chkEdgeFade         = Checkbutton(dlg, text="Burnt Corners", variable=self.isFadedEdges)
        chkBorder           = Checkbutton(dlg, text="Border",        variable=self.isBordered)
        chkBlurred          = Checkbutton(dlg, text="Blur",          variable=self.isBlurred)
        chkNashville        = Checkbutton(dlg, text="Nashville",     variable=self.isNashville)
        chkCinemagraph      = Checkbutton(dlg, text="Cinemagraph",   variable=self.isCinemagraph, state=cinemagraphState)
        chkCinemaInvert     = Checkbutton(dlg, text="Invert",        variable=self.invertCinemagraph, state=cinemagraphState)
        chkSound            = Checkbutton(dlg, text="Sound",         variable=self.isAudioEnabled, state=audioState)

        btnEditSound        = Button(dlg,  font=self.defaultFont, text="Configure...")
        btnEditMask         = Button(dlg,  font=self.defaultFont, text="Configure...")

        btnOK               = Button     (dlg, text='Done')

        btnTintColor        = Button(dlg,  font=self.defaultFont, text="Color Picker")
        btnBorderColor      = Button(dlg,  font=self.defaultFont, text="Color Picker")

        def OnSpin():
            # prevent events from queuing up
            dlg.update_idletasks()

        repeatRateMs = 1500
        spnDesaturateAmount = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.desaturatedAmount, state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        spnSepiaAmount      = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.sepiaAmount,       state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        spnSharpenAmount    = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.sharpenedAmount,   state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        spnFadedEdgeAmount  = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.fadedEdgeAmount,   state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        spnColorTintAmount  = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.colorTintAmount,   state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        spnBorderAmount     = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.borderAmount,      state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        spnNashvilleAmount  = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.nashvilleAmount,   state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        spnBlurAmount       = Spinbox(dlg, font=self.defaultFont, from_=0, to=100, increment=10, width=5, textvariable=self.blurredAmount,     state='readonly', wrap=True, repeatdelay=300, repeatinterval=repeatRateMs, command=OnSpin)
        rowIdx = -1


        rowIdx += 1
        lblHeadingCol1.grid       (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        lblHeadingCol2.grid       (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)
        lblHeadingCol3.grid       (row=rowIdx, column=2, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkSharpen.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnSharpenAmount.grid     (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkDesaturate.grid        (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnDesaturateAmount.grid  (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkSepia.grid             (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnSepiaAmount.grid       (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkEdgeFade.grid          (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnFadedEdgeAmount.grid   (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkNashville.grid         (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnNashvilleAmount.grid   (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkColorTint.grid         (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnColorTintAmount.grid   (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)
        btnTintColor.grid         (row=rowIdx, column=2, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkBlurred.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnBlurAmount.grid        (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkBorder.grid            (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        spnBorderAmount.grid      (row=rowIdx, column=1, sticky=W,  padx=4, pady=1)
        btnBorderColor.grid       (row=rowIdx, column=2, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkGrayScale.grid         (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkCinemagraph.grid       (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        btnEditMask.grid          (row=rowIdx, column=2, sticky=W,  padx=4, pady=1)
        chkCinemaInvert.grid      (row=rowIdx, column=3, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        chkSound.grid             (row=rowIdx, column=0, sticky=W,  padx=4, pady=1)
        btnEditSound.grid         (row=rowIdx, column=2, sticky=W,  padx=4, pady=1)

        rowIdx += 1
        btnOK.grid                (row=rowIdx, column=0, sticky=EW, padx=4, pady=4, columnspan=4)

        tooltips = {
            chkGrayScale:      "More specifically grayscale. Converting your GIF to grayscale will reduce file size. This is the last filter applied in the chain.",
            chkSharpen:        "Sharpen edges. If left unchecked, GIFs will have a slightly washed out look, which is sometimes desirable.",
            chkDesaturate:     "Tumblr will sometimes reject GIFs that are too rich in color. Use this to make your GIF less colorful.",
            chkSepia:          "Sepia tone. Make your GIF look like an early 1900's photo. It's the bee's knees!",
            chkColorTint:      "Add a color tint to your GIF",
            chkEdgeFade:       "Make the edges of your GIF look burnt.",
            chkBorder:         "Add a simple colored border.",
            chkNashville:      "Gives an iconic, nostalgic look to your GIF",
            chkBlurred:        "Blur effect",            
            chkCinemagraph:    "Freeze the entire GIF except for regions which you define. Requires a mask setting",
            chkCinemaInvert:   "Animate the regions that are NOT painted instead",
            btnEditMask:       "Edit the areas you wish to stay animated.",
            chkSound:          "Enable sound. Requires you to choose a format that supports sound such as mp4, webm or mov.",
            btnEditSound:      "Pick your audio track and start time."
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        def OnOK():
            self.OnStopPreview(None)
            dlg.destroy()
            return True

        def OnEditAudioClicked():
            hadAudio = self.HaveAudioPath()
            ret      = self.OnEditAudioSettings(dlg)

            self.ReModalDialog(dlg)

            if self.HaveAudioPath():
                if chkSound.cget('state') == 'disabled':
                    chkSound.configure(state="normal")
                    if hadAudio == False:
                        self.isAudioEnabled.set(1)
            else:
                chkSound.configure(state="disabled")

            self.OnEffectsChange(None)
            return ret


        def OnEditMaskClicked():
            hadMask = self.HaveMask()
            ret     = self.OnEditMask(dlg)

            self.ReModalDialog(dlg)
            
            if self.HaveMask():
                if chkCinemagraph.cget('state') == 'disabled':
                    chkCinemagraph.configure(state="normal")
                    chkCinemaInvert.configure(state="normal")
                    if hadMask == False:
                        self.isCinemagraph.set(1)
            else:
                chkCinemagraph.configure(state="disabled")
                chkCinemaInvert.configure(state="disabled")

            self.OnEffectsChange(None)
            return ret

        def OnSelectTintColor():
            (colorRgb, colorHex) = askcolor(parent=self.parent, initialcolor=self.colorTintColor.get(), title='Choose Tint Color')
            self.colorTintColor.set(colorHex)
            return True

        def OnSelectBorderColor():
            (colorRgb, colorHex) = askcolor(parent=self.parent, initialcolor=self.borderColor.get(), title='Choose Border Color')
            self.borderColor.set(colorHex)
            return True

        dlg.protocol("WM_DELETE_WINDOW", OnOK)
        btnOK.configure(command=OnOK)
        btnTintColor.configure(command=OnSelectTintColor)
        btnBorderColor.configure(command=OnSelectBorderColor)
        btnEditMask.configure(command=OnEditMaskClicked)     
        btnEditSound.configure(command=OnEditAudioClicked)

        if self.conf.GetParamBool('settings', 'autoPreview'):   
            self.OnShowPreview(None)

        return self.WaitForChildDialog(dlg)

    #
    #
    # Caption configuration dialog
    #
    #
    def OnCaptionConfig(self):
        if self.gif is None:
            return False

        positions = ('Top Left', 'Top', 'Top Right', 'Middle Left', 'Center', 'Middle Right', 'Bottom Left', 'Bottom', 'Bottom Right')
        fonts     = self.gif.GetFonts()
        isEdit    = False

        logging.info("Font count: %d" % (fonts.GetFontCount()))

        if fonts.GetFontCount() == 0:
            tkMessageBox.showinfo("Font Issue", "I wasn't able to find any fonts :(")
            return False

        # Default form values
        if len(self.OnCaptionConfigDefaults) == 0:
            recommendedFont = fonts.GetBestFontFamilyIdx(self.conf.GetParam('captiondefaults', 'captionFont'))

            try:
                positionIdx = positions.index(self.conf.GetParam('captiondefaults', 'position'))
            except:
                positionIdx = 7

            try:
                styleList = fonts.GetFontAttributeList(self.conf.GetParam('captiondefaults', 'captionFont'))
                styleIdx  = styleList.index(self.conf.GetParam('captiondefaults', 'fontStyle'))
            except:
                styleIdx = 0

            self.OnCaptionConfigDefaults["defaultFontSize"]             = self.conf.GetParam('captiondefaults', 'fontSize')
            self.OnCaptionConfigDefaults["defaultFontColor"]            = self.conf.GetParam('captiondefaults', 'fontColor')
            self.OnCaptionConfigDefaults["defaultFontOutlineColor"]     = self.conf.GetParam('captiondefaults', 'outlineColor')
            self.OnCaptionConfigDefaults["defaultFontIdx"]              = recommendedFont
            self.OnCaptionConfigDefaults["defaultFontStyleIdx"]         = styleIdx
            self.OnCaptionConfigDefaults["defaultPosition"]             = positionIdx
            self.OnCaptionConfigDefaults["defaultFontOutlineThickness"] = int(self.conf.GetParam('captiondefaults', 'outlineSize'))
            self.OnCaptionConfigDefaults["defaultOpacity"]              = int(self.conf.GetParam('captiondefaults', 'opacity'))
            self.OnCaptionConfigDefaults["defaultDropShadow"]           = int(self.conf.GetParamBool('captiondefaults', 'dropShadow'))
            self.OnCaptionConfigDefaults["defaultLineSpacing"]          = int(self.conf.GetParam('captiondefaults', 'interlineSpacing'))
            self.OnCaptionConfigDefaults["defaultApplyFxToText"]        = int(self.conf.GetParamBool('captiondefaults', 'applyFx'))

        if self.cbxCaptionList.current() == 0: # Entry zero is "Add new caption"
            captionIdx = len(self.cbxCaptionList["values"])
        else:
            captionIdx = self.cbxCaptionList.current()
            isEdit     = True

        # Create child dialog
        captionDlg = self.CreateChildDialog("Caption Configuration (%d)" % (captionIdx))
        if captionDlg is None:
            return False

        lblSample               = Label(captionDlg, text="Sample")
        lblFontPreview          = Label(captionDlg, text="AaBbYyZz")
        lblFontPreview['fg']    = self.OnCaptionConfigDefaults["defaultFontColor"]
        lblFontPreview['bg']    = '#000000'

        lblCaption              = Label(captionDlg, text="Caption")
        txtCaption              = Text(captionDlg,  font=self.defaultFont, width=45, height=3)
        txtCaption.focus()

        fontSize                = StringVar()
        fontSizeValues          = " ".join([ "%dpt" % (x) for x in range(9,72)])
        spnCaptionFontSize      = Spinbox(captionDlg, font=self.defaultFont, from_=9, to=72, increment=1, values=fontSizeValues, width=5, textvariable=fontSize, repeatdelay=300, repeatinterval=60) # font=self.defaultFont
        fontSize.set(self.OnCaptionConfigDefaults["defaultFontSize"])

        lblFont                 = Label(captionDlg, text="Font")
        fontFamily              = StringVar()
        cbxFontFamily           = ttk.Combobox(captionDlg, textvariable=fontFamily, state='readonly', width=20)

        cbxFontFamily['values'] = fonts.GetFamilyList()
        cbxFontFamily.current(self.OnCaptionConfigDefaults["defaultFontIdx"]) 

        fontStyle               = StringVar()
        lblStyle                = Label(captionDlg, font=self.defaultFont, text="Style")
        cbxStyle                = ttk.Combobox(captionDlg, textvariable=fontStyle, state='readonly', width=15, values=(fonts.GetFontAttributeList(fontFamily.get())))
        cbxStyle.current(self.OnCaptionConfigDefaults["defaultFontStyleIdx"])

        positioning             = StringVar()
        lblPosition             = Label(captionDlg, font=self.defaultFont, text="Positioning")
        cbxPosition             = ttk.Combobox(captionDlg, textvariable=positioning, state='readonly', width=15, values=positions)
        cbxPosition.current(self.OnCaptionConfigDefaults["defaultPosition"])    

        btnCaptionFontColor     = Button(captionDlg,  font=self.defaultFont, text="Color Picker")

        numFrames      = self.gif.GetNumFrames()
        lblStartFrame  = Label(captionDlg, font=self.defaultFont, text="Start Frame")
        sclStartFrame  = Scale(captionDlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)

        lblEndFrame    = Label(captionDlg, font=self.defaultFont, text="End Frame")
        sclEndFrame    = Scale(captionDlg, font=self.defaultFontTiny, from_=1, to=numFrames, resolution=1, tickinterval=0, orient=HORIZONTAL, sliderlength=20, width=15, length=275, showvalue=1)
        sclEndFrame.set(numFrames)
        
        animateSetting   = StringVar()
        animationType    = StringVar()
        lblAnimate       = Label(captionDlg, font=self.defaultFont, text="Animation")

        animValues = ['Off']

        for animType in ('FadeIn', 'FadeOut', 'FadeInOut', 'Triangle', 'Sawtooth', 'Square'):
            for animSpeed in ('Slow', 'Medium', 'Fast'):
                animValues.append( animType + ' ' + animSpeed)

        animValues.append("Random")

        cbxAnimate       = ttk.Combobox(captionDlg, textvariable=animateSetting, state='readonly', width=15, values=tuple(animValues))
        cbxAnimate.current(0)

        cbxAnimateType   = ttk.Combobox(captionDlg, textvariable=animationType, state='readonly', width=15, values=('Blink', 'Left-Right', 'Up-Down'))
        cbxAnimateType.current(0)

        lblOutline            = Label(captionDlg, font=self.defaultFont, text="Outline")
        lblOutlineSize        = Label(captionDlg, font=self.defaultFont, text="Size")

        outlineThickness      = IntVar()
        spnCaptionFontOutlineSize = Spinbox(captionDlg, font=self.defaultFont, from_=0, to=15, increment=1, width=5, textvariable=outlineThickness, repeatdelay=300, repeatinterval=60, state='readonly') 
        outlineThickness.set(self.OnCaptionConfigDefaults["defaultFontOutlineThickness"])

        dropShadow        = IntVar()
        chkdropShadow     = Checkbutton(captionDlg, text="Shadow", variable=dropShadow)
        dropShadow.set(self.OnCaptionConfigDefaults["defaultDropShadow"])

        lblFilters           = Label(captionDlg, font=self.defaultFont, text="Effects")
        applyFxToText        = IntVar()
        chkApplyFxToText     = Checkbutton(captionDlg, text="Apply Filters", variable=applyFxToText)
        applyFxToText.set(self.OnCaptionConfigDefaults["defaultApplyFxToText"])

        lblOpacity            = Label(captionDlg, font=self.defaultFont, text="Opacity")
        opacity               = IntVar()
        spnOpacity            = Spinbox(captionDlg, font=self.defaultFont, from_=0, to=100, increment=1, width=5, textvariable=opacity, repeatdelay=300, repeatinterval=30, state='readonly', wrap=True) 
        opacity.set(self.OnCaptionConfigDefaults["defaultOpacity"])

        lblLineSpacing        = Label(captionDlg, font=self.defaultFont, text="Line Space Adj.")
        lineSpacing           = IntVar()
        spnSpacing            = Spinbox(captionDlg, font=self.defaultFont, from_=-200, to=200, increment=1, width=5, textvariable=lineSpacing, repeatdelay=300, repeatinterval=30, state='readonly') 
        lineSpacing.set(self.OnCaptionConfigDefaults["defaultLineSpacing"])

        btnOk = Button(captionDlg, text='Done', padx=4, pady=4)

        # Place items on grid
        rowIdx = 0
        lblCaption.grid          (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        txtCaption.grid          (row=rowIdx, column=1, sticky=EW,  padx=4, pady=4, columnspan=3)

        rowIdx += 1
        lblFont.grid             (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        cbxFontFamily.grid       (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)        
        spnCaptionFontSize.grid  (row=rowIdx, column=2, sticky=W,  padx=4, pady=4)
        btnCaptionFontColor.grid (row=rowIdx, column=3, sticky=W,  padx=4, pady=4)
        
        rowIdx += 1
        lblSample.grid           (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        lblFontPreview.grid      (row=rowIdx, column=1, sticky=W,  padx=4, pady=4, columnspan=3)

        rowIdx += 1
        lblStyle.grid            (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        cbxStyle.grid            (row=rowIdx, column=1, sticky=EW,  padx=4, pady=4)

        rowIdx += 1
        lblPosition.grid         (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        cbxPosition.grid         (row=rowIdx, column=1, sticky=EW,  padx=4, pady=4)

        rowIdx += 1
        lblOutline.grid                (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        
        spnCaptionFontOutlineSize.grid (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)
        chkdropShadow.grid          (row=rowIdx, column=2, sticky=W,  padx=0, pady=4, columnspan=2)

        rowIdx += 1
        lblOpacity.grid          (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnOpacity.grid          (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)

        rowIdx += 1
        lblLineSpacing.grid      (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        spnSpacing.grid          (row=rowIdx, column=1, sticky=W,  padx=4, pady=4)

        rowIdx += 1
        lblFilters.grid          (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        chkApplyFxToText.grid    (row=rowIdx, column=1, sticky=W,  padx=0, pady=4, columnspan=1)

        rowIdx += 1  
        lblAnimate.grid          (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        cbxAnimateType.grid      (row=rowIdx, column=1, sticky=EW,  padx=4, pady=4)
        cbxAnimate.grid          (row=rowIdx, column=2, sticky=EW,  padx=4, pady=4, columnspan=2) 

        rowIdx += 1
        lblStartFrame.grid       (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        sclStartFrame.grid       (row=rowIdx, column=1, sticky=EW,  padx=4, pady=4, columnspan=3)
        rowIdx += 1
        lblEndFrame.grid         (row=rowIdx, column=0, sticky=W,  padx=4, pady=4)
        sclEndFrame.grid         (row=rowIdx, column=1, sticky=EW,  padx=4, pady=4, columnspan=3)

        rowIdx += 1
        btnOk.grid               (row=rowIdx, column=0, sticky=EW, padx=4, pady=4, columnspan=4)            

        tooltips = {   
            txtCaption:                "Type your text here.",
            cbxFontFamily:             "Font family. Try selecting this field, then scroll-wheeling over it with your mouse :)",
            spnCaptionFontSize:        "Font point size.",
            btnCaptionFontColor:       "Open up a color chooser to pick a color for your font.",
            cbxStyle:                  "Font parameters/styling",
            spnSpacing:                "Adjust the inter-line spacing. Only applies if your caption contains multiple lines. Can be negative or positive.",
            cbxAnimate:                "Pick your text animation style",
            cbxAnimateType:            "Pick your text animation effect",
            cbxPosition:               "Choose text placement on GIF.",
            spnCaptionFontOutlineSize: "Thickness of the black font outline.",
            sclStartFrame:             "Choose where in the GIF you want the text to start",
            sclEndFrame:               "Choose where you want the text to disappear",
            spnOpacity:                "Set the amount of transparency. Smaller values = more see-through",
            chkdropShadow:             "Add a shadow under the caption",
            chkApplyFxToText:          "Apply filters to text. Otherwise, text will be pasted on top of the filtered image.",
            btnOk:                     "Add this caption to the final GIF. Note: You can add up to 16 separate captions.",
        }

        for item, tipString in tooltips.iteritems():
            createToolTip(item, tipString)

        def OnFontUpdate(*args):
            # Did the font change?
            fontChanged = False
            if cbxFontFamily.current() != self.OnCaptionConfigDefaults["defaultFontIdx"]:
                fontChanged = True

            if fontChanged:
                cbxStyle["values"] = fonts.GetFontAttributeList(fontFamily.get())
                cbxStyle.current(0)

            previewFont = tkFont.Font(family=fontFamily.get(), size=14)

            if fontStyle.get().find("Italic") != -1:
                previewFont.configure(slant=tkFont.ITALIC)
            if fontStyle.get().find('Bold') != -1:
                previewFont.configure(weight=tkFont.BOLD)

            lblFontPreview.configure(font=previewFont)

            self.OnCaptionConfigDefaults["defaultFontSize"]     = fontSize.get()
            self.OnCaptionConfigDefaults["defaultFontColor"]    = lblFontPreview['fg']
            self.OnCaptionConfigDefaults["defaultFontIdx"]      = cbxFontFamily.current()
            self.OnCaptionConfigDefaults["defaultFontStyleIdx"] = cbxStyle.current()
            self.OnCaptionConfigDefaults["defaultPosition"]     = cbxPosition.current()
            self.OnCaptionConfigDefaults["defaultFontOutlineThickness"] = outlineThickness.get()
            self.OnCaptionConfigDefaults["defaultOpacity"]      = opacity.get()
            self.OnCaptionConfigDefaults["defaultDropShadow"]   = dropShadow.get()
            self.OnCaptionConfigDefaults["defaultLineSpacing"]  = lineSpacing.get()
            self.OnCaptionConfigDefaults["defaultApplyFxToText"]= applyFxToText.get()

            return True
        
        def OnSelectCaptionColor():
            (colorRgb, colorHex) = askcolor(parent=self.parent, initialcolor=lblFontPreview["fg"], title='Choose Caption Color')
            lblFontPreview.configure(fg=colorHex)
            OnFontUpdate(None)

        def OnSetFramePosition(newIdx):
            self.SetThumbNailIndex(int(newIdx))
            self.UpdateThumbnailPreview()

            start = int(sclStartFrame.get())
            end   = int(sclEndFrame.get())
            if start > end:
                sclStartFrame.set(end)
            return True

        def OnSaveCaption():
            caption = txtCaption.get(1.0, END)
            if len(caption.strip()) <= 0 and not isEdit:
                captionDlg.destroy()
                return False

            # Strip last new line
            if caption.endswith('\n'):
                caption = caption[:-1]

            # Check for unsupported unicode
            try:
                caption.encode(locale.getpreferredencoding())
            except UnicodeError, e:
                tkMessageBox.showinfo("Invalid Characters Detected", "Warning: Your caption contains invalid characters that don't exist in your locale's encoding (" + locale.getpreferredencoding() + "). Please remove unprintable characters before generating GIF.\n\n" + str(e))

            caption = caption.replace("\n",'[enter]')

            listValues = list(self.cbxCaptionList["values"])

            if len(caption) <= 0:
                self.captionChanges += self.conf.SetParam(confName, "text",              "")
                self.captionChanges += self.conf.SetParam(confName, "font",              "")
                self.captionChanges += self.conf.SetParam(confName, "style",             "")                
                self.captionChanges += self.conf.SetParam(confName, "size",              "")
                self.captionChanges += self.conf.SetParam(confName, "frameStart",        "")
                self.captionChanges += self.conf.SetParam(confName, "frameEnd",          "")
                self.captionChanges += self.conf.SetParam(confName, "color",             "")
                self.captionChanges += self.conf.SetParam(confName, "animationEnvelope", "")
                self.captionChanges += self.conf.SetParam(confName, "animationType",     "")
                self.captionChanges += self.conf.SetParam(confName, "positioning",       "")
                self.captionChanges += self.conf.SetParam(confName, "outlineColor",      "")
                self.captionChanges += self.conf.SetParam(confName, "outlineThickness",  "")
                self.captionChanges += self.conf.SetParam(confName, "opacity",           "")
                self.captionChanges += self.conf.SetParam(confName, "dropShadow",        "")
                self.captionChanges += self.conf.SetParam(confName, "applyFx",           "")
                self.captionChanges += self.conf.SetParam(confName, "interlineSpacing",  "")

                listValues[captionIdx] = '[deleted]'
            else:
                self.captionChanges += self.conf.SetParam(confName, "text",              caption)
                self.captionChanges += self.conf.SetParam(confName, "font",              fontFamily.get())
                self.captionChanges += self.conf.SetParam(confName, "style",             fontStyle.get())                
                self.captionChanges += self.conf.SetParam(confName, "size",              spnCaptionFontSize.get())
                self.captionChanges += self.conf.SetParam(confName, "frameStart",        sclStartFrame.get())
                self.captionChanges += self.conf.SetParam(confName, "frameEnd",          sclEndFrame.get())
                self.captionChanges += self.conf.SetParam(confName, "color",             lblFontPreview["fg"])
                self.captionChanges += self.conf.SetParam(confName, "animationEnvelope", animateSetting.get())
                self.captionChanges += self.conf.SetParam(confName, "animationType",     animationType.get())
                self.captionChanges += self.conf.SetParam(confName, "positioning",       positioning.get())
                self.captionChanges += self.conf.SetParam(confName, "outlineColor",      self.OnCaptionConfigDefaults["defaultFontOutlineColor"]) # Fixed for now
                self.captionChanges += self.conf.SetParam(confName, "outlineThickness",  outlineThickness.get())
                self.captionChanges += self.conf.SetParam(confName, "opacity",           opacity.get())
                self.captionChanges += self.conf.SetParam(confName, "dropShadow",        dropShadow.get())
                self.captionChanges += self.conf.SetParam(confName, "applyFx",           applyFxToText.get())
                self.captionChanges += self.conf.SetParam(confName, "interlineSpacing",  lineSpacing.get())

                if isEdit:
                    listValues[captionIdx] = caption
                else:
                    listValues.append(caption)

            # Convert list back to tuple.  Make sure that the last caption entered has focus
            self.cbxCaptionList["values"] = tuple(listValues)
            self.cbxCaptionList.current(captionIdx)

            captionDlg.destroy()

        #
        # Attach handlers
        #

        sclStartFrame.configure       (command=OnSetFramePosition)
        sclEndFrame.configure         (command=OnSetFramePosition)
        btnOk.configure               (command=OnSaveCaption)
        btnCaptionFontColor.configure (command=OnSelectCaptionColor)

        applyFxToText.trace     ("w", OnFontUpdate)
        dropShadow.trace        ("w", OnFontUpdate)
        outlineThickness.trace  ("w", OnFontUpdate)
        opacity.trace           ("w", OnFontUpdate)
        fontSize.trace          ("w", OnFontUpdate)
        fontFamily.trace        ("w", OnFontUpdate)
        fontStyle.trace         ("w", OnFontUpdate)
        positioning.trace       ("w", OnFontUpdate)
        animateSetting.trace    ("w", OnFontUpdate)
        animationType.trace     ("w", OnFontUpdate)
        lineSpacing.trace       ("w", OnFontUpdate)

        OnFontUpdate(None)

        # Initialize dialog with existing values
        confName = "caption" + str(captionIdx)
        if self.conf.GetParam(confName, "text") != "":
            txtCaption.insert(END,  self.conf.GetParam(confName, "text").replace("[enter]", "\n"))
            fontFamily.set(         self.conf.GetParam(confName, "font"))
            fontStyle.set(          self.conf.GetParam(confName, "style"))
            fontSize.set(           self.conf.GetParam(confName, "size"))
            sclStartFrame.set(      self.conf.GetParam(confName, "frameStart"))
            sclEndFrame.set(        self.conf.GetParam(confName, "frameEnd"))
            animateSetting.set(     self.conf.GetParam(confName, "animationEnvelope"))
            animationType.set(      self.conf.GetParam(confName, "animationType"))
            cbxPosition.set(        self.conf.GetParam(confName, "positioning"))
            captionColor =          self.conf.GetParam(confName, "color")
            outlineThickness.set(   self.conf.GetParam(confName, "outlineThickness"))
            opacity.set(            self.conf.GetParam(confName, "opacity"))
            dropShadow.set(         self.conf.GetParam(confName, "dropShadow"))
            applyFxToText.set(      self.conf.GetParam(confName, "applyFx"))
            lineSpacing.set(        self.conf.GetParam(confName, "interlineSpacing"))


            lblFontPreview.configure(fg=captionColor)

        self.parent.update_idletasks()

        return self.WaitForChildDialog(captionDlg)

#
# Little yellow tool tips shown on mouse-over
#

class ToolTip(object):

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"


        # Line wrap
        text = '\n'.join(line.strip() for line in re.findall(r'.{1,40}(?:\s+|$)', text))

        self.text = text
        if self.tipwindow or not self.text:
            return

        bboxVals = self.widget.bbox("insert")

        if bboxVals is None:
            logging.error("Failed to display tooltip: " + text)
            return False

        if len(bboxVals) == 4:
            x, y, cx, cy  =  bboxVals
        else:
            x, y, cx, cy  =  [int(n) for n in bboxVals.split()]

        # Set the X and Y offset
        x = x + self.widget.winfo_rootx() + 15
        y = y + cy + self.widget.winfo_rooty() + 50

        self.tipwindow = tw = Toplevel(self.widget)
        #tw.wm_attributes('-alpha', 0.6)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass

        #tw.withdraw()

        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def makevisable(self):
        self.tipwindow.deiconify()

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def createToolTip(widget, text):
    if len(text) <= 0:
        return

    toolTip = ToolTip(widget)
    def enter(event):
        toolTip.showtip(text)
        #toolTip.tipwindow.after(400, toolTip.makevisable())

    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)



# Any uncaught exceptions will end up here
lastErrorTimestamp = 0
def tkErrorCatcher(self, *args):
    global lastErrorTimestamp
    # Rate-limit the pop-up. If there's a constantly repeating bug, the never-ending popup becomes very annoying.
    if time.time() - lastErrorTimestamp > 10:
        showGuiMessage = True
        lastErrorTimestamp = time.time()
    else:
        showGuiMessage = False
    
    err = traceback.format_exception(*args)

    logging.error("Error trace:")

    for errLine in err:
        logging.error("%s" % (errLine))

        if "invalid command name" in errLine:
            showGuiMessage = False

    if showGuiMessage:
        openBugReport = tkMessageBox.askyesno("Oh crap, this is embarrasing!",
                                              "A problem occurred somewhere in the Instagiffer code. Please go to Help -> Generate Bug Report and send it to instagiffer@gmail.com and I'll fix it ASAP. Would you like to open the bug report now?",
                                              default="yes")

        if openBugReport:
            OpenFileWithDefaultApp(GetLogPath())
    #else:
        #raise SystemExit

    #self.quit()


class InstaCommandLine:

    description = "Instagiffer Command Line"
    author      = "Exhale Software Inc."

    def __init__(self):
        if not self.ArgsArePresent():
            return

        self.videoFileName = None
        self.ParseArguments()
        
    def ParseArguments(self):
        # parser = argparse.ArgumentParser(prog="instagiffer",
        #                                  description="You've discovered the Instagiffer %s command line. You're hardcore!" % (__version__),
        #                                  epilog="Happy Giffing!")
        # parser.add_argument('video', help='Path to local video file or Youtube link')
        # self.args          = parser.parse_args()

        self.videoFileName = sys.argv[1]      #self.args.video

    def ArgsArePresent(self):
        return len(sys.argv) > 1

    def GetVideoPath(self):
        if self.videoFileName is not None:
            logging.info(u"File specified on command line: " + self.videoFileName) 
            logging.info(u"File exists: %d" % (os.path.exists(self.videoFileName)))
            return self.videoFileName
        else:
            return None

    #
    # Coming soon stuff
    #

    def BatchRun(self):
        self.binPath  = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.conf     = InstaConfig(self.binPath + os.sep + 'instagiffer.conf')
        self.workDir  = CreateWorkingDir(self.conf)
        self.gif      = AnimatedGif(self.conf, self.videoFileName, self.workDir, self.OnShowProgress, None) 
        self.MakeGif()
        return 0

    # Progress callback
    def OnShowProgress(self, doneFlag, ignore = None):
        if doneFlag:
            print " [OK]"
        else:
            sys.stdout.write('.')

    # Makes a GIF according to current configuration
    def MakeGif(self):
        print "Extracting frames:"
        self.gif.ExtractFrames()
        print "Cropping and resizing:"
        self.gif.CropAndResize()
        print "Generating GIF:"
        self.gif.Generate()


def main():
    global __version__
    global __release__

    # cwd to the directory containing the executable
    exeDir = os.path.dirname(os.path.realpath(sys.argv[0]))
    os.chdir(exeDir)

    # Set environment
    if ImAMac():
        os.environ['MAGICK_HOME']           = './macdeps/im'
        os.environ['MAGICK_CONFIGURE_PATH'] = './macdeps/im/etc/ImageMagick-6'
        os.environ['FONTCONFIG_PATH']       = './macdeps/im/etc/fonts'

        # Now that Insta is loaded with a bundled Python version, we want
        # to make sure that youtube-dl to use the built-in Python
        os.environ['PYTHONHOME']='/System/Library/Frameworks/Python.framework/Versions/Current'

    # File logging options
    try:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s %(levelname)s: %(message)s",
                            #filename=open(expanduser("~") + 'instagiffer-event.log',
                            filename='instagiffer-event.log',
                            filemode='w')

    except:
        # Oh well. no logging!
        pass

    # Turn off annoying Pillow logs
    # print logging.Logger.manager.loggerDict # list all loggers
    logging.getLogger('PIL.Image').setLevel(logging.CRITICAL)
    logging.getLogger('PIL').setLevel(logging.CRITICAL)


    # Developers only:
    if not __release__:
        console = logging.StreamHandler(sys.stdout)
        logging.getLogger('').addHandler(console)

    #
    # Command line mode
    #

    cmdline = InstaCommandLine()
    cmdlineBatchMode = False
    cmdlineVideoPath = None
    if ImAPC() and cmdline.ArgsArePresent():
        cmdlineVideoPath = cmdline.GetVideoPath()
    
    # Command line mode or GUI?

    if cmdlineBatchMode:
        pass
    else:
        # Start the app.  Gather some diagnostic information about this machine to help with bug reporting
        logging.info("Starting Instagiffer version " + __version__ + "..." )

        Tk.report_callback_exception = tkErrorCatcher

        import platform
        if ImAPC():
            logging.info("OS: " + platform.platform())
        elif ImAMac():
            logging.info("OSX Version: " + str(platform.mac_ver()))
        else:
            logging.info("Unknown OS")

        logging.info(sys.version_info)
        logging.info("App: [" + exeDir + "]. Home: [" + expanduser("~") + "]")
        logging.info("System Locale: " + str(locale.getdefaultlocale()) + "; Preferred encoding: " + locale.getpreferredencoding())

        root = Tk()
        app  = GifApp(root, cmdlineVideoPath)

        root.mainloop()



#
# Entry point
#

if __name__ == '__main__':
    main()

