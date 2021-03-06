# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
from builtins import str

import io
import json
import locale
import os
import re
import sys
import time
import traceback
from __builtin__ import True
from subprocess import Popen
import tomlkit
from castervoice.lib.clipboard import Clipboard
from castervoice.lib import printer
from castervoice.lib.util import guidance

if sys.version_info > (3, 0):
    from pathlib import Path  # pylint: disable=import-error
else:
    from castervoice.lib.util.pathlib import Path

try:
    import win32gui
    import win32clipboard
    from _winreg import (CloseKey, ConnectRegistry, HKEY_CLASSES_ROOT,
                         HKEY_CURRENT_USER, OpenKey, QueryValueEx)
    from dragonfly.windows.window import Window
    from dragonfly import Key, Pause
except:
    printer.out("utilities.py imports failed.")

try:  # Style C -- may be imported into Caster, or externally
    BASE_PATH = os.path.realpath(__file__).rsplit(os.path.sep + "castervoice", 1)[0]
    if BASE_PATH not in sys.path:
        sys.path.append(BASE_PATH)
finally:
    from castervoice.lib import settings, printer

# filename_pattern was used to determine when to update the list in the element window,
# checked to see when a new file name had appeared
FILENAME_PATTERN = re.compile(r"[/\\]([\w_ ]+\.[\w]+)")

import struct
from ctypes import cdll

# https://github.com/mrob95/pyVirtualDesktopAccessor
# Source: https://github.com/Ciantic/VirtualDesktopAccessor
try:
    if struct.calcsize("P")*8 == 32:
        vda = cdll.LoadLibrary(
            str(Path(BASE_PATH).joinpath("castervoice/bin/VirtualDesktopAccessor32.dll")).encode(locale.getpreferredencoding()))
    else:
        vda = cdll.LoadLibrary(
            str(Path(BASE_PATH).joinpath("castervoice/bin/VirtualDesktopAccessor64.dll")).encode(locale.getpreferredencoding()))
except Exception as e:
    print("Virtual desktop accessor loading failed with '%s'" % str(e))

def move_current_window_to_desktop(n=0, follow=False):
    vda = load_vda()  # pylint: disable=undefined-variable
    wndh = win32gui.GetForegroundWindow()
    vda.MoveWindowToDesktopNumber(wndh, n-1)
    if follow:
        vda.GoToDesktopNumber(n-1)

def go_to_desktop_number(n):
    vda.GoToDesktopNumber(n-1)

def close_all_workspaces():
    total = vda.GetDesktopCount()
    go_to_desktop_number(total)
    Key("wc-f4/10:" + str(total-1)).execute()

def window_exists(classname, windowname):
    try:
        import win32ui
        win32ui.FindWindow(classname, windowname)
    except win32ui.error:
        return False
    else:
        return True


def get_active_window_title(pid=None):
    _pid = win32gui.GetForegroundWindow() if pid is None else pid
    return unicode(win32gui.GetWindowText(_pid), errors='ignore')


def get_active_window_path():
    return Window.get_foreground().executable


def get_window_by_title(title):
    # returns 0 if nothing found
    hwnd = win32gui.FindWindowEx(0, 0, 0, title)
    return hwnd


def get_window_title_info():
    '''get name of active file and folders in path;
    will be needed to look up collection of symbols
    in scanner data'''
    global FILENAME_PATTERN
    title = get_active_window_title().replace("\\", "/")
    match_object = FILENAME_PATTERN.findall(title)
    filename = None
    if len(match_object) > 0:
        filename = match_object[0]
    path_folders = title.split("/")[:-1]
    return [filename, path_folders, title]

def focus_mousegrid(gridtitle):
    '''
    Loops over active windows for MouseGrid window titles. Issue #171
    When MouseGrid window titles found focuses MouseGrid overly.
    '''
    if sys.platform.startswith('win'):
        # May not be needed for Linux/Mac OS - testing required
        try:
            for i in range(9):
                matches = Window.get_matching_windows(title=gridtitle, executable="python")
                if not matches:
                    Pause("50").execute()
                else:
                    break
            if matches:
                for handle in matches:
                    handle.set_foreground()
                    break
            else:
                printer.out("`Title: `{}` no matching windows found".format(gridtitle))
        except Exception as e:
            printer.out("Error focusing MouseGrid: {}".format(e))
    else:
        pass


def save_toml_file(data, path):
    guidance.offer()
    try:
        formatted_data = unicode(tomlkit.dumps(data))
        with io.open(path, "wt", encoding="utf-8") as f:
            f.write(formatted_data)
    except Exception:
        simple_log(True)


def load_toml_file(path):
    guidance.offer()
    result = {}
    try:
        with io.open(path, "rt", encoding="utf-8") as f:
            result = tomlkit.loads(f.read()).value
    except IOError as e:
        if e.errno == 2:  # The file doesn't exist.
            save_toml_file(result, path)
        else:
            raise
    except Exception:
        simple_log(True)
    return result


