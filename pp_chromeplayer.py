#sudo apt install selenium
#sudo apt install chromium-chromedriver

import os
import copy
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options 
from pp_player import Player
from pp_displaymanager import DisplayManager


class ChromePlayer(Player):

# ***************************************
# EXTERNAL COMMANDS
# ***************************************

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
        
        # and initialise things for this player        
        self.dm=DisplayManager()
        
        # get duration limit (secs ) from profile
        if self.track_params['duration'] != '':
            self.duration= int(self.track_params['duration'])
        else:
            self.duration= int(self.show_params['duration'])
        self.duration_limit=20*self.duration

        # process web window                  
        if self.track_params['chrome-window'] != '':
            self.chrome_window_text= self.track_params['chrome-window']
        else:
            self.chrome_window_text= self.show_params['chrome-window']

        # process web window                  
        if self.track_params['chrome-freeze-at-end'] != '':
            self.freeze_at_end= self.track_params['chrome-freeze-at-end']
        else:
            self.freeze_at_end= self.show_params['chrome-freeze-at-end']
       
        if self.track_params['chrome-zoom'] != '':
            self.chrome_zoom_text= self.track_params['chrome-zoom']
        else:
            self.chrome_zoom_text= self.show_params['chrome-zoom']

        if self.track_params['chrome-other-options'] != '':
            self.chrome_other_options= self.track_params['chrome-other-options']
        else:
            self.chrome_other_options= self.show_params['chrome-other-options']

        # Initialize variables
        self.command_timer=None
        self.tick_timer=None
        self.quit_signal=False     # signal that user has pressed stop
        
        # initialise the play state
        self.play_state='initialised'
        self.load_state=''


    # LOAD - loads the browser and show stuff
    def load(self,track,loaded_callback,enable_menu):  
        # instantiate arguments
        self.loaded_callback=loaded_callback   # callback when loaded
        self.mon.trace(self,'')


        # Is display valid and connected
        status,message,self.display_id=self.dm.id_of_display(self.show_canvas_display_name)
        if status == 'error':
            self.mon.err(self,message)
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error','cannot find file; '+track )
                return



        # does media exist    
        if not ':' in track:
            if not os.path.exists(track):
                self.mon.err(self, 'cannot find file; '+track )
                self.play_state='load-failed'
                if self.loaded_callback is not  None:
                    self.loaded_callback('error','cannot find file; '+track )
                    return
                    
        # add file:// to files.
        if ':' in track:
            self.current_url=track
        else:
            self.current_url='file://'+track
        print ('start',self.current_url)
        # do common bits of  load
        Player.pre_load(self)
        
        # prepare chromium options
        status,message=self.process_chrome_options()
        if status == 'error':
            self.mon.err(self, message)
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error',message)
                return
                
        print ('after options',self.current_url)
                     
        # parse browser commands to self.command_list
        reason,message=self.parse_commands(self.track_params['browser-commands'])
        if reason == 'error':
            self.mon.err(self,message)
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error',message)
                return


        # load the plugin, this may modify self.track and enable the plugin drawing to canvas
        if self.track_params['plugin'] != '':
            status,message=self.load_plugin()
            if status == 'error':
                self.mon.err(self,message)
                self.play_state='load-failed'
                if self.loaded_callback is not  None:
                    self.loaded_callback('error',message)
                    return

        # start loading the browser
        self.play_state='loading'
        print ('loading',self.current_url,self.app_mode)


        # load the images and text
        status,message=self.load_x_content(enable_menu)
        if status == 'error':
            self.mon.err(self,message)
            self.play_state='load-failed'
            if self.loaded_callback is not  None:
                self.loaded_callback('error',message)
                return

        #start the browser
        self.driver_open()

        # for kiosk and fullscreen need to get the url - in browser command for app mode
        if self.app_mode is False:
            self.driver_get(self.current_url) 
        self.mon.log (self,'Loading browser from show Id: '+ str(self.show_id))
                
        self.play_state='loaded'
        
        # and start executing the browser commands
        self.play_commands()
        self.mon.log(self,"      State machine: chromium loaded")
        if self.loaded_callback is not None:
            self.loaded_callback('normal','browser loaded')
        return



    # UNLOAD - abort a load when browser is loading or loaded
    def unload(self):
        self.mon.trace(self,'')
        self.mon.log(self,">unload received from show Id: "+ str(self.show_id))
        self.driver_close()
        self.play_state = 'closed'


         
     # SHOW - show a track from its loaded state 
    def show(self,ready_callback,finished_callback,closed_callback):
                         
        # instantiate arguments
        self.ready_callback=ready_callback         # callback when ready to show a web page- 
        self.finished_callback=finished_callback         # callback when finished showing  - not used
        self.closed_callback=closed_callback            # callback when closed

        self.mon.trace(self,'')
        
        self.play_state='showing'        
        # init state and signals  
        self.quit_signal=False
        # do common bits
        Player.pre_show(self)
        #self.driver.get(self.current_url)
        self.duration_count=self.duration_limit
        self.tick_timer=self.canvas.after(10, self.show_state_machine)

        
    def show_state_machine(self):

        if self.play_state == 'showing':
            self.duration_count -= 1
            # self.mon.log(self,"      Show state machine: " + self.show_state)
            
            # service any queued stop signals and test duration count
            if self.quit_signal is True or (self.duration_limit != 0 and self.duration_count == 0):
                self.mon.log(self,"      Service stop required signal or timeout")
                if self.quit_signal is True:
                    self.quit_signal=False
                if self.freeze_at_end =='yes':
                    self.mon.log(self,'chrome says pause_at_end')
                    if self.finished_callback is not None:
                        self.finished_callback('pause_at_end','pause at end')
                        self.tick_timer=self.canvas.after(50, self.show_state_machine)
                else:
                    self.mon.log(self,'chrome says niceday')
                    self.driver_close()
                    self.play_state='closed'
                    if self.closed_callback is not  None:
                        self.closed_callback('normal','chromedriver closed')
                    return
            else:        
                self.tick_timer=self.canvas.after(50, self.show_state_machine)

                    
    # CLOSE - nothing to do in browserplayer - x content is removed by ready callback and hide browser does not implement pause_at_end
    def close(self,closed_callback):
        self.mon.trace(self,'')
        self.closed_callback=closed_callback
        self.mon.log(self,">close received from show Id: "+ str(self.show_id))
        self.driver_close()
        self.play_state='closed'
        # PP does not use close callback but it does read self.play_state



    def input_pressed(self,symbol):
        self.mon.trace(self,symbol)
        # print symbol
        if symbol == 'pause':
            self.pause()
        elif symbol == 'pause-on':
            self.pause_on()
        elif symbol == 'pause-off':
            self.pause_off()
        elif symbol=='stop':
            self.stop()

    # browsers do not do pause
    def pause(self):
        self.mon.log(self,"!<pause rejected")
        return False

    # browsers do not do pause
    def pause_on(self):
        self.mon.log(self,"!<pause on rejected")
        return False

    # browsers do not do pause
    def pause_off(self):
        self.mon.log(self,"!<pause off rejected")
        return False
        

    # respond to normal stop
    def stop(self):
        # send signal to stop the track to the state machine
        self.mon.log(self,">stop received")
        self.quit_signal=True

