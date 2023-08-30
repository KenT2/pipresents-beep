#!/usr/bin/env python

import copy
import os
import configparser
import time
from pp_vibeplayer import VibePlayer
from subprocess import call, check_output

class pp_DRV2605driver(object):

    # control list items
    NAME = 0                # command match - symbolic name for output  DRV2605
    PARAM_TYPE = 1          # type of params - command match  sequence,
                            # sequence-name, audio-vibe
    SEQUENCE_NAME = 2            # name of sequence
    TRIGGER = 3             # internal, various external
    SEQUENCE = 4            # for sequence 10,2,-10,4
    LOOP_TYPE = 5
    VIBE_NAME = 6
    MAX_INPUT = 7
    MIN_INPUT = 8                

    TEMPLATE=['','','','','','','','','']

    # CLASS VARIABLES  (pp_DRV2605driver.)
    driver_active=False



    # executed by main program and by each object using the driver
    def __init__(self):
        # test I2C is enabled
        com=['sudo' ,'raspi-config' ,'nonint' ,'get_i2c']
        result= check_output(com,universal_newlines=True)
        #print ('I2C-driver',result)
        if int(result) == 1:
            #print ('driver-error')
            print("ERROR: DRV2506 I/O plugin,I2C interface must be enabled for Vibes")
            exit(102)
        else:
            #print('dr2506 driver _init vibeplayer')
            self.vp=VibePlayer()


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

        pp_DRV2605driver.driver_active = False

        # read .cfg file.
        reason,message=self._read(self.filename,self.filepath)
        if reason =='error':
            return 'error',message
            
        
        if self.config.has_section('DRIVER') is False:
            return 'error','No DRIVER section in '+self.filepath+'/'+self.filename
        
        # read information from DRIVER section
        pp_DRV2605driver.title=self.config.get('DRIVER','title')
        self.device = self.config.get('DRIVER','device-type')
        self.library=self.config.get('DRIVER','library')

  
        pp_DRV2605driver.out_names=[]
        for section in self.config.sections():
            if section == 'DRIVER':
                continue
            entry=copy.deepcopy(pp_DRV2605driver.TEMPLATE)
            entry[pp_DRV2605driver.NAME]=self.config.get(section,'name')
            entry[pp_DRV2605driver.PARAM_TYPE]=self.config.get(section,'type')
            param_type = entry[pp_DRV2605driver.PARAM_TYPE]
            if param_type == 'sequence-name':
                entry[pp_DRV2605driver.SEQUENCE_NAME]=self.config.get(section,'sequence-name')
                entry[pp_DRV2605driver.SEQUENCE]=self.config.get(section,'sequence')
                entry[pp_DRV2605driver.TRIGGER]=self.config.get(section,'trigger')
                entry[pp_DRV2605driver.LOOP_TYPE]=self.config.get(section,'loop-type')
            if param_type == 'sequence':
                entry[pp_DRV2605driver.TRIGGER]=self.config.get(section,'trigger')
                entry[pp_DRV2605driver.LOOP_TYPE]=self.config.get(section,'loop-type')
            if param_type == 'audio-vibe-name':
                entry[pp_DRV2605driver.VIBE_NAME]=self.config.get(section,'vibe-name')
                entry[pp_DRV2605driver.MAX_INPUT]=self.config.get(section,'max-input')
                entry[pp_DRV2605driver.MIN_INPUT]=self.config.get(section,'min-input')
                entry[pp_DRV2605driver.LOOP_TYPE]=self.config.get(section,'loop-type')

            pp_DRV2605driver.out_names.append(copy.deepcopy(entry))


        #print (pp_DRV2605driver.out_names)
        self.vp.init(self.device,self.library)
        
        self.tick_timer=None

        
        # all ok so indicate the driver is active
        pp_DRV2605driver.driver_active=True

        # init must return two arguments
        return 'normal',pp_DRV2605driver.title + ' active'


    # start the input loop - no inputs to sample
    def start(self):
        pass

      
    # allow querying of driver state
    def is_active(self):
        return pp_DRV2605driver.driver_active

    # dummy get input
    def get_input(self,channel):
            return False, None

  # called by main program only. Called when PP is closed down               
    def terminate(self):
        self.vp.stop_sequence()
        #reset to stop audio vibe
        self.vp.init(self.device,self.library)
        if self.tick_timer is not None:
            self.widget.after_cancel(self.tick_timer)
            self.tick_timer=None
        pp_DRV2605driver.driver_active = False



