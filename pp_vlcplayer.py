# -*- coding: utf-8 -*-
import os,sys
from pp_vlcdriver import VLCDriver
from pp_player import Player
#sudo pip3 install python-vlc

from pp_displaymanager import DisplayManager
from pp_audiomanager import AudioManager
import pexpect
from tkinter import *

class VLCPlayer(Player):
    """
    plays a track using VLCDriver to access VLC via libvlc
    _init_ iniitalises state and checks resources are available.
    use the returned instance reference in all other calls.
    At the end of the path (when closed) do not re-use, make instance= None and start again.
    States - 'initialised' when done successfully.
    """
    
    debug = False
    debug = True
    
    def __init__(self,
                 show_id,
                 showlist,
                 root,
                 canvas,
                 show_params,
                 track_params ,
                 pp_dir,
                 pp_home,
                 pp_profile,
                 end_callback,
                 command_callback):
                     

        # initialise items common to all players   
        Player.__init__( self,
                         show_id,
                         showlist,
                         root,
                         canvas,
                         show_params,
                         track_params ,
                         pp_dir,
                         pp_home,
                         pp_profile,
                         end_callback,
                         command_callback)
        self.mon.trace(self,'')
        
        self.dm=DisplayManager()
        self.am=AudioManager()

        # get player parameters from show/track
        if self.track_params['vlc-audio'] != "":
            self.vlc_audio= self.track_params['vlc-audio']
        else:
            self.vlc_audio= self.show_params['vlc-audio']        
        
        if self.track_params['vlc-volume'] != "":
            self.vlc_volume_text= self.track_params['vlc-volume']
        else:
            self.vlc_volume_text= self.show_params['vlc-volume']
            
        if self.track_params['vlc-window'] != '':
            self.vlc_window_text= self.track_params['vlc-window']
        else:
            self.vlc_window_text= self.show_params['vlc-window']

        if self.track_params['vlc-aspect-mode'] != '':
            self.vlc_aspect_mode= self.track_params['vlc-aspect-mode']
        else:
            self.vlc_aspect_mode= self.show_params['vlc-aspect-mode']
            
        if self.track_params['vlc-image-duration'] != '':
            self.vlc_image_duration_text= self.track_params['vlc-image-duration']
        else:
            self.vlc_image_duration_text= self.show_params['vlc-image-duration']
        
        if self.track_params['vlc-other-options'] != '':
            self.vlc_other_options= self.track_params['vlc-other-options']
        else:
            self.vlc_other_options= self.show_params['vlc-other-options']

        if self.track_params['vlc-layer'] != '':
            self.vlc_layer_text= self.track_params['vlc-layer']
        else:
            self.vlc_layer_text= self.show_params['vlc-layer']


        if self.track_params['vlc-freeze-at-start'] != '':
            self.freeze_at_start_text= self.track_params['vlc-freeze-at-start']
        else:
            self.freeze_at_start_text= self.show_params['vlc-freeze-at-start']

        if self.track_params['vlc-freeze-at-end'] != '':
            self.freeze_at_end_text= self.track_params['vlc-freeze-at-end']
        else:
            self.freeze_at_end_text= self.show_params['vlc-freeze-at-end']
            
        if self.track_params['pause-timeout'] != '':
            pause_timeout_text= self.track_params['pause-timeout']
        else:
            pause_timeout_text= self.show_params['pause-timeout']

        if pause_timeout_text.isdigit():
            self.pause_timeout= int(pause_timeout_text)
        else:
            self.pause_timeout=0
            
        # track only
        
        self.vlc_subtitles= self.track_params['vlc-subtitles']
            
        self.vlc_max_volume_text=self.track_params['vlc-max-volume']

        self.vlc_aspect_ratio= self.track_params['vlc-aspect-ratio']
    
        self.vlc_crop= self.track_params['vlc-crop']
           
                    
        # initialise video playing state and signals
        self.quit_signal=False
        self.unload_signal=False
        self.play_state='initialised'
        self.frozen_at_end=False
        self.pause_timer=None




    # LOAD - creates a VLC instance, loads a track and then pause
    def load(self,track,loaded_callback,enable_menu):  
        # instantiate arguments
        self.track=track
        self.loaded_callback=loaded_callback   #callback when loaded
        self.mon.log(self,"Load track received from show Id: "+ str(self.show_id) + ' ' +self.track)
        self.mon.trace(self,'')
        
        #process vlc parameters
        status,message=self.process_params()
        if status == 'error':
            self.mon.err(self,message)
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error',message)
                return 

        #for pulse get sink name and check device is connected 
        self.audio_sys=self.am.get_audio_sys()
        if self.audio_sys == 'pulse':
            status,message,self.vlc_sink = self.am.get_sink(self.vlc_audio)
            if status == 'error':
                self.mon.err(self,message)
                self.play_state='load-failed'
                if self.loaded_callback is not  None:
                    self.loaded_callback('error',message)
                    return
                    
            if not self.am.sink_connected(self.vlc_sink):
                self.mon.err(self,self.vlc_audio +' audio device not connected\n\n    sink: '+ self.vlc_sink)
                self.play_state='load-failed'
                if self.loaded_callback is not  None:
                    self.loaded_callback('error','audio device not connected')
                    return
        else:
            self.mon.err(self,'audio systems other than pulseaudio are not supported\n hint: audio.cfg error' )
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error','audio device not connected')
                return


        # do common bits of  load
        Player.pre_load(self) 
        
        # load the plugin, this may modify self.track and enable the plugin drawing to canvas
        if self.track_params['plugin'] != '':
            status,message=self.load_plugin()
            if status == 'error':
                self.mon.err(self,message)
                self.play_state='load-failed'
                if self.loaded_callback is not  None:
                    self.loaded_callback('error',message)
                    return

        # load the images and text
        status,message=self.load_x_content(enable_menu)
        if status == 'error':
            self.mon.err(self,message)
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error',message)
                return

        # check file exists if not a mrl
        if not ':'in track:        
            if not os.path.exists(track):
                    self.mon.err(self,"Track file not found: "+ track)
                    self.play_state='load-failed'
                    if self.loaded_callback is not  None:
                        self.loaded_callback('error','track file not found: '+ track)
                        return

        cmd= 'DISPLAY= python3 '+ self.pp_dir+'/pp_vlcdriver.py'
        #print (cmd)
        # need bash because of DISPLAY=
        self.vlcdriver = pexpect.spawn('/bin/bash', ['-c', cmd],encoding='utf-8')
        
        # get rid of driver start message
        start_message=self.vlcdriver.readline().strip('\r\n')
        if start_message != 'VLCDriver starting':
            self.mon.fatal(self,"VLCDriver failed\n Hint: sudo pip3 install python-vlc ")
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error','VLCDriver starting')
                return
        self.vlcdriver.setecho(False)

        self.vlcdriver.sendline('iopts'+self.iopts)
        self.vlcdriver.sendline('pauseopts'+self.pauseopts)
        self.vlcdriver.sendline('track '+track)

        # load the media
        self.vlcdriver.sendline('load')

        #get size of media, do after load and before play. Not used at the moment
        self.media_width,self.media_height=self.get_size()
        
        # calculate and send crop/aspect ratio and aspect mode. Done here as size might be needed in the future
        status,message=self.aspect_mode()
        if status !='normal':
            self.mon.err(self,message)
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error','track file not found: '+ track)
                return
                
        # play until pause at start
        self.vlcdriver.sendline('play')
        self.start_state_machine_load()



     # SHOW - show a track      
    def show(self,ready_callback,finished_callback,closed_callback):
        self.ready_callback=ready_callback         # callback when paused after load ready to show video
        self.finished_callback=finished_callback         # callback when finished showing
        self.closed_callback=closed_callback

        self.mon.trace(self,'')

        #  do animation at start and ready_callback
        Player.pre_show(self)

        # start show state machine
        self.start_state_machine_show()



    # UNLOAD - abort a load when vlcdriver is loading or loaded
    def unload(self):
        self.mon.trace(self,'')
        self.mon.log(self,">unload received from show Id: "+ str(self.show_id))
        self.start_state_machine_unload()


    # CLOSE - quits vlcdriver from 'pause at end' state
    def close(self,closed_callback):
        self.mon.trace(self,'')
        self.mon.log(self,">close received from show Id: "+ str(self.show_id))
        self.closed_callback=closed_callback
        self.start_state_machine_close()


    def get_size(self):
        self.vlcdriver.sendline('get-size')
        resp=self.vlcdriver.readline().strip('\r\n')
        resp_list=resp.split(' ')
        return resp_list[0],resp_list[1]
      

    def get_state(self):
        self.vlcdriver.sendline('t')
        resp=self.vlcdriver.readline().strip('\r\n')
        #print (resp)
        return resp


