#!/usr/bin/env python

import copy
import os
import configparser
import time
from pp_beepplayer import BeepPlayer


class pp_aplaydriver(object):

    # control list items
    DIRECTION = 0       # out, if blank  or in then section disabled
    NAME = 1                # command match - symbolic name for output
    FILE = 2            # file to play
    DEVICE = 3        # blank, hdmi, local or alsa


    TEMPLATE=['','','','']

    # CLASS VARIABLES  (pp_aplaydriver.)
    driver_active=False



    # executed by main program and by each object using the driver
    def __init__(self):
        self.bp=BeepPlayer()
        pass

     # executed once from main program   
    def init(self,filename,filepath,widget,pp_dir,pp_home,pp_profile,event_callback=None):
        # instantiate arguments
        self.widget=widget
        self.filename=filename
        self.filepath=filepath
        self.event_callback=event_callback
        self.pp_dir = pp_dir
        self.pp_home=pp_home
        self.pp_profile=pp_profile

        pp_aplaydriver.driver_active = False

        # read .cfg file.
        reason,message=self._read(self.filename,self.filepath)
        if reason =='error':
            return 'error',message
        
        if self.config.has_section('DRIVER') is False:
            return 'error','No DRIVER section in '+self.filepath
        
        # read information from DRIVER section
        pp_aplaydriver.title=self.config.get('DRIVER','title')
  
        pp_aplaydriver.out_names=[]
        for section in self.config.sections():
            if section == 'DRIVER':
                continue
            entry=copy.deepcopy(pp_aplaydriver.TEMPLATE)
            entry[pp_aplaydriver.DIRECTION]=self.config.get(section,'direction')
            entry[pp_aplaydriver.NAME]=self.config.get(section,'name')
            entry[pp_aplaydriver.FILE]=self.config.get(section,'file')
            entry[pp_aplaydriver.DEVICE]=self.config.get(section,'device')

            if entry[pp_aplaydriver.DIRECTION] == 'out':
                if entry[pp_aplaydriver.DEVICE] not in ('','hdmi','local','USB','A/V','hdmi0','hdmi1','USB2','bluetooth'):
                    return 'error',pp_aplaydriver.title + ' unknown device for '+ entry[pp_aplaydriver.NAME] +' - ' +entry[pp_aplaydriver.DEVICE]
                pp_aplaydriver.out_names.append(copy.deepcopy(entry))


        # print pp_aplaydriver.out_names
        
        self.tick_timer=None

        
        # all ok so indicate the driver is active
        pp_aplaydriver.driver_active=True

        # init must return two arguments
        return 'normal',pp_aplaydriver.title + ' active'


    # start the input loop - no inputs to sample
    def start(self):
        pass

      
    # allow querying of driver state
    def is_active(self):
        return pp_aplaydriver.driver_active

    # dummy get input
    def get_input(self,channel):
            return False, None

  # called by main program only. Called when PP is closed down               
    def terminate(self):
        if self.tick_timer is not None:
            self.widget.after_cancel(self.tick_timer)
            self.tick_timer=None
        pp_aplaydriver.driver_active = False



# ************************************************
# output interface method
# this can be called from many objects so needs to operate on class variables
# if it is supplying data to the main program
# ************************************************                            
    # execute an output event

    def handle_output_event(self,name,param_type,param_values,req_time):

        # print 'comand is',name,param_type, param_values

        # match command against all out entries in config data
        for entry in pp_aplaydriver.out_names:
            # does the symbolic name and type match value in the configuration (type is fixed at beep)
            if name == entry[pp_aplaydriver.NAME] and param_type == 'beep':
                device=entry[pp_aplaydriver.DEVICE]
                location=entry[pp_aplaydriver.FILE]
                status,message=self.bp.play_animate_beep(location,device)
                if status=='error':
                    return status,message
                else:
                    return 'normal',''
        return 'normal','no match for ' + name + ' ' + param_type


   


                    
# ***********************************
# reading .cfg file
# ************************************

    def _read(self,filename,filepath):
        # try inside profile
        if os.path.exists(filepath):
            self.config = configparser.ConfigParser(inline_comment_prefixes = (';',))
            self.config.read(filepath)
            # self.mon.log(self,filename + " read from "+ filepath)
            return 'normal',filename+' read'
        else:
            return 'error',filename + ' not found at: '+filepath

# ****************************************


if __name__ == '__main__':
    from tkinter import *

    def button_callback(symbol,source):
        print('callback',symbol,source)
        if symbol=='pp-stop':
            idd.terminate()
            exit()
        pass

    root = Tk()

    w = Label(root, text="pp_aplaydriver.py test harness")
    w.pack()
    
    idd=pp_aplaydriver()
    
    pp_dir='/home/pi/pipresents'
    pp_home='/home/pi'
    pp_profile='/home/pi/pp_home/pp_profiles/beep'
    
    reason,message=idd.init('beep.cfg','/home/pi/pipresents/pp_resources/pp_templates/beep.cfg',root,pp_dir,pp_home,pp_profile,button_callback)
    print(reason,message)
    if reason != 'error':
        idd.start()
        idd.handle_output_event('beep1','beep','',0)
    # root.mainloop()
