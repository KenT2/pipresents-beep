"""
pp_vlcdriver.py

API for vlc which allows vlc to be controlled by libvlc when using the Pi's --vout mm-vout display driver
while at the same time inhibiting VLC's extraneous x-window based video window.

python bindings for libvlc are here http://www.olivieraubert.net/vlc/python-ctypes/doc/

USE

The driver has a command line interface, either type commands into terminal or use pp_vlcplayer.py
which accesses the interface through pexpect.
After the start message line there is no prompt, type the command followed by return.

commands
ipots - supply a set of options for a VLC instance iopts <option> <option> .......
popts - pause options   popts <pause-at-start>  <pause-at-end> 
        pause-at-start before-first-frame/after-first-frame/no - pause before or after first frame
        pause-at-end  yes/no   - pause before last frame or run on to track is finished.
track - path of track to play track <full track path>

Initial state is idle, this is altered by the commands

load - start VLC and obtain the media. Returns when the media is obtained.

get-size - optionally use this command between load and play to obtain the dimensions of the media 

play - complete loading a track and then run to start as in popts. Load is non-blocking and returns immeadiately. To determine load is complete poll using the t command to obtain the state
    load-loading - load in progress
    load-ok - loading complete and ok
    load-fail

show - show a track that has been loaded. Show is non-blocking and returns immeadiately. To determine showing is complete poll using the t command to obtain the state
    show-showing - showing in progress
    show-pauseatend - paused before last frame - does not respond to stop or unpause, use close
    show-niceday - track has ended, stop then close commands required to shut process down
    show-fail
    
stop - stops showing. To determine if complete poll state for: 
      show-niceday

unload - stops loading. To determine if complete poll state for:
      load-unloaded

close - exits vlc and exits pp_vlcdriver.py
    
t - get the current state of loading/showing. Returns a single line with one of the above values

vol - set the volume between 0 and 100. Use only when showing  vol <volume>
      
ratio - set video ratio
crop - set video crop
set-device - set audio device
pause/ unpause - pauses the track
mute/unmute - mute without changing volume

"""

import time
import threading
import sys,os
import vlc #sudo pip3 install python-vlc