# ***********************
# track showing state machine
# **********************

    """
    STATES OF STATE MACHINE
    Threre are ongoing states and states that are set just before callback

    >init - Create an instance of the class
    <On return - state = initialised   -  - init has been completed, do not generate errors here

    >load
        Fatal errors should be detected in load. If so  loaded_callback is called with 'load-failed'
         Ongoing - state=loading - load called, waiting for load to complete   
    < loaded_callback with status = normal
         state=loaded - load has completed and video paused before or after first frame      
    <loaded_callback with status=error
        state= load-failed -  failure to load   

    On getting the loaded_callback with status=normal the track can be shown using show


    >show
        show assumes a track has been loaded and is paused.
       Ongoing - state=showing - video is showing 
    <finished_callback with status = pause_at_end
            state=showing but frozen_at_end is True
    <closed_callback with status= normal
            state = closed - video has ended vlc has terminated.


    On getting finished_callback with status=pause_at end a new track can be shown and then use close to close the previous video when new track is ready
    On getting closed_callback with status=  nice_day vlcdriver closing should not be attempted as it is already closed
    Do not generate user errors in Show. Only generate system errors such as illegal state and then use end()

    >close
       Ongoing state - closing - vlcdriver processes are dying
    <closed_callback with status= normal - vlcdriver is dead, can close the track instance.

    >unload
        Ongoing states - start_unload and unloading - vlcdriver processes are dying.
        when unloading is complete state=unloaded
        I have not added a callback to unload. its easy to add one if you want.

    closed is needed because wait_for_end in pp_show polls for closed and does not use closed_callback
    
    """


    def start_state_machine_load(self):
        # initialise all the state machine variables
        self.play_state='loading'
        #self.set_volume(self.volume)
        self.tick_timer=self.canvas.after(1, self.load_state_machine) #50
        
    def load_state_machine(self):
        if self.unload_signal is True:
            self.unload_signal=False
            self.state='unloading'
            self.vlcdriver.sendline('unload')
            self.root.after(100,self.load_state_machine)
        else:
            resp=self.get_state()
            # pp_vlcdriver changes state from load-loading when track is frozen at start.
            if resp == 'load-fail':
                self.play_state = 'load-failed'
                self.mon.log(self,"      Entering state : " + self.play_state + ' from show Id: '+ str(self.show_id))
                if self.loaded_callback is not  None:
                    self.loaded_callback('error','timeout when loading vlc track')
                return
            elif resp=='load-unloaded':
                self.play_state = 'unloaded'
                self.mon.log(self,"      Entering state : " + self.play_state + ' from show Id: '+ str(self.show_id))
                # PP does not need this callback
                #if self.loaded_callback is not  None:
                    #self.loaded_callback('normal','unloaded')
                return            
            elif resp=='load-ok':
                self.play_state = 'loaded'
                if self.vlc_sink!='':
                    self.set_device(self.vlc_sink)
                else:
                    self.set_device('')   
                self.set_volume(self.volume)
                self.mon.log(self,"      Entering state : " + self.play_state + ' from show Id: '+ str(self.show_id))
                if self.loaded_callback is not  None:
                    self.loaded_callback('normal','loaded')
                return
            else:
                self.root.after(10,self.load_state_machine) #100
            

    def start_state_machine_unload(self):
        # print ('videoplayer - starting unload',self.play_state)
        if self.play_state in('closed','initialised','unloaded'):
            # vlcdriver already closed
            self.play_state='unloaded'
            # print ' closed so no need to unload'
        else:
            if self.play_state  ==  'loaded':
                # load already complete so set unload signal and kick off load state machine
                self.play_state='start_unload'
                self.unload_signal=True
                self.tick_timer=self.canvas.after(50, self.load_state_machine)
                
            elif self.play_state == 'loading':
                # signal load state machine to start_unloading state and stop vlcdriver
                self.unload_signal=True
            else:
                self.mon.err(self,'illegal state in unload method: ' + self.play_state)
                self.end('error','illegal state in unload method: '+ self.play_state)           


            
    def start_state_machine_show(self):
        if self.play_state == 'loaded':
            # print '\nstart show state machine ' + self.play_state
            self.play_state='showing'
            self.freeze_signal=False     # signal that user has pressed stop
            self.must_quit_signal=False
            # show the track and content
            self.vlcdriver.sendline('show')
            self.mon.log (self,'>showing track from show Id: '+ str(self.show_id))  
            self.set_volume(self.volume)
            # and start polling for state changes
            # print 'start show state machine show'
            self.tick_timer=self.canvas.after(0, self.show_state_machine)
            """
            # race condition don't start state machine as unload in progress
            elif self.play_state == 'start_unload':
                pass
            """
        else:
            self.mon.fatal(self,'illegal state in show method ' + self.play_state)
            self.play_state='show-failed'
            if self.finished_callback is not None:
                self.finished_callback('error','illegal state in show method: ' + self.play_state)


    def show_state_machine(self):
        if self.play_state=='showing':
            if self.quit_signal is True:
                # service any queued stop signals by sending stop to vlcdriver
                self.quit_signal=False
                self.mon.log(self,"      stop video - Send stop to vlcdriver")
                self.vlcdriver.sendline('stop')
                self.tick_timer=self.canvas.after(10, self.show_state_machine)
            else:
                resp=self.get_state()
                #print (resp)
                # driver changes state from show-showing depending on freeze-at-end.
                if resp == 'show-pauseatend':
                    self.mon.log(self,'vlcdriver says pause_at_end')
                    self.frozen_at_end=True
                    if self.finished_callback is not None:
                        self.finished_callback('pause_at_end','pause at end')
                        
                elif resp == 'show-niceday':
                    self.mon.log(self,'vlcdriver says nice_day')
                    self.play_state='closing'
                    self.vlcdriver.sendline('close')
                    # and terminate the vlcdriver process through pexpect
                    self.vlcdriver.terminate()
                    self.tick_timer=self.canvas.after(10, self.show_state_machine)
                                        
                elif resp=='show-fail':
                    self.play_state='show-failed'
                    if self.finished_callback is not None:
                        self.finished_callback('error','pp_vlcdriver says show failed: '+ self.play_state)
                else:
                    self.tick_timer=self.canvas.after(30,self.show_state_machine)
                    
        elif self.play_state=='closing':
            # close the pexpect process
            self.vlcdriver.close()
            self.play_state='closed'
            # state change needed for wait for end
            self.mon.log(self,"      Entering state : " + self.play_state + ' from show Id: '+ str(self.show_id))
            if self.closed_callback is not  None:
                self.closed_callback('normal','vlcdriver closed')             

    # respond to normal stop
    def stop(self):
        self.mon.log(self,">stop received from show Id: "+ str(self.show_id))
        # cancel the pause timer
        if self.pause_timer != None:
            self.canvas.after_cancel(self.pause_timer)
            self.pause_timer=None
        self.vlcdriver.sendline('stop')


    def start_state_machine_close(self):
        # self.mon.log(self,">close received from show Id: "+ str(self.show_id))
        # cancel the pause timer
        if self.pause_timer != None:
            self.canvas.after_cancel(self.pause_timer)
            self.pause_timer=None
        self.vlcdriver.sendline('close')
        self.play_state='closing'
        #print ('start close state machine close')
        self.tick_timer=self.canvas.after(0, self.show_state_machine)



