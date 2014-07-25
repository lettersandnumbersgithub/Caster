#http://effbot.org/tkinterbook/tkinter-events-and-bindings.htm
import Tkinter as tk
import tkFileDialog
from threading import (Timer, Thread)
import signal
from Tkinter import (StringVar, OptionMenu, Scrollbar, Frame)
import os, re, sys, json
import paths, utilities

import bottle
from bottle import run, post, request, response

"""
X    - Automatically figures out which file is open by continually scanning the top-level window and looking for something with the file extension
X    - it scans an entire directory, creating an XML file for that directory, which contains the names of all imports and things which follow a single
       = operator, or other language specific traits
X    - It remembers what folder was opened last, maybe save this to the json file
X    - Make it longer and docked on the right
X    - Ability to scroll the list
- a box into which to type file extensions
- 1 to 10 sticky list at the top, non-sticky list starts from index 11 --  this way, we don't need  separate commands for picking from the sticky list
- Create better patterns than the generic pattern
- It also has a drop-down box for manually switching files, and associated command
- It can also take the highlighted text and add it to the list
- A  rescan directory command
- Element control commands activate and deactivate with Element-- is it possible to do this from the element code?apparently not, at least not easily.
"""

   


class Element:
    def __init__(self):
        
        
        # setup stuff that were previously globals
        self.JSON_PATH=paths.get_element_json_path()
        self.TOTAL_SAVED_INFO={}
        self.current_file=None
        self.last_file_loaded=None
        self.GENERIC_PATTERN=re.compile("([A-Za-z0-9._]+\s*=)|(import [A-Za-z0-9._]+)")

        
        # setup tk
        self.all_names=[]
        self.root=tk.Tk()
        self.root.title("Element v.01")
        self.root.geometry("200x"+str(self.root.winfo_screenheight()-100)+"-1+20")
        self.root.wm_attributes("-topmost", 1)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
        # setup hotkeys
        self.root.bind_all("1", self.get_new)