class VLCDriver(object):
    
    # used first time and for every other instance
    def __init__(self):
        self.work_dir=sys.path[0]
        self.logger=Logger()
        self.logger.log('init VLC instance')
        self.quit_load_signal=False
        self.quit_show_signal=False
        self.instance_options=' --mmal-layer=1 --mmal-vout-window 400x300+100+100 --mmal-vout-transparent --aout=pulse --mmal-display=HDMI-1 '         # obtained from iopts command, just a test set
        self.player_options=''            #options for mediaplayer, none required
        self.instance_mandatory=' --quiet --no-xlib --vout mmal_vout --mmal-vout-transparent '   #mandatory set of options

        self.track_path= '/home/pi/pp_home/media/5sec.mp4'   #test track to play
        self.freeze_at_start='no'       #test value, normally obtained from pauseopts command
        self.freeze_at_end='yes'           #test value, normally obtained from pauseopts command
        self.show_status_thread=None
        self.load_status_thread=None
        self.volume=100
        self.state='idle'
        self.user_pause=False
        self.frozen_at_start=False
        self.frozen_at_end=False
        self.player=None
        self.vlc_instance=None


    def load(self):
        
        self.state='load-loading'


        if self.freeze_at_end=='yes':
            freezeopt='--play-and-pause '
        else:
            freezeopt=''
            
            
        # create a vlc instance
        options=self.instance_mandatory+freezeopt+self.instance_options
        self.logger.log('Instance Options: ',options)       
        self.vlc_instance = vlc.Instance(options)
        
        #print ('enumerate devices',self.vlc_instance.audio_output_enumerate_devices())
        #print ('device list',self.vlc_instance.audio_output_device_list_get('pulse'))

        # get the media and obtain its length
        self.media = self.vlc_instance.media_new(self.track_path)
        self.media.parse()
        self.length=self.media.get_duration()
        self.logger.log ('track length',self.length)
        
        #create mediaplayer instance
        self.player = vlc.MediaPlayer(self.vlc_instance,'',self.player_options)
        #self.set_volume(0)
        #print ('player device enum',self.player.audio_output_device_enum())
        self.player.set_media(self.media)
        return

    def set_crop(self,crop):
        if crop !='':
            self.player.video_set_crop_geometry(crop)
        
    def set_aspect_ratio(self,ratio):
        if ratio !='':
            self.player.video_set_aspect_ratio(ratio)


    # between load and play you can read the dimensions of the media (get_size())
        
    def play(self):
        
        self.player.play()
        
        #calculate position for freeze at start
        # no  - pauses after play() before the first frame, show then unpauses
        # before/after  - pauses after play() as required. Show does not unpause, go command does.
        if self.freeze_at_start in ('no','before-first-frame'):
            # before first frame, pause when first 0 get_time() report followed by n zeros is received
            self.load_pause_position=-1
            self.zero_count= 2         #2 was released
            
        if self.freeze_at_start=='after-first-frame':
            # after first frame, when get_time() > 0 allowing for sampling rate.
            self.load_pause_position = 200 #mS
            self.zero_count=-1    #do not use it for after first frame
        
        #monitor the loading of the track using a thread so can receive commands during the load
        self.load_status_thread= threading.Thread(target=self.load_status_loop)
        self.load_status_thread.start()
        return



    def load_status_loop(self):
        # wait until the load is complete
        #need a timeout as sometimes a load will fail 
        timeout= 500   #5 seconds released 500

        while True:
            if self.quit_load_signal is True:
                self.quit_load_signal=False
                self.player.stop() 
                self.state= 'load-unloaded'
                self.logger.log ('unloaded at: ',position)
                return
                
            position=self.player.get_time()
            #self.logger.log('loading',self.state,position,self.zero_count)
            if position > self.load_pause_position and self.zero_count<0: #milliseconds
                self.player.set_pause(True)
                self.frozen_at_start=True
                self.logger.log ('track frozen at start at: ',position,self.zero_count)
                self.state='load-ok'
                self.logger.log ('load-ok at: ',position)
                return
                
            timeout-=1
            if timeout <=0:
                self.logger.log ('load failed at: ',position)
                self.state='load-fail'
                return
            else:
                # first frame does not appear until after a number of 0 position frames, get close as possible
                if position ==0:
                    self.zero_count-=1
                time.sleep(0.01)


    def show(self):
        if self.freeze_at_start == 'no':
            self.state='show-showing'
            self.player.set_pause(False)
            self.logger.log ('freeze off, start showing')
            self.show_status_thread=threading.Thread(target=self.show_status_loop)
            self.show_status_thread.start()
        return
        
    def go(self):
        if self.frozen_at_start is True:
            self.player.set_pause(False)
            self.state='show-showing'
            self.logger.log ('freeze off, go ok')
            self.show_status_thread=threading.Thread(target=self.show_status_loop)
            self.show_status_thread.start()
            return 'go-ok'
        else:
            self.logger.log ('go rejected')
            return 'go-reject'
    
 
    def show_status_loop(self):
        self.logger.log ('show loop start')
        # wait for initial unpause to take effect. Seems to be required for images
        while self.player.get_state() == vlc.State.Paused:
            #self.logger.log('wait 10mS for unpause')
            time.sleep(0.01)
        self.frozen_at_start=False
        while True:
            if self.quit_show_signal is True:
                self.quit_show_signal= False
                if self.freeze_at_end == 'yes':
                    self.frozen_at_end=True
                    self.player.set_pause(True)
                    self.state='show-pauseatend'
                    self.logger.log('stop caused pause',self.state)
                    return
                else:
                    self.player.stop()
                    self.state='show-niceday'
                    self.logger.log('stop caused no pause',self.state)
                    return
            #cope with image with --image-duration (no end) = -1 which yields 0 length
            if self.length==0:
                time.sleep(0.1)
            else:
                #position=self.player.get_time()
                #self.logger.log('track time',self.freeze_at_end,self.length,position,self.player.get_state())

                # when using --play-and-pause option VLC pauses on the last frame into a funny state.
                if self.freeze_at_end == 'yes':
                    #self.logger.log('before',self.state)
                    if self.user_pause is False and self.player.get_state() == vlc.State.Paused:
                        # in this state VLC does not respond to stop or unpause, only close
                        self.frozen_at_end=True
                        #self.logger.log ('paused at end at')
                        self.state='show-pauseatend'
                        return
                    else:
                        #self.logger.log('after',self.state)
                        time.sleep(0.03)
                else:
                    #self.logger.log('before',self.state)
                    if self.freeze_at_end == 'no':
                        if self.player.get_state() == vlc.State.Ended:
                            self.player.stop()
                            self.logger.log ('ended with no pause')
                            self.state='show-niceday'
                            return
                        else:
                            #self.logger.log('after',self.state)
                            time.sleep(0.03)
                    else:
                        self.logger.log( 'illegal freeze at end')
                    