# ************************
# COMMANDS
# ************************

    def input_pressed(self,symbol):
        if symbol == 'inc-volume':
            self.inc_volume()
        elif symbol == 'dec-volume':
            self.dec_volume()            
        elif symbol  == 'pause':
            self.pause()
        elif symbol  == 'go':
            self.go()
        elif symbol  == 'unmute':
            self.unmute()
        elif symbol  == 'mute':
            self.mute()
        elif symbol  == 'pause-on':
            self.pause_on()    
        elif symbol  == 'pause-off':
            self.pause_off()
        elif symbol == 'stop':
            self.stop()


    def inc_volume(self):
        self.mon.log(self,">inc-volume received from show Id: "+ str(self.show_id))
        if self.play_state  == 'showing':
            if self.volume < self.max_volume:
                self.volume+=1
            self.set_volume(self.volume)
            return True
        else:
            self.mon.log(self,"!<inc-volume rejected " + self.play_state)
            return False

    def dec_volume(self):
        self.mon.log(self,">dec-volume received from show Id: "+ str(self.show_id))

        if self.play_state  == 'showing':
            if self.volume > 0:
                self.volume-=1
            self.set_volume(self.volume)
            return True
        else:
            self.mon.log(self,"!<dec-volume rejected " + self.play_state)
            return False

    def set_volume(self,vol):
        # print ('SET VOLUME',vol)
        self.vlcdriver.sendline('vol '+ str(vol))
        
    def set_device(self,device):
        self.vlcdriver.sendline('device '+ device)

    def mute(self):
        self.mon.log(self,">mute received from show Id: "+ str(self.show_id))
        self.vlcdriver.sendline('mute')
        return True        
                

    def unmute(self):
        self.mon.log(self,">unmute received from show Id: "+ str(self.show_id))
        self.vlcdriver.sendline('unmute')


    # toggle pause
    def pause(self):
        self.mon.log(self,">toggle pause received from show Id: "+ str(self.show_id))
        self.vlcdriver.sendline('pause')
        reply=self.vlcdriver.readline().strip('\r\n')
        if reply == 'pause-on-ok':
            if self.pause_timeout>0:
                # kick off the pause timeout timer
                self.pause_timer=self.canvas.after(self.pause_timeout*1000,self.pause_timeout_callback)
            return True
        elif reply == 'pause-off-ok':
            if self.pause_timer != None:
                # cancel the pause timer
                self.canvas.after_cancel(self.pause_timer)
                self.pause_timer=None
            return True
        else:
            self.mon.log(self,"!<toggle pause rejected " + self.play_state)
            return False              
            

    def pause_timeout_callback(self):
        self.pause_off()
        self.pause_timer=None

    # pause on
    def pause_on(self):
        self.mon.log(self,">pause on received from show Id: "+ str(self.show_id))
        self.vlcdriver.sendline('pause-on')
        reply=self.vlcdriver.readline().strip('\r\n')
        if reply == 'pause-on-ok':
            if self.pause_timeout>0:
                # kick off the pause timeout timer
                self.pause_timer=self.canvas.after(self.pause_timeout*1000,self.pause_timeout_callback)
            return True
        else:
            self.mon.log(self,"!<pause on rejected " + self.play_state)
            return False

    # pause off
    def pause_off(self):
        self.mon.log(self,">pause off received from show Id: "+ str(self.show_id))
        self.vlcdriver.sendline('pause-off')
        reply=self.vlcdriver.readline().strip('\r\n')
        if reply == 'pause-off-ok':
            if self.pause_timer != None:
                # cancel the pause timer
                self.canvas.after_cancel(self.pause_timer)
                self.pause_timer=None
            return True
        else:
            self.mon.log(self,"!<pause off rejected " + self.play_state)
            return False

    # go after freeze at start
    def go(self):
        self.vlcdriver.sendline('go')
        reply=self.vlcdriver.readline().strip('\r\n')
        if reply == 'go-ok':
            return True
        else:
            self.mon.log(self,"!<go rejected " + self.play_state)
            return False