# ***********************
# veneer for controlling chromium browser
# ***********************

    def driver_open(self):
        tries=4
        while tries>0:
            try:
                self.driver = webdriver.Chrome(options=self.chrome_options)
                return
            except Exception as e:
                #print ("Failed to open Chromium", e, e.__class__,tries)
                tries-=1


    def driver_close(self):
        try:
            self.driver.close()
        except WebDriverException as e:
            self.mon.warn(self,'Browser Closed in Close !!!!!!\n'+str(e))
        except Exception as e:
            print("Oops!", e, e.__class__, "occurred.")
        else:
            return

    def driver_refresh(self):
        try:
            self.driver.refresh()
        except WebDriverException as e:
            self.mon.warn(self,'Browser Closed in Refresh !!!!!!\n'+str(e))
        except Exception as e:
            print("Oops!", e, e.__class__, "occurred.")
        else:
            return
            
    def driver_get(self,url):
        print ('get',url)
        try:
            self.driver.get(url)
        except WebDriverException as e:
            self.mon.warn(self,'Browser Closed in Get !!!!!!\n'+str(e))
        except Exception as e:
            print("Oops!",e, e.__class__, "occurred.")
        else:
            return

            
# *******************   
# browser commands
# ***********************

    def parse_commands(self,command_text):
        self.command_list=[]
        self.max_loops=-1      #loop continuous if no loop command
        lines = command_text.split('\n')
        for line in lines:
            if line.strip() == '':
                continue
            #print (line)
            reason,entry=self.parse_command(line)
            if reason != 'normal':
                return 'error',entry
            self.command_list.append(copy.deepcopy(entry))
            
        num_loops=0
        for entry in self.command_list:
            if entry[0]=='loop':
                num_loops+=1
            if num_loops>1:
                return 'error', str(num_loops) + ' loop commands in browser commands'
        return 'normal',''

    def parse_command(self,line):
        fields = line.split()
        #print (fields)
        if len(fields) not in (1,2):
            return 'error',"incorrect number of fields in command: " + line
        command=fields[0]
        arg=''
        
        if command not in ('load','refresh','wait','loop'):
            return 'error','unknown browser command: '+ line
            
        if command in ('refresh',) and len(fields) !=1:
            return 'error','incorrect number of fields for '+ command + 'in: ' + line
            
        if command in ('refresh',):
            return 'normal',[command,'']
            
        if command == 'load':
            if len(fields)!=2:
                return 'error','incorrect number of fields for '+ command + 'in: ' + line

            arg=fields[1]
            track=self.complete_path(arg)
            # does media exist    
            if not ':' in track:
                if not os.path.exists(track):
                    return 'error','cannot find file: '+track 
                    
            # add file:// to files.
            if ':' in track:
                url=track
            else:
                url='file://'+track

            return 'normal',[command,url]
                
        if command == 'loop':
            if len(fields)==1:
                arg='-1'
                self.max_loops=-1    #loop continuously if no argument
                return 'normal',[command,arg]
                
            elif len(fields)==2:
                if not fields[1].isdigit() or fields[1]=='0':
                    return 'error','Argument for Loop is not a positive number in: ' + line
                else:
                    arg = fields[1]
                    self.max_loops=int(arg)
                return 'normal',[command,arg]
                                    
            else:
                return 'error','incorrect number of fields for '+ command + 'in: ' + line
                
        if command == 'wait':
            if len(fields)!=2:
                return 'error','incorrect number of fields for '+ command + 'in: ' + line
            else:
                arg = fields[1]
                if not arg.isdigit():
                    return 'error','Argument for Wait is not 0 or positive number in: ' + line
                else:
                    return 'normal',[command,arg]

 
    def play_commands(self):
        # init
        if len(self.command_list)==0:
            return
        self.loop_index=-1 # -1 no loop  comand found
        self.loop_count=0
        self.command_index=0
        self.next_command_index=0  #start at beginning
        #loop round executing the commands
        self.canvas.after(100,self.execute_command)

        
    def execute_command(self):
        self.command_index=self.next_command_index
        if self.command_index==len(self.command_list):
            # past end of command list
            self.quit_signal = True
            return
            
        if self.command_index==len(self.command_list)-1 and self.loop_index!=-1:
            # last in list and need to loop
            self.next_command_index=self.loop_index
        else:
            self.next_command_index=self.command_index+1

        entry=self.command_list[self.command_index]
        command=entry[0]
        arg=entry[1]
        self.mon.log (self,str(self.command_index) + ' Play '+command+' '+arg + '  Next: '+str(self.next_command_index))        
                    
        # and execute command
        if command == 'load':
            self.driver_get(arg)
            self.command_timer=self.canvas.after(10,self.execute_command)
            
        elif command == 'refresh':
            self.driver_refresh()
            self.command_timer=self.canvas.after(10,self.execute_command)
            
        elif command == 'wait':
            self.command_timer=self.canvas.after(1000*int(arg),self.execute_command)
                   
        elif command=='loop':
            if self.loop_index==-1:
                # found loop for first time
                self.loop_index=self.command_index
                self.loop_count=0
                self.mon.log (self,'Loop init To: '+str(self.loop_index) + '  Count: '+str(self.loop_count))
                self.command_timer=self.canvas.after(10,self.execute_command)
            else:
                self.loop_count+=1
                # hit loop command after the requied number of loops
                if self.loop_count==self.max_loops:   #max loops is -1 for continuous
                    self.mon.log (self,'end of loop: '+ '  Count: '+str(self.loop_count))
                    self.quit_signal=True
                    return
                else:
                    self.mon.log (self,'Looping to: '+str(self.loop_index) + ' Count: '+str(self.loop_index))
                    self.command_timer=self.canvas.after(10,self.execute_command)
                    
        elif  command=='exit':
            self.quit_signal=True
            return



    def process_chrome_options(self):
        self.chrome_options = Options()
        #self.add_option("--incognito")
        self.add_option("--noerrdialogs")
        self.add_option("--disable-infobars") 
        self.add_option("--check-for-update-interval=31536000")
        self.add_option('--disable-overlay-scrollbar')
        self.chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])

        try: 
            self.zoom=float(self.chrome_zoom_text)
        except ValueError: 
            return  'error','Chrome Zoom is not a number'+self.chrome_zoom_text

        self.add_option('--force-device-scale-factor='+self.chrome_zoom_text)

        status,message= self.process_chrome_window(self.chrome_window_text)
        if status  == 'error':
            return 'error',message
        
        status,message=self.add_other_options()
        if status  == 'error':
            return 'error',message        
            
        return 'normal',''
          
    def add_other_options(self):
        opts_list=self.chrome_other_options.split (' ')
        #print (opts_list)
        for opt in opts_list:
            if opt=='':
                continue
            if opt[0:2] != '--':
                return 'error','option is not preceded by -- :  '+ opt
            else:
                self.add_option(opt)
        return 'normal',''

    def add_option(self,option):
        #print ('Adding Option: ',option)
        self.chrome_options.add_argument(option)

    def process_chrome_window(self,line):
        #parse chrome window
        # kiosk,fullscreen,app,showcanvas,display
        # obxprop | grep "^_OB_APP"  and click the window

        self.app_mode=False
        
        # showcanvas|display +  [x+y+w*h]
        words=line.split(' ')
        if len(words) not in (1,2):
            return 'error','bad Chrome Web Window form '+line
            
        if words[0] not in ('display','showcanvas','kiosk','fullscreen','app'):
            return 'error','No or invalid Chrome Web Window mode: '+line


        if len(words)==1 and words[0] == 'kiosk':
            self.add_option('--kiosk')
            x_org,y_org=self.dm.real_display_position(self.display_id)
            self.add_option('--window-position='+str(x_org)+','+str(y_org))
            return 'normal',''
            
        if len(words)==1 and words[0] == 'fullscreen':
            self.add_option('--start-fullscreen')
            x_org,y_org=self.dm.real_display_position(self.display_id)
            self.add_option('--window-position='+str(x_org)+','+str(y_org))
            return 'normal',''

        # display or showcanvas with or without dimensions
        self.app_mode=True
        if words[0] == 'display':
            x_org,y_org=self.dm.real_display_position(self.display_id)
            width,height= self.dm.real_display_dimensions(self.display_id)

            
        if words[0] == 'showcanvas':
            x_org,y_org=self.dm.real_display_position(self.display_id)
            x_org+=self.show_canvas_x1
            y_org+= self.show_canvas_y1
            width=self.show_canvas_width
            height=self.show_canvas_height

        x_offset=0
        y_offset=0
        #calc offset and width/height from dimensions
        if len(words)>1:
            status,message,x_offset,y_offset,width,height=self.parse_dimensions(words[1],width,height)
            if status =='error':
                return 'error',message
                
        #correct for zoom
        width=int(width/self.zoom)
        height=int(height/self.zoom)
                
        x= x_org+x_offset
        y= y_org+y_offset
        self.chrome_window_x=x
        self.chrome_window_y=y
        self.chrome_window_width=width
        self.chrome_window_height=height
        print ('app',self.app_mode,x,y,width,height)
        self.add_option('--app='+self.current_url)
        self.add_option('--window-size='+str(width)+','+str(height))
        self.add_option('--window-position='+str(x)+','+str(y))
        return 'normal',''
                
          
            
    def parse_dimensions(self,dim_text,show_width,show_height):
        if '+' in dim_text:
            # parse x+y+width*height
            fields=dim_text.split('+')
            if len(fields) != 3:
                return 'error','bad chrome window form '+dim_text,0,0,0,0

            if not fields[0].isdigit():
                return 'error','x is not a positive decimal in chrome web window '+dim_text,0,0,0,0
            else:
                x=int(fields[0])
            
            if not fields[1].isdigit():
                return 'error','y is not a positive decimal in chrome webwindow '+dim_text,0,0,0,0
            else:
                y=int(fields[1])

            dimensions=fields[2].split('*')
            if len(dimensions)!=2:
                return 'error','bad chrome web window dimensions '+dim_text,'',0,0,0,0
                
            if not dimensions[0].isdigit():
                return 'error','width is not a positive decimal in chrome web window '+dim_text,0,0,0,0
            else:
                width=int(dimensions[0])
                
            if not dimensions[1].isdigit():
                return 'error','height is not a positive decimal in chrome web window '+dim_text,0,0,0,0
            else:
                height=int(dimensions[1])

            return 'normal','',x,y,width,height
        else:
            #width*height
            dimensions=dim_text.split('*')
            if len(dimensions)!=2:
                return 'error','bad chrome web window dimensions '+line,'',0,0,0,0
                
            if not dimensions[0].isdigit():
                return 'error','width is not a positive decimal in chrome web window '+line,'',0,0,0,0
            else:
                window_width=int(dimensions[0])
                
            if not dimensions[1].isdigit():
                return 'error','height is not a positive decimal in chrome web window '+line,'',0,0,0,0
            else:
                window_height=int(dimensions[1])
                
            x=int((show_width-window_width)/2)
            y=int((show_height-window_height)/2)
            return 'normal','',x,y,window_width,window_height