def save_json_file(data, path):
    guidance.offer()
    try:
        formatted_data = unicode(json.dumps(data, ensure_ascii=False))
        with io.open(path, "wt", encoding="utf-8") as f:
            f.write(formatted_data)
    except Exception:
        simple_log(True)


def load_json_file(path):
    guidance.offer()
    result = {}
    try:
        with io.open(path, "rt", encoding="utf-8") as json_file:
            result = json.load(json_file)
    except IOError as e:
        if e.errno == 2:  # The file doesn't exist.
            save_json_file(result, path)
        else:
            raise
    except Exception:
        simple_log(True)
    return result


def list_to_string(l):
    return u"\n".join([unicode(x) for x in l])


def simple_log(to_file=False):
    msg = list_to_string(sys.exc_info())
    printer.out(msg)
    for tb in traceback.format_tb(sys.exc_info()[2]):
        printer.out(tb)
    if to_file:
        with io.open(settings.SETTINGS["paths"]["LOG_PATH"], 'at', encoding="utf-8") as f:
            f.write(msg + "\n")


def availability_message(feature, dependency):
    printer.out(feature + " feature not available without " + dependency)


def remote_debug(who_called_it=None):
    if who_called_it is None:
        who_called_it = "An unidentified process"
    try:
        import pydevd  # @UnresolvedImport pylint: disable=import-error
        pydevd.settrace()
    except Exception:
        printer.out("ERROR: " + who_called_it +
              " called utilities.remote_debug() but the debug server wasn't running.")


def reboot(wsr=False):
    popen_parameters = []
    if wsr:
        popen_parameters.append(settings.SETTINGS["paths"]["REBOOT_PATH_WSR"])
        popen_parameters.append(settings.SETTINGS["paths"]["WSR_PATH"])
        # castervoice path inserted too if there's a way to wake up WSR
    else:
        popen_parameters.append(settings.SETTINGS["paths"]["REBOOT_PATH"])
        popen_parameters.append(settings.SETTINGS["paths"]["ENGINE_PATH"])
        import natlinkstatus
        status = natlinkstatus.NatlinkStatus()
        username = status.getUserName()
        popen_parameters.append(username)
    printer.out(popen_parameters)
    Popen(popen_parameters)

def default_browser_command():
    '''
    Tries to get default browser command, returns either a space delimited
    command string with '%1' as URL placeholder, or empty string.
    '''
    browser_class = 'Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\https\\UserChoice'
    try:
        reg = ConnectRegistry(None,HKEY_CURRENT_USER)
        key = OpenKey(reg, browser_class)
        value, t = QueryValueEx(key, 'ProgId')
        CloseKey(key)
        CloseKey(reg)
        reg = ConnectRegistry(None,HKEY_CLASSES_ROOT)
        key = OpenKey(reg, '%s\\shell\\open\\command' % value)
        path, t = QueryValueEx(key, None)
    except WindowsError:
        # logger.warn(e)
        traceback.print_exc()
        return ''
    finally:
        CloseKey(key)
        CloseKey(reg)
    return path


def clear_log():
    # Function to clear natlink status window
    try:
        # pylint: disable=import-error
        import natlink
        windows = Window.get_all_windows()
        matching = [w for w in windows
        if b"Messages from Python Macros" in w.title]
        if matching:
            handle = (matching[0].handle)
            rt_handle = win32gui.FindWindowEx(handle, None, "RICHEDIT", None)
            win32gui.SetWindowText(rt_handle, "")
            return
    except Exception as e:
        printer.out(e)

def get_clipboard_formats():
    '''
    Return list of all data formats currently in the clipboard
    '''
    formats = []
    f = win32clipboard.EnumClipboardFormats(0)
    while f:
        formats.append(f)
        f = win32clipboard.EnumClipboardFormats(f)
    return formats

def get_selected_files(folders=False):
    '''
    Copy selected (text or file is subsequently of interest) to a fresh clipboard
    '''
    cb = Clipboard(from_system=True)
    cb.clear_clipboard()
    Key("c-c").execute()
    time.sleep(0.1)
    files = get_clipboard_files(folders)
    cb.copy_to_system()
    return files

def get_clipboard_files(folders=False):
    '''
    Enumerate clipboard content and return files either directly copied or
    highlighted path copied
    '''
    files = None
    win32clipboard.OpenClipboard()
    f = get_clipboard_formats()
    if win32clipboard.CF_HDROP in f:
        files = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
    elif win32clipboard.CF_UNICODETEXT in f:
        files = [win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)]
    elif win32clipboard.CF_TEXT in f:
        files = [win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)]
    elif win32clipboard.CF_OEMTEXT in f:
        files = [win32clipboard.GetClipboardData(win32clipboard.CF_OEMTEXT)]
    if folders:
        files = [f for f in files if os.path.isdir(f)] if files else None
    else:
        files = [f for f in files if os.path.isfile(f)] if files else None
    win32clipboard.CloseClipboard()
    return files