#         self.root.bind_all("2", self.do_scrolling)
        
        # setup options for directory ask
        self.dir_opt = {}
        self.dir_opt['initialdir'] = 'C:\\natlink\\natlink\\macrosystem\\'
        self.dir_opt['mustexist'] = False
        self.dir_opt['parent'] = self.root
        self.dir_opt['title'] = 'Please select directory'
        
        # setup drop-down box
        self.dropdown_selected=StringVar(self.root)
        self.default_dropdown_message="Please select a scanned folder"
        self.dropdown_selected.set(self.default_dropdown_message)
        self.dropdown=OptionMenu(self.root, self.dropdown_selected, self.default_dropdown_message)
        self.dropdown.pack()
        self.populate_dropdown()
        if len(self.TOTAL_SAVED_INFO)==0:# if this is being run for the first time:
            self.TOTAL_SAVED_INFO["config"]={}
            self.TOTAL_SAVED_INFO["directories"]={}
        else:
            self.dropdown_selected.set(self.TOTAL_SAVED_INFO["config"]["last_directory"])
        
        # set up list
        label1 = tk.Label(text="Variable Names", name="label1")
        label1.pack()
        
        stickyframe=Frame(self.root)
        stickyscrollbar =  Scrollbar(stickyframe, orient=tk.VERTICAL)
        self.sticky_listbox_numbering = tk.Listbox(stickyframe, yscrollcommand=stickyscrollbar.set)
        self.sticky_listbox_content = tk.Listbox(stickyframe, yscrollcommand=stickyscrollbar.set)

        self.sticky_listbox_index=0
        s_lbn_opt={}
        s_lbn_opt_height=10
        s_lbn_opt["height"]=s_lbn_opt_height
        s_lbn_opt["width"]=4
        s_lbn_opt2={}
        s_lbn_opt2["height"]=s_lbn_opt_height
        
        stickyscrollbar.config(command=self.sticky_scroll_lists)
        stickyscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sticky_listbox_numbering.config(s_lbn_opt)
        self.sticky_listbox_numbering.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.sticky_listbox_content.config(s_lbn_opt2)
        self.sticky_listbox_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        stickyframe.pack()
        #-------
        
        listframe= Frame(self.root)
        scrollbar = Scrollbar(listframe, orient=tk.VERTICAL)
        self.listbox_numbering = tk.Listbox(listframe, yscrollcommand=scrollbar.set)
        self.listbox_content = tk.Listbox(listframe, yscrollcommand=scrollbar.set)
        
        self.listbox_index=0
        lbn_opt={}
        lbn_opt_height=30
        lbn_opt["height"]=lbn_opt_height
        lbn_opt["width"]=4
        lbn_opt2={}
        lbn_opt2["height"]=lbn_opt_height
        
        scrollbar.config(command=self.scroll_lists)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_numbering.config(lbn_opt)
        self.listbox_numbering.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.listbox_content.config(lbn_opt2)
        self.listbox_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        listframe.pack()
        
        # setup search box
        self.search_box = tk.Entry(name="search_box")
        self.search_box.pack()
        
        # update active file every n seconds
        self.interval=1
        self.filename_pattern=re.compile(r"[/\\]([\w]+\.[\w]+)")
        self.old_active_window_title=""
        Timer(self.interval, self.update_active_file).start()
        
        # start bottle server, tk main loop
        Timer(self.interval, self.start_server).start()
        bottle.route('/process',method="POST")(self.process_request)
        self.root.mainloop()
    
    def on_exit(self):
        utilities.report("Element: shutting down")
        self.root.destroy()
        os.kill(os.getpid(), signal.SIGTERM)
    
    def start_server(self):
        run(host='localhost', port=1337, debug=True)
    
    def update_active_file(self):
        
        active_window_title=utilities.get_active_window_title()
        if not self.old_active_window_title==active_window_title:
            
            filename=""
            
            match_objects=self.filename_pattern.findall(active_window_title)
            if not len(match_objects)==  0:# if we found variable name in the line
                filename=match_objects[0]
             
            if not filename=="":
                self.old_active_window_title=active_window_title# only update were on a new file, not just a new window
                self.populate_list(filename)
                self.last_file_loaded=filename
        Timer(self.interval, self.update_active_file).start()
        
    def scroll_to(self, index):#don't need this for sticky list
        self.scroll_lists(index)
    
    def scroll_lists(self, *args):# synchronizes  numbering list and  content list with a single scrollbar
        apply(self.listbox_numbering.yview, args)
        apply(self.listbox_content.yview, args)
    
    def sticky_scroll_lists(self, *args):
        apply(self.sticky_listbox_numbering.yview, args)
        apply(self.sticky_listbox_content.yview, args)
        
    def clear_lists(self):# used when changing files
        self.listbox_numbering.delete(0, tk.END)
        self.listbox_content.delete(0, tk.END)
        self.sticky_listbox_numbering.delete(0, tk.END)
        self.sticky_listbox_content.delete(0, tk.END)
    
    #FOR MANIPULATING THE     LIST    
    def move_to_top(self,name):
        self.all_names.remove(name)
        self.all_names=[name]+self.all_names
    
    #FOR LOADING 
    def populate_dropdown(self):
        self.TOTAL_SAVED_INFO=utilities.load_json_file(self.JSON_PATH)
        menu = self.dropdown["menu"]
        menu.delete(0, tk.END)
        if "directories" in self.TOTAL_SAVED_INFO:
            for key in self.TOTAL_SAVED_INFO["directories"]:
                menu.add_command(label=key, command=lambda key=key: self.select_from_dropdown(key))
    
    def select_from_dropdown(self, key):
        self.TOTAL_SAVED_INFO["config"]["last_directory"]=key
        utilities.save_json_file(self.TOTAL_SAVED_INFO, self.JSON_PATH)
        self.dropdown_selected.set(key)
    
    def populate_list(self, file_to_activate):

        selected_directory=self.dropdown_selected.get()
        self.current_file=None
        if selected_directory==self.default_dropdown_message:
            return#  if a scanned for hasn't been selected, there's no need to go any further
        self.clear_lists()
        for absolute_path in self.TOTAL_SAVED_INFO["directories"][selected_directory]["files"]:
            if absolute_path.endswith("/"+file_to_activate) or absolute_path.endswith("\\"+file_to_activate):
                self.current_file=self.TOTAL_SAVED_INFO["directories"][selected_directory]["files"][absolute_path]
                break
        if not self.current_file==None:
            self.reload_list(self.current_file["names"],self.current_file["sticky"])
    
    def reload_list(self, namelist, stickylist):
        self.listbox_index=0# reset index upon reload
        for i in range(0, 10):
            self.add_to_stickylist(stickylist[i])
        for name in namelist:
            self.add_to_list(name)

    def add_to_list(self, item):
        self.listbox_index+=1    
        self.listbox_numbering.insert(tk.END, str(self.listbox_index))
        self.listbox_content.insert(tk.END, item)
    
    def add_to_stickylist(self, sticky):
        self.listbox_index+=1
        self.sticky_listbox_numbering.insert(tk.END, str(self.listbox_index))
        self.sticky_listbox_content.insert(tk.END, sticky)
    
    #FOR SCANNING AND SAVING FILES    
    def get_new(self,event):
        directory=self.ask_directory()
        self.scan_directory(directory)
        utilities.save_json_file(self.TOTAL_SAVED_INFO, self.JSON_PATH)
        self.populate_dropdown()
        
    def scan_directory(self,directory):
        pattern_being_used=self.GENERIC_PATTERN# later on, can add code to choose which pattern to use
        
        scanned_directory={}
        acceptable_extensions=[".py"]# this is hardcoded for now, will read from a box later
        try:
            for base, dirs, files in os.walk(directory):# traverse base directory, and list directories as dirs and files as files
                utilities.report(base)
                for fname in files:
                    extension="."+fname.split(".")[-1]
                    if extension in acceptable_extensions:
                        scanned_file={}
                        scanned_file["filename"]=fname
                        absolute_path=base+"/"+fname
                        scanned_file["names"]=[]
                        scanned_file["sticky"]=["","","","","","","","","",""]
                        f = open(base+"\\"+fname, "r")
                        lines = f.readlines()
                        f.close()
                        
                        for line in lines:#search out imports, function names, variable names
                            match_objects=pattern_being_used.findall(line)
                            if not len(match_objects)==  0:# if we found  something relevant in the line
                                mo=match_objects[0][0]
                                result=""
                                if "." in mo:# figure out whether it's an import#----- to do: this check doesn't work right
                                    result=mo.split(".")[-1]
                                else:
                                    result=mo.replace(" ", "").split("=")[0]
                                # also to do: scan for function names
                                
                                if not (result in scanned_file["names"] or result in scanned_file["sticky"]) and not result=="":
                                    scanned_file["names"].append(result)
                        
                        scanned_file["names"].sort()
                        scanned_directory[absolute_path]=scanned_file
        except Exception:
            utilities.report(utilities.list_to_string(sys.exc_info()))
        meta_information={}
        meta_information["files"]=scanned_directory
        meta_information["extensions"]=acceptable_extensions
        self.TOTAL_SAVED_INFO["directories"][directory]=meta_information
        

        
    def ask_directory(self):# returns a string of the directory name
        return tkFileDialog.askdirectory(**self.dir_opt)
    
    def process_request(self):
        if self.current_file==None:
            return "No file is currently loaded."
        
        request_object = json.loads(request.body.read())
        action_type=request_object["action_type"]
        if "index" in request_object:
            index=int(request_object["index"])
            if action_type=="scroll":
                if index<self.listbox_content.size():
                    self.scroll_to(index)
                return "c"
            elif action_type=="retrieve":
                index_plus_one=index+1
                if index<10:# if sticky
                    return self.sticky_listbox_content.get(index, index_plus_one)[0]#
                else:
                    return self.listbox_content.get(index-10, index_plus_one-10)[0]
            elif action_type=="sticky":# requires sticky_index,auto_sticky regardless of what mode it's in
                sticky_index=request_object["sticky_index"]# the index of the slot on the sticky list to be overwritten
                sticky_previous=self.current_file["sticky"][sticky_index]
                if not sticky_previous=="":# if you overwrite an old sticky entry, move it back down to the unordered list
                    self.current_file["names"].append(sticky_previous)

                # now, either replace the slot with a string or a word from the unordered list, first a string:                
                if not request_object["auto_sticky"]=="":
                    self.current_file["sticky"][sticky_index]=request_object["auto_sticky"]
                else:
                    index_plus_one= index+1
                    target_word=self.listbox_content.get(index-10, index_plus_one-10)[0]
                    self.current_file["sticky"][sticky_index]=target_word
                    self.current_file["names"].remove(target_word)
#
                utilities.save_json_file(self.TOTAL_SAVED_INFO, self.JSON_PATH)
                self.populate_list(self.last_file_loaded)
                return "c"
            elif action_type=="delete":
                return "mode not ready yet"
            elif action_type=="unsticky":
                return "mode not ready yet"
        elif "name" in request_object:
            name=request_object["name"]
            if action_type=="add":
                if name not in self.all_names:
                    self.all_names.append(name)
                    #save json
                    # reload list- you want to make sure that all_names is being used in the first place
            return "mode not ready yet"
        return 'unrecognized request received: '+request_object["action_type"]


app=Element()  
