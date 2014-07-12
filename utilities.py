'''
Created on Jun 12, 2014

@author: dave
'''
from dragonfly import Key
import win32gui, win32process, win32api
import os, json
import paths

BASE_PATH = paths.get_base()

def press_digits(n):
    number=str(n)
    for digit in number:
        Key(digit).execute()
        
def get_active_window_hwnd():
    return str(win32gui.GetForegroundWindow())

def get_active_window_title():
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())

def get_active_window_path():
    name = win32gui.GetForegroundWindow()
    t,p = win32process.GetWindowThreadProcessId(name)
    handle = win32api.OpenProcess(0x0410,False,p)
    return win32process.GetModuleFileNameEx( handle, 0 )

def clear_pyc():
    global BASE_PATH
    os.chdir(BASE_PATH)
    for files in os.listdir("."):
        if files.endswith(".pyc"):
            filepath=BASE_PATH+files
            os.remove(filepath)
            print "Deleted: "+filepath

def save_json_file(data, path):
    try:
        formatted_data = json.dumps(data, sort_keys=True, indent=4,
            ensure_ascii=False)
        with open(path, "w+") as f:
            f.write(formatted_data)
            f.close()
    except Exception as e:
        print("Could not save file: %s" % str(e))

def load_json_file(path):
    result={}
    try:
        if os.path.isfile(path):  # If the file exists.
            with open(path, "r") as f:
                result = json.loads(f.read())
                f.close()
        else:
            save_json_file(result, path)
    except Exception as e:
        print("Could not load file: %s" % str(e))
    return result

def remote_debug():
    import pydevd;#@UnresolvedImport
    pydevd.settrace()