# ***********************
# Commands
# ***********************
        
    def get_state(self):
        return self.state
        
    def get_size(self):
        w,h=self.player.video_get_size(0)
        return str(w)+' '+str(h)
        
    def pause(self):
        if self.state== 'show-showing' and self.frozen_at_end is False and self.frozen_at_start is False:
            if self.user_pause is True:
                self.player.set_pause(False)
                self.user_pause=False
                self.logger.log ('pause to pause-off ok')
                return 'pause-off-ok'
            else:
                self.user_pause=True
                self.player.set_pause(True)
                self.logger.log ('pause to pause-on ok')
                return 'pause-on-ok'
        else:
            self.logger.log ('pause rejected')
            return 'pause-reject'


    def pause_on(self):
        if self.state== 'show-showing' and self.frozen_at_end is False and self.frozen_at_start is False:
            self.user_pause=True
            self.player.set_pause(True)
            self.logger.log ('pause on ok')
            return 'pause-on-ok'
        else:
            self.logger.log ('pause on rejected')
            return 'pause-on-reject'
            
                    
    def pause_off(self):
        if self.state== 'show-showing' and self.frozen_at_end is False and self.frozen_at_start is False:
            self.player.set_pause(False)
            self.user_pause=False
            self.logger.log ('pause off ok')
            return 'pause-off-ok'
        else:
            return 'pause-off-reject'

    def stop(self):
        if self.frozen_at_start is True:
            self.player.stop()
            self.state='stop-frozen'
            self.logger.log('stop during frozen at start',self.state)
            return
        else:
            self.quit_show_signal=True
            return

    def close(self):
        self.player.stop()
        if self.load_status_thread != None:
            self.load_status_thread.join()
        if self.show_status_thread != None:
            self.show_status_thread.join()
        if self.player != None:
            self.player.release()
            self.player=None
        if self.vlc_instance !=None:
            self.vlc_instance.release()
            self.vlc_instance=None        
        
    def unload(self):
        if self.state=='load-loading':
            self.quit_load_signal=True
        else:
            self.state='load-unloaded'

    def mute(self):
        self.player.audio_set_mute(True)
        
    def unmute(self):
        self.player.audio_set_mute(False)
                
    def set_volume(self,volume):
        self.player.audio_set_volume(volume)        

    def set_device(self,device_id):
        if device_id=='':
            self.player.audio_output_device_set(None,None) 
        else:           
            self.player.audio_output_device_set(None,device_id)
        
class  Logger(object): 

