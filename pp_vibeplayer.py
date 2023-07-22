import os
import copy
from pp_utils import Monitor
import time
from DRV2605_lib import DRV2605, PlayWaveform, WaitMillis

class VibePlayer(object):

    pp_home=''
    pp_profile=''

    def __init__(self):
        self.mon=Monitor()
        self.drv2605 = DRV2605()

    # run once when PP starts
    def init(self,device,library):
        self.device=device
        self.library=library


        self.drv2605.reset()
        
        self.drv2605.set_feedback_mode(device)  #depends on actuator connected ERM or LRA
        
        # LRA has one library, for ERM there are a number to choose from
        if device == 'LRA':
            self.drv2605.set_library('LRA')
        else:
            self.drv2605.set_library(library)
            
        #self.drv2605.set_erm_loop_mode(loop)

        
    # should only be done when PP starts (in init) because of long wait time
    def calibrate(self):
        print("Calibrating...")
        self.drv2605.auto_calibrate()
        time.sleep(0.5)


    #play a sequence using a waveform from the DRV2506 library
    def play_animate_vibe_sequence(self,sequence_vals,loop,trigger):
        self.mon.log (self,'Play sequence '+ ','.join(sequence_vals))
        self.drv2605.set_mode(trigger) #mode for the sequence 'Internal Trigger',Edge Trigger',Level Trigger'
        self.drv2605.set_erm_loop_mode(loop)  # library always uses open loop
        self.drv2605.set_ac_couple('Off')
        self.drv2605.set_pwm_input_mode('PWM')
        self.do_sequence(sequence_vals)



    def do_sequence(self,sequence_vals):
        sequence = []
        index=0
        for val in sequence_vals:
            if int(val) >-1:
                sequence.append(PlayWaveform(int(val)))    #waveform index
            else:
                sequence.append(WaitMillis(-int(val)))     #delay in mS
            index +=1
            if index>8:
                return 'error', 'Vibe Sequence too long: '+ sequence_vals
        if index <8:
            sequence.append(PlayWaveform(0))            
        self.drv2605.set_sequence(*sequence)
        self.drv2605.go()
        return 'normal',''
        
    def stop_sequence(self):
        self.mon.log(self,'stop sequence')
        self.drv2605.stop()

    # play a sequence from a show control command
    def play_show_vibe(self,command_text):

        fields = command_text.split()
        print ('show VIBW',fields)
        if len(fields) !=2:
            return 'error',"incorrect number of fields in vibe command" + line
        sequence_vals = fields[1].split(',')

        self.drv2605.set_mode('Internal Trigger') #trigger for the sequence, 'Internal Trigger' for show control
        self.drv2605.set_erm_loop_mode('Open Loop')  # library always uses open loop
        self.do_sequence(sequence_vals)
        return 'normal',''
        
    def start_audio_vibe(self,loop,max_input,min_input,vibe_name):
        self.mon.log(self,'start audio vibe: '+vibe_name)
        self.drv2605.set_ac_couple('On')
        self.drv2605.set_pwm_input_mode('Analog')
        self.drv2605.set_erm_loop_mode(loop) 
        self.drv2605.set_mode('Audio In')
        self.drv2605.set_max_audio_input(max_input)
        self.drv2605.set_min_audio_input(min_input)        
        
    def stop_audio_vibe(self):
        self.mon.log(self,'stop audio vibe')
        self.init(self.device,self.library)







 