# *****************************
# SETUP
# *****************************

    def process_params(self):
            
        # volume will be set during show by set_volume()
        # --------------------------------------
        if self.vlc_max_volume_text != "":
            if not self.vlc_max_volume_text.isdigit():
                return 'error','VLC Max Volume must be a positive integer: '+self.vlc_max_volume_text
            self.max_volume= int(self.vlc_max_volume_text)
            if self.max_volume>100:
                return 'error','VLC Max Volume must be <= 100: '+ self.vlc_max_volume_text                
        else:
            self.max_volume=100
            
        if self.vlc_volume_text != "":
            if not self.vlc_volume_text.isdigit():
                return 'error','VLC Volume must be a positive integer: '+self.vlc_volume_text
            self.volume= int(self.vlc_volume_text)
            if self.volume>100:
                return 'error','VLC Volume must be <= 100: '+self.vlc_max_volume_text  
        else:
            self.volume=100
            
        self.volume=min(self.volume,self.max_volume)


        # instance options
        # ----------------
        
        #audio system - pulseaudio
        audio_opt= '--aout=pulse '
        
        # other options
        if self.vlc_other_options!='':
            other_opts = self.vlc_other_options+' '
        else:
            other_opts=''
        
        # subtitles
        if self.vlc_subtitles !='yes':
            subtitle_opt='--no-spu '
        else:
            subtitle_opt=''

 
        # display
        # -------
        # start with board name
        if self.track_params['display-name'] != "":
            video_display_name = self.track_params['display-name']
        else:
            video_display_name = self.show_canvas_display_name
        # Is it valid and connected
        status,message,self.display_id=self.dm.id_of_display(video_display_name)
        if status == 'error':
            return 'error',message
            
        #convert to task bar names for vlc
        vlc_display_name=self.dm.vlc_display_name_map[video_display_name]

        display_opt='--mmal-display='+vlc_display_name +' '
        # does it do DSI-1????
        
        # layer
        # ******
        if self.vlc_layer_text=='':
            layer_opt=''
        elif self.vlc_layer_text=='hidden':
                layer_opt='--mmal-layer=-128 '
        else:
            if not self.vlc_layer_text.isdigit():
                return 'error','Display Layer is not a positive number: '+self.vlc_layer_text
            layer_opt='--mmal-layer='+self.vlc_layer_text +' '

        # image duration
        # **************
        if not self.vlc_image_duration_text.isdigit():
            return 'error','Image Duration is not a positive number: '+ self.vlc_image_duration_text
        if int(self.vlc_image_duration_text)==0:
            image_duration_opt='--image-duration -1 '
        else:
            image_duration_opt='--image-duration '+ self.vlc_image_duration_text+ ' '
        
        # video window
        # ************
        # parse video window and mangle wxh+x+y string for aspect_mode
        status,message,window_text= self.parse_vlc_video_window(self.vlc_window_text)
        if status  == 'error':
            return 'error',message

        if window_text !='':
            window_opt= '--mmal-vout-window '+ window_text +' '
        else:
            window_opt=''


        # transformation
        # ***************
        # model other than 4 video is rotated by hdmi_display_rotate in config.txt
        if self.dm.model_of_pi() == 4:
            rotation= self.dm.real_display_orientation(self.display_id)
        else:
            rotation = 'normal'
            
        if rotation == 'normal':
            transform_opt=' --mmal-vout-transform=0 '            
        elif rotation == 'right':
            transform_opt=' --mmal-vout-transform=90 '
        elif rotation =='left':
            transform_opt=' --mmal-vout-transform=270 '
        else:
            #inverted
            transform_opt=' --mmal-vout-transform=180 '
            
        
        self.iopts=' '+window_opt+layer_opt+display_opt+transform_opt+subtitle_opt +audio_opt + image_duration_opt + other_opts


        # pause options
        #---------------
        
        if self.freeze_at_end_text == 'yes':
            self.freeze_at_end_required=True
        else:
            self.freeze_at_end_required=False
        
        freeze_start_opt=' '+self.freeze_at_start_text
        freeze_end_opt=' '+self.freeze_at_end_text
        
        self.pauseopts= freeze_start_opt+freeze_end_opt
        
        return 'normal',''
        

    def aspect_mode(self):

        """
        In omxplayer Video Window has parameters only for warp, all other modes are centred the full screen

        In vlcplayer there are two fields, VLC Window and Aspect Mode. VLC Window position and sizes the window then
        Aspect Mode is applied to all results of VLC Window :
        
        stretch - transform video to make it fill the window with aspect ratio the same as the window

        fill - crop the video so that it fills the window while retaining the video's aspect ratio

        letterbox - vlc's default mode
                        adjust the video  so that whole video is seen in the window while keeping the video's aspect ratio
                        If the window's aspect ratio does not match that of the video media then the x,y, position will be incorrect,
                        (except on fullscreen). This is because the result is centred in the window.


        vlc - use vlc's aspect ratio and crop in the defined window
            Cannot use both crop and aspect ratio
            window size w*h needs to have the same ratio as the result of crop or aspect-ratio otherwise the displayed position will be incorrect
            values must be integers e.g 5.1:1 does not work 
            crop formats:    <aspect_num>:<aspect_den> e.g.4:3
                            <width>x<height>+<x>+<y>
                            <left>+<top>+<right>+<bottom>
            aspect ratio formats: <aspect_num>:<aspect_den> e.g.4:3
        """
        if self.vlc_aspect_mode == 'stretch':
            window_ratio=self.vlc_window_width/self.vlc_window_height
            self.vlcdriver.sendline('ratio '+ str(self.vlc_window_width)+':'+str(self.vlc_window_height))
            return 'normal',''
            
        elif self.vlc_aspect_mode == 'fill':
            self.vlcdriver.sendline('crop '+ str(self.vlc_window_width)+':'+str(self.vlc_window_height))
            return 'normal',''
            
        elif self.vlc_aspect_mode == 'letterbox':
            # default vlc behavior
            return 'normal',''
            
        elif self.vlc_aspect_mode == 'vlc':
            if self.vlc_aspect_ratio != '' or self.vlc_crop!= '':
                if self.vlc_crop!= '':
                    self.vlcdriver.sendline('crop '+ self.vlc_crop)
                    
                if self.vlc_aspect_ratio != '':
                    self.vlcdriver.sendline('ratio '+ self.vlc_aspect_ratio)
                return 'normal',''
            else:
                return 'error', 'crop or aspect mode not specified for vlc option'
        else:
            return 'error','Aspect Mode cannot be blank '+ self.vlc_aspect_mode


    def parse_vlc_video_window(self,line):
        words=line.split()
        if len(words) not in (1,2):
            return 'error','bad vlc video window form '+line,''
            
        if words[0] not in ('display','showcanvas'):
            return 'error','Bad VLC Window option: '+line,''
            

        if words[0] == 'display':
            x_org=0
            y_org=0
            width,height= self.dm.canvas_dimensions(self.display_id)
            
        if words[0] == 'showcanvas':
            x_org=self.show_canvas_x1
            y_org= self.show_canvas_y1
            width=self.show_canvas_width
            height=self.show_canvas_height

        #replace canvas/display height/width from spec
        x_offset=0
        y_offset=0
        if len(words)==2:
            #pass in canvas/display width/height. Returns window width/height
            status,message,x_offset,y_offset,width,height=self.parse_dimensions(words[1],width,height)
            if status =='error':
                return 'error',message,''
                
        x= x_org+x_offset
        y= y_org+y_offset
        self.vlc_window_x=x
        self.vlc_window_y=y
        self.vlc_window_width=width
        self.vlc_window_height=height
        vlc_text=str(width)+'x'+str(height)+'+'+str(x)+'+'+str(y)
        return 'normal','',vlc_text
            
          
            
    def parse_dimensions(self,dim_text,show_width,show_height):
        # parse x+y+width*height or width*height
        if '+' in dim_text:
            # x+y+width*height
            fields=dim_text.split('+')
            if len(fields) != 3:
                return 'error','bad vlc video window form '+dim_text,0,0,0,0

            if not fields[0].isdigit():
                return 'error','x value is not a positive decimal in vlc video window '+dim_text,0,0,0,0
            else:
                x=int(fields[0])
            
            if not fields[1].isdigit():
                return 'error','y value is not a positive decimal in vlc video window '+dim_text,0,0,0,0
            else:
                y=int(fields[1])

            dimensions=fields[2].split('*')
            if len(dimensions)!=2:
                return 'error','bad vlc video window dimensions '+dim_text,0,0,0,0
                
            if not dimensions[0].isdigit():
                return 'error','width is not a positive decimal in vlc video window '+dim_text,0,0,0,0
            else:
                width=int(dimensions[0])
                
            if not dimensions[1].isdigit():
                return 'error','height is not a positive decimal in vlc video window '+dim_text,0,0,0,0
            else:
                height=int(dimensions[1])

            return 'normal','',x,y,width,height
        else:
            dimensions=dim_text.split('*')
            if len(dimensions)!=2:
                return 'error','bad vlc video window dimensions '+dim_text,0,0,0,0
                
            if not dimensions[0].isdigit():
                return 'error','width is not a positive decimal in vlc video window '+dim_text,0,0,0,0
            else:
                window_width=int(dimensions[0])
                
            if not dimensions[1].isdigit():
                return 'error','height is not a positive decimal in vlc video window '+dim_text,0,0,0,0
            else:
                window_height=int(dimensions[1])
                
            x=int((show_width-window_width)/2)
            y=int((show_height-window_height)/2)
            return 'normal','',x,y,window_width,window_height