# ************************************************
# output interface method
# this can be called from many objects so needs to operate on class variables
# if it is supplying data to the main program
# ************************************************                            
    # execute an output event

    def handle_output_event(self,name,param_type,param_values,req_time):

        # print ('comand is',name,param_type, param_values)

        # match command against all out entries in config data
        for entry in pp_DRV2605driver.out_names:
            # does the symbolic name and param type match value in the configuration 
            if name == entry[pp_DRV2605driver.NAME] and param_type == entry[pp_DRV2605driver.PARAM_TYPE]:
                status,message=self.dispatch_command(name,param_type,param_values,entry)
                if status == 'error':
                    return status,message
                else:
                    return 'normal',''        

        return 'normal','no match for ' + name + ' ' + param_type


    def dispatch_command(self,name,param_type,param_values,entry):
        # print ('dispatch',name,param_type,param_values)
        if param_type == 'sequence':
            status,message=self.do_sequence(param_values,entry)
            return status,message
        if param_type == 'sequence-name':
            status,message=self.do_sequence_name(param_values,pp_DRV2605driver.out_names)
            return status,message
        if param_type == 'audio-vibe-name':
            status,message=self.do_audio_vibe_name(param_values,pp_DRV2605driver.out_names)
            return status,message
        if param_type == 'stop-sequence':
            self.vp.stop_sequence()
            return 'normal',''
        if param_type == 'stop-audio-vibe':
            self.vp.stop_audio_vibe()
            return 'normal',''
        # print ('NO MATCH on param type')    
        return 'normal','no match on param-type'

   
    def do_sequence(self,param_values,entry):
        sequence_values=param_values[0].split(',')
        # print('sequence',sequence_values,entry[pp_DRV2605driver.TRIGGER])
        self.vp.play_animate_vibe_sequence(sequence_values,
            entry[pp_DRV2605driver.LOOP_TYPE],
            entry[pp_DRV2605driver.TRIGGER])
        return 'normal',''
        
    def do_sequence_name(self,param_values,entries):
        for entry in entries:
            #print (param_values[0], entry[pp_DRV2605driver.SEQUENCE_NAME])
            if param_values[0] != entry[pp_DRV2605driver.SEQUENCE_NAME]:
                continue
            sequence=entry[pp_DRV2605driver.SEQUENCE]
            sequence_values=sequence.split(',')
            # print('sequence-name',sequence_values,entry[pp_DRV2605driver.TRIGGER])
            self.vp.play_animate_vibe_sequence(sequence_values,
            entry[pp_DRV2605driver.LOOP_TYPE],
            entry[pp_DRV2605driver.TRIGGER])
            return 'normal',''
        return 'normal','param does not match'
        
    def do_audio_vibe_name(self,param_values,entries):
        for entry in entries:

            if param_values[0] != entry[pp_DRV2605driver.VIBE_NAME]:
                continue
            # print (param_values[0], entry[pp_DRV2605driver.VIBE_NAME])
            self.vp.start_audio_vibe(entry[pp_DRV2605driver.LOOP_TYPE],
                                 entry[pp_DRV2605driver.MAX_INPUT],
                                 entry[pp_DRV2605driver.MIN_INPUT],
                                  entry[pp_DRV2605driver.VIBE_NAME])
            return 'normal',''
        return 'normal','name does not match'

                    
# ***********************************
# reading .cfg file
# ************************************

    def _read(self,filename,filepath):
        # try inside profile
        if os.path.exists(filepath):
            self.config = configparser.ConfigParser(inline_comment_prefixes = (';',))
            self.config.optionxform = str
            self.config.read(filepath)
            # print (filename + " read from "+ filepath)
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

    w = Label(root, text="pp_DRV2605driver.py test harness")
    w.pack()
    
    idd=pp_DRV2605driver()
    
    pp_dir='/home/pi/pipresents-beep'
    pp_home='/home/pi'
    pp_profile='/home/pi/pp_home/pp_profiles/beep'
    
    reason,message=idd.init('DRV2605.cfg','/home/pi/pipresents-beep/pp_io_config/DRV2605.cfg',root,pp_dir,pp_home,pp_profile,button_callback)
    print(reason,message)
    if reason != 'error':
        idd.start()
        idd.handle_output_event('DRV2605','sequence-name',['sequence1'],0)
    # root.mainloop()