# -------------------------------
# logging - log-file opened in init
# ------------------------------- 

    def init(self):
        tfile=open(self.work_dir+'/pp_logs/vlcdriver_time.txt','w')
        tfile.write(str(time.time()))
        tfile.close()
        return 

    # control logging here
    def __init__(self,enabled=False):
        self.enabled=enabled
        self.work_dir=sys.path[0]
        self.log_file=open(self.work_dir+'/pp_logs/vlcdriver_log.txt','a')
        self.id=str(int(time.time()%10000000))
        # READ START TIME
        if os.path.exists(self.work_dir+'/pp_logs/vlcdriver_time.txt'):
            tfile=open(self.work_dir+'/pp_logs/vlcdriver_time.txt','r')
            self.start_time=float(tfile.readline())


    def log(self,*args):
        if not self.enabled:
            return
        al=[]
        for arg in args:
            string_arg=str(arg)
            al.append(string_arg)
        text=' '.join(al)
        #.strftime("%A %d %B %Y %I:%M:%S%p")
        time_str="{:.6f}".format(time.time()-self.start_time)
        #print(time_str,text)
        self.log_file.write(time_str+ '  ' +self.id+'     ' + text + '\n')
        self.log_file.flush()

    def close(self):
        self.log_file.close()


class CLI(object):

    def __init__(self):
        self.logger=Logger()
        self.work_dir=sys.path[0]
        self.vv=VLCDriver()


    def cli_loop(self):
        if 'vlc' in sys.modules:
            print ('VLCDriver starting')
        else:
            print ('sudo pip3 install python-vlc')
        while True:
            cmd= input()
            cmd_list= cmd.split(' ', 1)
            if len(cmd_list)==1:
                if cmd !='t':
                    self.logger.log ('Command: ',cmd) #don't log  state requests
                if cmd == 't':
                    print (self.vv.get_state())   #send state back to pp_vlcplayer
                elif cmd == 'load':
                    self.vv.load()
                elif cmd == 'play':
                    self.vv.play()
                elif cmd== 'show':
                    self.vv.show()
                elif cmd == 'stop':
                    self.vv.stop()
                elif cmd== 'unload':
                    self.vv.unload()           
                elif cmd== 'close':
                    self.logger.close()
                    exit(0)
                elif cmd=='go':
                    print(self.vv.go())
                elif cmd=='pause':
                    print(self.vv.pause())
                elif cmd=='pause-on':
                    print(self.vv.pause_on())
                elif cmd=='pause-off':
                    print(self.vv.pause_off())
                elif cmd=='mute':
                    self.vv.mute()
                elif cmd=='unmute':
                    self.vv.unmute()
                elif cmd == 'get-size':
                    size=self.vv.get_size()
                    self.logger.log ('Size:',size)
                    print (size)
                else:
                    self.logger.log('bad-command',cmd)
            else:
                cmd_bit, parameters = cmd.split(' ', 1)
                if cmd_bit=='iopts':
                    self.vv.instance_options=' '+parameters
                    self.logger.log ('iopts: ',parameters)
                elif cmd_bit=='track':
                    self.vv.track_path=parameters
                    self.logger.log ('track: ',parameters)
                elif cmd_bit=='pauseopts':
                    self.vv.freeze_at_start,self.vv.freeze_at_end=parameters.split(' ')
                    self.logger.log ('pauseopts: ',parameters)
                elif cmd_bit=='ratio':
                    self.vv.set_aspect_ratio(parameters)
                    self.logger.log ('set ratio: ',parameters)
                elif cmd_bit=='crop':
                    self.vv.set_crop(parameters)
                    self.logger.log ('crop: ',parameters)
                elif cmd_bit=='vol':
                    self.vv.set_volume(int(parameters))
                    self.logger.log ('vol: ',parameters)
                elif cmd_bit=='device':
                    self.vv.set_device(parameters)
                    self.logger.log ('device: ',parameters)
                else:
                    self.logger.log('bad-command',cmd)



if __name__ == '__main__':    
    cc=CLI()
    cc.cli_loop()



  
    

    