class CLI(object):
    
    """
    # Tests vlcdriver and the pexpect interface by
    # allowing commands to be sent by the user
    # commands are as in vlcdriver.py without Return

    # PP would call _init_ load,show, and close/quit 
    # If no parameters are sent using iopts and pauseopts aspectopt cropopt commands then the defaults in vlcdrive.py are used
    # track must be the full path to file. If no track command is sent then the default track in vlcdrive.py is used
    """
            
    def __init__(self):
        self.work_dir=sys.path[0]
        # start the vlc driver which waits for commands
        cmd= 'DISPLAY= python3 '+ self.work_dir+'/pp_vlcdriver.py'
        # need bash because of DISPLAY=
        self.vlcdrive = pexpect.spawn('/bin/bash', ['-c', cmd],encoding='utf-8')
        
        # print the start message read from the driver
        sm=self.vlcdrive.readline()
        print('Start Message: ' + sm)
        #stop pexpect echoing the command
        self.vlcdrive.setecho(False) 

        while True:
            x=input('>:')
            self.do_command(x)
        
    def do_command(self,cmd):
        cmd_list= cmd.split(' ', 1)
        if len(cmd_list)==1:
            if cmd == 't':
                # print state of track playing
                self.vlcdrive.sendline('t')
                print(self.vlcdrive.readline(),end="")
                
            elif cmd in ('load','play','show','unload','stop'):
                self.vlcdrive.sendline(cmd)
                
            elif cmd==('get-size','pause','pause-on','pause-off','go'):
                self.vlcdrive.sendline(cmd)
                print (self.vlcdrive.readline())
                                
            elif cmd == 'close':
                self.vlcdrive.sendline('close')            
                exit(0)
            else:
                print ('bad command')
        else:
            cmd_bit, parameters = cmd.split(' ', 1)
            #print (cmd_bit,parameters)
            if cmd_bit in ('iopts','pauseopts','track','vol','ratio','crop','device'):
                self.vlcdrive.sendline(cmd) 
            else:
                print ('bad command')



if __name__ == '__main__':

    # command line utility to test pp_vlcdriver.py and pexpect interface  
    cc=CLI()
