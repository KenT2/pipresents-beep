#! /usr/bin/env python3

import os
import sys
import subprocess
#from subprocess import run,call
from tkinter import Tk, Canvas,Toplevel,NW,Scrollbar,RIGHT,Y,LEFT,BOTH,TOP
import copy
import configparser


class DisplayManager(object):
    
    # DSI1    0 - MainLCD - official DSI touchscreen
    #         1 -         - Auxilliary LCD ?whats this
    # HDMI0   2 - HDMI0 -   HDMI port 0
    # A/V     3 - Composite  - TV
    #         4 -         - Force LCD
    #         5 -         - Force TV
    #         6 -         - Force non-default display
    #         7 - HDMI1   - HDMI Port 1
    #         8 - 
    
    debug = False
    debug = True
    
    display_map = {'DSI0':0,'HDMI0':2,'HDMI':2,'A/V':3,'HDMI1':7 }    # lookup display Id by display name e.g. HDMI1>7
    display_reverse_map = {0:'DSI0',2:'HDMI0',3:'A/V',7:'HDMI1' }  # lookup display name by Id  e.g. 2>HDMI0

    
    # Class Variables
    
    # obtained from tvservice for model 3 or randr for model 4
    numdisplays=0
    displays=[]         # list of dispay Id's  e.g.[2,7]

    # tv service parameters by Display Id
    # width and height from tvservice does not take into account rotation
    # tvservice needs to be main source of info for model 3. For 4 it is just for info as its use is deprecated
    tv_num_displays = 0
    tv_displays = []
    tv_display_width = {}
    tv_display_height = {}


    # randr paramters by randr name (HDMI-1 etc)
    randr_num_displays = 0 # should be the same as tvservice
    randr_displays = []     
    randr_rotation = {} 
    randr_width = {}
    rand_height = {}
    randr_x = {}
    randr_y = {}

    # dimensions of the real displays obtained from tvservice and randr by display_id (2,7
    real_display_width={}    
    real_display_height={}
    real_display_x = {}
    real_display_y = {}
    real_display_rotation={}
    overlap = ''            #are the displays overlapping also above/sid by side
    
    # dimensions modified by fake in display.cfg, used to create windows
    fake_display_width={}    
    fake_display_height={}
    
    # dimensions of the window in non-fullscreen mode (as modified by non-full window width/height)
    window_width=dict()
    window_height=dict()
    
    # canvas parameters by Display Id
    canvas_obj=dict()     # Tkinter widget
    canvas_width=dict()
    canvas_height=dict()
    
    # touch matrix by display id
    rotation_x_offset={}
    rotation_y_offset={}
    touch_matrix={}
    
    #called by all classes using DisplayManager
    def __init__(self):
        return

# ***********************************************
# Methods for rest of Pi Presents
# ************************************************

    def model_of_pi(self):
        return DisplayManager.pi_model

    def id_of_display(self,display_name):
        if display_name not in DisplayManager.display_map:
            return 'error','Display Name not known '+ display_name,-1
        display_id = DisplayManager.display_map[display_name]
        if display_id not in DisplayManager.displays:
            return 'error','Display not connected '+ display_name,-1
        return 'normal','',display_id
        
    def id_of_canvas(self,display_name):
        if display_name not in DisplayManager.display_map:
            return 'error','Display Name not known '+ display_name,-1,-1
        display_id = DisplayManager.display_map[display_name]
        if display_id not in DisplayManager.canvas_obj:
            return 'error','Display has no canvas '+ display_name,-1,-1
        return 'normal','',display_id,DisplayManager.canvas_obj[display_id]
        
    def name_of_display(self,display_id):
        return DisplayManager.display_reverse_map[display_id]

    def canvas_widget(self,display_id):
        return DisplayManager.canvas_obj[display_id]

    def canvas_dimensions(self,display_id):
        return DisplayManager.canvas_width[display_id],DisplayManager.canvas_height[display_id]
        
    def display_dimensions(self,display_id):
        return DisplayManager.fake_display_width[display_id],DisplayManager.fake_display_height[display_id]

    def real_display_dimensions(self,display_id):
        return DisplayManager.real_display_width[display_id],DisplayManager.real_display_height[display_id]

    def real_display_position(self,display_id):
        return DisplayManager.real_display_x[display_id],DisplayManager.real_display_y[display_id]

    def real_display_orientation(self,display_id):
        return DisplayManager.real_display_rotation[display_id]

    def orientation_offset(self,display_id):
        return DisplayManager.rotation_x_offset[display_id],DisplayManager.rotation_y_offset[display_id]

    def touch_matrix_for(self,display_id):
        matrix=DisplayManager.touch_matrix[display_id]
        # convert to strings array
        cstr=['','','','','','','','','']
        i=0
        while i <9:
            cstr[i]= '{:f}'.format(matrix[i])
            i+=1
        chunks=self.chunks(cstr,3)
        ms='Matrix:\n    '
        for chunk in chunks:
            ms=ms+ '   '.join(chunk)
            ms +='\n    '
        return matrix,ms




# ***********************************************
# Initialize displays at start
# ************************************************

    # called by pipresents.py  only when PP starts
    def init(self,options,close_callback,pp_dir):
        
        # read display.cfg
        self.read_config(pp_dir)

        # get model of Pi. Only interested if it is 4 or less
        self.model=self.pi_model()
        DisplayManager.pi_model=self.model

        self.print_info()

        if self.model == 4:
            # find connected displays from randr and get their parameters            
            status,message=self.find_randr_displays()
            if status=='error':
                return status,message,None
                
            # find connected displays from tvservice and get their parameters
            status,message=self.find_tv_displays()
            if status=='error':
                return status,message,None

            # process Randr displays to display_id
            status,message=self.process_displays_model4()
            if status=='error':
                return status,message,None 

        else:
            # find connected displays from tvservice and get their parameters
            status,message=self.find_tv_displays()
            if status=='error':
                return status,message,None

            # process tvservice displays to display_id and add missing paramters from displau options
            status,message=self.process_displays_model123()
            if status=='error':
                return status,message,None 

        # compute display_width, display_height accounting for --screensize option
        status,message=self.do_fake_display()
        if status=='error':
            return status,message,None            
            
        # Have now got all the required information

        # setup the touch input for touchscreens
        status,message=self.init_touch()
        if status=='error':
            return status,message,None
        
        # set up Tkinter windows
        status,message,root=self.init_tk(options,close_callback)
        if status=='error':
            return status,message,None

        return status,message,root
        

# ***********************************************
# Get information about displays
# ************************************************
        
    def find_tv_displays(self):
        DisplayManager.tv_num_displays=0
        DisplayManager.tv_displays=[]        
        DisplayManager.tv_display_width=dict()
        DisplayManager.tv_display_height=dict()

        # get number of displays and ther Display ID's from tvservice
        l_reply=subprocess.run(['tvservice','-l'],stdout=subprocess.PIPE)
        l_reply_list=l_reply.stdout.decode('utf-8').split('\n')
        DisplayManager.tv_num_displays=int(l_reply_list[0].split(' ')[0])

        for line in range(1,DisplayManager.tv_num_displays+1):
            disp_list=l_reply_list[line].split(' ')
            disp_id=disp_list[2][:1]
            if int(disp_id) not in DisplayManager.display_reverse_map:
                return 'error','Display Id not known: '+ l_reply_list[line]
            DisplayManager.tv_displays.append(int(disp_id))



            # get dimensions of this display from tvservice
            command=['tvservice','-s','-v'+ disp_id]
            s_reply=subprocess.run(command,stdout=subprocess.PIPE)
            s_reply_list=s_reply.stdout.decode('utf-8').split(',')
            s_tt_list=s_reply_list[1].strip().split(' ')
            s_dim_list=s_tt_list[0].split('x')
            # get real display width and height
            DisplayManager.tv_display_width[int(disp_id)]=int(s_dim_list[0])
            DisplayManager.tv_display_height[int(disp_id)]=int(s_dim_list[1])
        self.print_tv()
        return 'normal',''



    def find_randr_displays(self):
        # clear dicts to be used
        DisplayManager.randr_num_displays = 0 # should be the same as tvservice
        DisplayManager.randr_displays = []   # If there are 2 HDMI then HDMI0 is the first
        DisplayManager.randr_rotation = dict() 
        DisplayManager.randr_width = dict() 
        DisplayManager.randr_height = dict() 
        DisplayManager.randr_x = dict() 
        DisplayManager.randr_y = dict() 
        
        #execute xrandr command
        output = subprocess.check_output(["xrandr"]).decode("utf-8").splitlines()
        for l in output:
            if ' connected ' in l:
                fields = l.split()
                name= fields[0]
                DisplayManager.randr_displays.append(name)
                DisplayManager.randr_num_displays +=1
                if 'primary' in l:
                    whxy_field=3
                else:
                    whxy_field=2
                whxy=fields[whxy_field]
                rotation = fields[whxy_field+1]
                if rotation[0]=='(':
                    rotation = rotation[1:]
                wh=whxy.split('+')[0]
                w=wh.split('x')[0]
                h=wh.split('x')[1]
                xy=whxy.split('+')
                x=xy[1]
                y=xy[2]
                DisplayManager.randr_width[name]=int(w)
                DisplayManager.randr_height[name]=int(h)
                DisplayManager.randr_x[name]=int(x)
                DisplayManager.randr_y[name]=int(y)
                DisplayManager.randr_rotation[name]=rotation
        self.print_randr()
        return 'normal',''


    def process_displays_model123(self):
        """
        For model 1,2,3 randr gives no more information than tvservice
        so just copy stuff from tvservice
        However tvservice dos not supply rotation so this has to be got from display.cfg
        """
        # init class variables
        DisplayManager.displays=[]
        DisplayManager.num_displays=0
        DisplayManager.real_display_width=dict()
        DisplayManager.real_display_height=dict()
        DisplayManager.real_display_x=dict()
        DisplayManager.real_display_y=dict()
        DisplayManager.real_display_rotation = dict()
        
        #obtain real from tv and display.cfg
        DisplayManager.displays=DisplayManager.tv_displays
        DisplayManager.num_displays= DisplayManager.tv_num_displays
        for did in DisplayManager.displays:    

            DisplayManager.real_display_x[did]=0   #only one display so x and y are 0
            DisplayManager.real_display_y[did]=0
            status,message,rotation= self.get_rotation(did)
            if status =='error':
                return status,message
            if status == 'null':
                rotation = 'normal'
            DisplayManager.real_display_rotation[did]=rotation
            width=DisplayManager.tv_display_width[did]
            height=DisplayManager.tv_display_height[did]
            if rotation in ('right','left'):
                width,height=height,width
            DisplayManager.real_display_width[did] = width
            DisplayManager.real_display_height[did] = height
        self.print_real()
        return 'normal',''



    def process_displays_model4(self):

        """
        we need to have all parameters referenced to the display_id as display_id is used by omxplayer etc.
        however for model 4:
                x position and y position are provided only by xrandr
                display width and height are swappped for rotated displays by xrandr
                display rotation is provided only by xrandr
        and
        xrandr does not reference display by display_id but by DSI-1 HDMI-1 HDMI-2
        The translation is not constant:
            DSI-1 always equates to display_id 0
            but HDMI-1 and HDMI-2 translation depends on the number of HDMI monitors

        DSI-1 only:  > [0]
        HDMI-1 only: >  [2]  (plugged into HDMI0 port)
        HDMI-2 > [] does not happen because 7 not in randr list - report error
        
        DSI-1 + HDMI-1: [0 + 2]
        DSI-1 + HDMI-2: [0] only because  HDMI-2 cannot be the only HDMI monitor
        HDMI-1 + HDMI-2: [2,7]   assume HDMI0 port is always first in the list

        """

        DisplayManager.displays=[]
        DisplayManager.num_displays=0
        DisplayManager.real_display_width=dict()
        DisplayManager.real_display_height=dict()
        DisplayManager.real_display_x=dict()
        DisplayManager.real_display_y=dict()
        DisplayManager.real_display_rotation = dict()
        
        # translate rand r display names into display_id's
        if DisplayManager.randr_num_displays == 1:
            if DisplayManager.randr_displays[0] == 'HDMI-2':
                return 'error','HDMI-2 cannot be the only display'
            DisplayManager.num_displays = 1
            if DisplayManager.randr_displays[0] == 'DSI-1':
                DisplayManager.displays.append(DisplayManager.display_map['DSI0'])
            elif DisplayManager.randr_displays[0] == 'HDMI-1':
                DisplayManager.displays.append(DisplayManager.display_map['HDMI0'])
        else:
            if 'DSI-1' in DisplayManager.randr_displays and 'HDMI-1' in DisplayManager.randr_displays:
                DisplayManager.displays.append(DisplayManager.display_map['DSI0'])              
                DisplayManager.displays.append(DisplayManager.display_map['HDMI0'])
                DisplayManager.num_displays = 2
            elif 'HDMI-1' in DisplayManager.randr_displays and 'HDMI-2' in DisplayManager.randr_displays:                           
                DisplayManager.displays.append(DisplayManager.display_map['HDMI0'])              
                DisplayManager.displays.append(DisplayManager.display_map['HDMI1'])
                DisplayManager.num_displays = 2
            elif 'DSI-1' in DisplayManager.randr_displays and 'HDMI-2' in DisplayManager.randr_displays:
                DisplayManager.displays.append(DisplayManager.display_map['DSI0'])                                       
                DisplayManager.num_displays = 1

        # copy display dimensions from randr arrays to real arrays
        if DisplayManager.num_displays==1:
            dname1=DisplayManager.randr_displays[0]
            did1=DisplayManager.displays[0]
            if did1 == 7:
                return 'error','single HDMI display must be in port HDMI0'
                
            DisplayManager.real_display_width[did1]= DisplayManager.randr_width[dname1]
            DisplayManager.real_display_height[did1]  = DisplayManager.randr_height[dname1]  
            DisplayManager.real_display_x[did1]= DisplayManager.randr_x[dname1]
            DisplayManager.real_display_y[did1]  = DisplayManager.randr_y[dname1]
            DisplayManager.real_display_rotation[did1]  = DisplayManager.randr_rotation[dname1]


        if DisplayManager.num_displays==2:
            dname1=DisplayManager.randr_displays[0]
            did1=DisplayManager.displays[0]
            dname2=DisplayManager.randr_displays[1]
            did2=DisplayManager.displays[1]
            if did2 == 7 and did1 !=2:
                return 'error','single HDMI display must be in port HDMI0'
                
            DisplayManager.real_display_width[did1]= DisplayManager.randr_width[dname1]
            DisplayManager.real_display_height[did1]  = DisplayManager.randr_height[dname1]  
            DisplayManager.real_display_x[did1]= DisplayManager.randr_x[dname1]
            DisplayManager.real_display_y[did1]  = DisplayManager.randr_y[dname1] 
            DisplayManager.real_display_rotation[did1]  = DisplayManager.randr_rotation[dname1]
            
            DisplayManager.real_display_width[did2]= DisplayManager.randr_width[dname2]
            DisplayManager.real_display_height[did2]  = DisplayManager.randr_height[dname2]  
            DisplayManager.real_display_x[did2]= DisplayManager.randr_x[dname2]
            DisplayManager.real_display_y[did2]  = DisplayManager.randr_y[dname2]
            DisplayManager.real_display_rotation[did2]  = DisplayManager.randr_rotation[dname2]
            
        if DisplayManager.num_displays == 2:
            id0=DisplayManager.displays[0]
            id1=DisplayManager.displays[1]
            if  DisplayManager.real_display_x[id0] == DisplayManager.real_display_x[id1]\
            and DisplayManager.real_display_y[id0] == DisplayManager.real_display_y[id1]:
                DisplayManager.overlap='on-top'
                
            elif  DisplayManager.real_display_x[id0] == DisplayManager.real_display_x[id1]:
                DisplayManager.overlap='above'
            else:
                DisplayManager.overlap='side-by-side'                         

        self.print_real()
        return 'normal',''
    
 
    def do_fake_display(self):
        DisplayManager.fake_display_width=dict()
        DisplayManager.fake_display_height=dict()
        
        for did in DisplayManager.displays:
            reason,message,fake_width,fake_height=self.get_fake_dimensions(DisplayManager.display_reverse_map[did])
            if reason =='error':
                return 'error',message
            if reason == 'null':
                DisplayManager.fake_display_width[did]=DisplayManager.real_display_width[did]
                DisplayManager.fake_display_height[did]=DisplayManager.real_display_height[did]  
            else:
                DisplayManager.fake_display_width[did] = fake_width
                DisplayManager.fake_display_height[did] = fake_height

        self.print_fake()
        return 'normal',''
        
        


# ***********************************************
# Set up Tkinter windows and canvases.
# ************************************************

    def init_tk(self,options,close_callback):
        
        # clear class variables
        DisplayManager.window_width=dict()
        DisplayManager.window_height=dict()
        DisplayManager.canvas_obj=dict()
        DisplayManager.canvas_width=dict()
        DisplayManager.canvas_height=dict()
        
        # get the display to be called Tk
        if len(DisplayManager.displays)==0:
            return 'error','No displays connected',None

        # primary is the display_id that is to be Tk root
        # primary display needs to be 0 if DSI0 is used otherwise Tkinter crashes
        # set to  2 if HDMI0 and HDMI1 as HDMI0 is the main dislay
        # primary_id is assigned to Tk() main window
        # develop_id is windowed if not fullscreen


        if self.model<4:
            # model < 4 
            if DisplayManager.num_displays>1:
                # DSI0 and HDMI0 connected. HDMI0 is in tvservice -l but useless for other than omxplayer output
                primary_id=0
                self.develop_id=0
            else:
                #one display which could be DSI0 or HDMI0
                primary_id=DisplayManager.displays[0]
                self.develop_id=primary_id
        
        else:
            # Model 4
            if len(DisplayManager.displays)==1:
                # single display either DSI0 or HDMI0
                primary_id=DisplayManager.displays[0]
                self.develop_id = primary_id

            elif 0 in DisplayManager.displays and 2 in DisplayManager.displays:
                # DSI0 and HDMI0. Make HDMI0 the windowed display as best for developing.
                primary_id=0     # tk falls over if 0 is not the primary display.
                self.develop_id=2 # 2 is HDMI so best for developing
                
            elif 2 in DisplayManager.displays and 7 in DisplayManager.displays:
                # HDMI0 and HDMI1
                primary_id=2
                self.develop_id=2
        
        # setup Tk windows/canvases for all connected displays
        for this_id in DisplayManager.displays:
            
            # HDMI0 is not useable as a Tk display if there are 2 displays on model<4
            if self.model <4 and DisplayManager.num_displays>1 and this_id !=0:
                continue
                
            # print (this_id, self.develop_id)            
            if this_id == primary_id:
                tk_window=Tk()
                root=tk_window
            else:
                tk_window=Toplevel()
            
            tk_window.title('Pi Presents - ' + DisplayManager.display_reverse_map[this_id])
            tk_window.iconname('Pi Presents')
            tk_window.config(bg='black')

    
            # set window dimensions and decorations
            # make develop_id screen windowed
            if options['fullscreen'] is False and this_id == self.develop_id:
                status,message,x,y,w_scale,h_scale=self.get_develop_window(DisplayManager.display_reverse_map[this_id])
                if status != 'normal':
                    return 'error',message,None
                window_width=DisplayManager.real_display_width[this_id]*w_scale
                window_height= DisplayManager.real_display_height[this_id]*h_scale
                window_x=DisplayManager.real_display_x[self.develop_id] + x
                window_y= DisplayManager.real_display_y[self.develop_id] + y
                # print ('Window Position not FS', this_id,window_x,window_y)
                tk_window.geometry("%dx%d%+d%+d" % (window_width,window_height,window_x,window_y))
                

            else:
                # fullscreen for all displays that are not develop_id
                window_width=DisplayManager.fake_display_width[this_id]
                # krt changed
                window_height=DisplayManager.fake_display_height[this_id]
                window_x=DisplayManager.real_display_x[this_id]
                window_y=DisplayManager.real_display_y[this_id]
                tk_window.attributes('-fullscreen', True)
                os.system('unclutter > /dev/null 2>&1 &')
                
                # print ('Window Position FS', this_id, window_x,window_y,window_width,window_height)
                tk_window.geometry("%dx%d%+d%+d"  % (window_width,window_height,window_x,window_y))
                tk_window.attributes('-zoomed','1')

            DisplayManager.window_width[this_id]=window_width
            DisplayManager.window_height[this_id]=window_height    

            # define response to main window closing.
            tk_window.protocol ("WM_DELETE_WINDOW", close_callback)
            

            # setup a canvas onto which will be drawn the images or text
            # canvas covers the whole screen whatever the size of the window

            
            canvas_height=DisplayManager.fake_display_height[this_id]
            canvas_width=DisplayManager.fake_display_width[this_id]
            


            if options['fullscreen'] is False:
                ##scrollbar = Scrollbar(tk_window)
                #scrollbar.pack(side=RIGHT, fill=Y)
                tk_canvas = Canvas(tk_window, bg='black')
                #tk_canvas = Canvas(tk_window, bg='blue',yscrollcommand=scrollbar.set)
                tk_canvas.config(height=canvas_height,
                                   width=canvas_width,
                                   highlightcolor='yellow',
                                   highlightthickness=1)
                #tk_canvas.pack(anchor=NW,fill=Y)
                #scrollbar.config(command=tk_canvas.yview)
                tk_canvas.place(x=0,y=0)
            else:
                tk_canvas = Canvas(tk_window, bg='black')
                tk_canvas.config(height=canvas_height,
                                 width=canvas_width,
                                 highlightthickness=0,
                                highlightcolor='yellow')
                tk_canvas.place(x=0,y=0)

            

            # tk_canvas.config(bg='black')

            
            DisplayManager.canvas_obj[this_id]=tk_canvas
            DisplayManager.canvas_width[this_id]=canvas_width
            DisplayManager.canvas_height[this_id]=canvas_height

            tk_window.focus_set()
            tk_canvas.focus_set()
        
        self.print_tk()
        return 'normal','',root




    def print_info(self):
        if DisplayManager.debug is True:
            print ('\nMaps:',DisplayManager.display_map,DisplayManager.display_reverse_map)
            print ('Pi Model:',self.model)

    def print_tv(self):
        if DisplayManager.debug is True:        
            print ('\nNumber of Displays - tvservice:',DisplayManager.tv_num_displays)
            print ('Displays Connected - tvservice:',DisplayManager.tv_displays)
            print ('Display Dimensions - tvservice:',DisplayManager.tv_display_width,DisplayManager.tv_display_height)

    def print_randr(self):
        if DisplayManager.debug is True:
            print ('\nNumber of Displays - randr:',DisplayManager.randr_num_displays)
            print ('Displays Connected- randr:',DisplayManager.randr_displays)
            print ('Display Dimensions - randr:',DisplayManager.randr_width,DisplayManager.randr_height)
            print ('Display Position - randr:',DisplayManager.randr_x,DisplayManager.randr_y)
            print ('Display Rotation - randr:',DisplayManager.randr_rotation)

    def print_real(self):
        if DisplayManager.debug is True:
            print ('\nNumber of Displays - real:',DisplayManager.num_displays)
            print ('Displays Connected- real:',DisplayManager.displays)
            
            print ('Display Dimensions - real:',DisplayManager.real_display_width,DisplayManager.real_display_height)
            print ('Display Position - real:',DisplayManager.real_display_x,DisplayManager.real_display_y)
            print ('Display Rotation - real:',DisplayManager.real_display_rotation)

    def print_fake(self):
        if DisplayManager.debug is True:
            print ('\nDisplay Dimensions - fake:',DisplayManager.fake_display_width,DisplayManager.fake_display_height)

    def print_tk(self):
        if DisplayManager.debug is True:
            print ('\nDevelopment Display:',self.develop_id)
            print ('Window Dimensions - non-full:',DisplayManager.window_width,DisplayManager.window_height)
            print ('Canvas Widget:',DisplayManager.canvas_obj)
            print ('Canvas Dimensions:',DisplayManager.canvas_width,DisplayManager.canvas_height,'\n\n')




# ***********************************************
# Touchscreen Calibration
# ************************************************

    def init_touch(self):
        
        # enable display debug output to terminal
        self.debug=DisplayManager.debug
        total_width=0
        total_height=0

        for display_id in DisplayManager.displays:
            # for model 3 miss out id = 2 or 3 if touchsreen is connected as tvservice includes HDMI0 even if useless
            if self.model <4 and DisplayManager.num_displays>1 and display_id !=0:
                continue
            if DisplayManager.overlap == 'on-top':
                return 'error','The two monitors must not overlap in Screen Config Utility'
            elif DisplayManager.overlap == 'above':
                total_height += DisplayManager.real_display_height[display_id]
                total_width=max(total_width,DisplayManager.real_display_width[display_id])
            else:
                total_width += DisplayManager.real_display_width[display_id]
                total_height=max(total_height,DisplayManager.real_display_height[display_id])            
        
        for display_id in DisplayManager.displays:
            rotation=DisplayManager.real_display_rotation[display_id]
            width=DisplayManager.real_display_width[display_id]
            height=DisplayManager.real_display_height[display_id]
            x_position=DisplayManager.real_display_x[display_id]
            y_position=DisplayManager.real_display_y[display_id]
            # print (display_id)
            DisplayManager.touch_matrix[display_id],coords_str \
               =self.calc_coords(display_id,rotation,width,height,x_position,y_position,total_width,total_height,'',self.debug)

            status,message,driver_name=self.get_driver_name(display_id)
            if status =='error':
                return status,message
            if status =='null':
                if self.debug:
                    print ('Touch driver not defined for '+ str(display_id))
            if status == 'normal':
                status,message=self.send_xinput(display_id,coords_str,driver_name)
            if status == 'error':
                return 'error','Touch driver is '+ message
        return 'normal',''
        

        
        

    def calc_coords(self,display_id,rotation,width,height,x_position,y_position,total_width,total_height,title,debug):

        # if display is rotated the origin moves, offset is how the ORIGIN moves
        # Note: left and right reversed from how you might draw them
        rotation_x_offset ={'normal':0,
                            'left':width,     # !! display rotated clockwise 
                            'inverted':width,
                            'right':0,        # !! display rotated anti-clock

                        }   
                        
        rotation_y_offset ={'normal':0,
                            'left':0,
                            'inverted':height,
                            'right':height,
                        }  

          
        # calling function has swapped width and height for rotated monitos

        sx = width/total_width
        sy = height/total_height
        tx=(rotation_x_offset[rotation]+ x_position)/total_width
        ty=(rotation_y_offset[rotation]+ y_position)/total_height
        DisplayManager.rotation_x_offset[display_id]=rotation_x_offset[rotation]
        DisplayManager.rotation_y_offset[display_id]=rotation_y_offset[rotation]

        
        if debug is True:
            print ('\n---------'+ title + '-------------')
            print ('width rot-ofxset x-position total-width:',width,rotation_x_offset[rotation],x_position,total_width)
            print ('height rot-ofxset y-position total-height:',height,rotation_y_offset[rotation],y_position,total_height)
        c,cstr=self.matrix(DisplayManager.display_reverse_map[display_id],rotation,sx,sy,tx,ty,'',debug)
        
        return c,cstr


    def chunks(self,lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def matrix(self,position,rotation,sx,sy,tx,ty,text,debug):
        
        
        # base has c[2] and c[5] set to include the offset of the origin due to rotation, however these
        # are not used by this code as the coords are given by tx and ty
                        
        self.base={
            'normal':   [1, 0, 0,
                        0, 1, 0,
                        0 ,0 ,1],
                        
            'left':     [0, -1, 1,   #90 degrees
                        1, 0, 0,
                        0 ,0 ,1],
                        
            'inverted':[-1, 0, 1,
                        0, -1, 1,
                         0 ,0 ,1],
                         
            'right':    [0, 1, 0,    #270 degrees
                        -1, 0, 1,
                        0 ,0 ,1]}
                        
        rb = self.base[rotation]
        
        # deepcopy the rotated template
        c=copy.deepcopy(rb)
        #print (c)

        c[0] = sx * c[0]
        c[1] = sx * c[1]
        c[2] = tx
        c[3] = sy * c[3]
        c[4] = sy * c[4]
        c[5] = ty
        
        # convert to strings array
        cstr=['','','','','','','','','']
        i=0
        while i <9:
            cstr[i]= '{:f}'.format(c[i])
            i+=1
        chunks=self.chunks(cstr,3)
        
        if debug is True:
            print ('\n'+ position +' Monitor, Rotation = ' + rotation)
            if text!='': print('\n'+text)
            for chunk in chunks:
                print ('   '+'   '.join(chunk))
        return c,cstr


    def send_xinput(self,display_id,coords_str,driver_name):
        self.xinput_template=['xinput', 'set-prop', '', '--type=float', '"Coordinate Transformation Matrix"']

        if driver_name !='':
            # send command only if a display driver is present  
            xinput_command=copy.deepcopy(self.xinput_template)
            xinput_command[2]=driver_name
            xinput_command += coords_str
            xinput_str=' '.join(xinput_command)
            if self.debug:
                print ('\nxinput call for ' + DisplayManager.display_reverse_map[display_id] +  ':\n    '+' '+xinput_str+'\n')
            proc=subprocess.Popen(xinput_str, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=proc.communicate(xinput_str)
            #strip newline
            err= err[0:-1]
            if len(err)==0:
                return 'normal',''
            else:
                return 'error',err.decode('utf-8')+'|'

            


        
        
# ***********************************************
# Determine model of Pi - 1,2,3,4
# ************************************************

## awk '/^Revision/ {sub("^1000", "", $3); print $3}' /proc/cpuinfo 

    def pi_model(self):
        command=['cat', '/proc/device-tree/model']
        l_reply=subprocess.run(command,stdout=subprocess.PIPE)
        l_reply_list=l_reply.stdout.decode('utf-8').split(' ')
        if l_reply_list[2] == 'Zero':
            return 0
        elif l_reply_list[2] == 'Model':
            return 1
        else:
            return int(l_reply_list[2])

# ***********************************************
# Read and process configuration data
# ************************************************

    # read display.cfg    
    def read_config(self,pp_dir):
        filename=pp_dir+os.sep+'pp_config'+os.sep+'pp_display.cfg'
        if os.path.exists(filename):
            DisplayManager.config = configparser.ConfigParser(inline_comment_prefixes = (';',))
            DisplayManager.config.read(filename)
            return 'normal','display.cfg read'
        else:
            return 'error',"Failed to find display.cfg at "+ filename

    def displays_in_config(self):
        return DisplayManager.config.sections()
        
    def display_in_config(self,section):
        return DisplayManager.config.has_section(section)
        
    def get_item_in_config(self,section,item):
        return DisplayManager.config.get(section,item)

    def item_in_config(self,section,item):
        return DisplayManager.config.has_option(section,item)


    def get_rotation(self,did):
        if not self.display_in_config(DisplayManager.display_reverse_map[did]):
            return 'error','display not in display.cfg '+ DisplayManager.display_reverse_map[did],0,0
        if not self.item_in_config(DisplayManager.display_reverse_map[did],'rotation-1-2-3'):
            return 'null','',''
        rot_text=self.get_item_in_config(DisplayManager.display_reverse_map[did],'rotation-1-2-3')
        if rot_text=='':
            return 'null','',''
        if rot_text not in ('normal','right','inverted','left'):
            return 'error','rotation not understood in display.cfg '+rot_text,''
        return 'normal','',rot_text


    def get_fake_dimensions(self,dname):
        if not self.display_in_config(dname):
            return 'error','display not in display.cfg '+ dname,0,0
        if not self.item_in_config(dname,'fake-dimensions'):
            return 'null','',0,0
        size_text=self.get_item_in_config(dname,'fake-dimensions')
        if size_text=='':
            return 'null','',0,0
        fields=size_text.split('*')
        if len(fields)!=2:
            return 'error','do not understand fake-dimensions in display.cfg for '+dname,0,0
        elif fields[0].isdigit()  is False or fields[1].isdigit()  is False:
            return 'error','fake dimensions are not positive integers in display.cfg for '+dname,0,0
        else:
            return 'normal','',int(fields[0]),int(fields[1])

    def get_develop_window(self,dname):
        if not self.display_in_config(dname):
            return 'error','display not in display.cfg '+ dname,0,0
        if not self.item_in_config(dname,'develop-window'):
            return 'normal','',0,0,0.45,0.7
        size_text=self.get_item_in_config(dname,'develop-window')
        if size_text=='':
            return 'normal','',0,0,0.45,0.7
        if '+' in size_text:
            # parse  x+y+width*height
            fields=size_text.split('+')
            if len(fields) != 3:
                return 'error','Do not understand Display Window in display.cfg for '+dname,0,0,0,0
            dimensions=fields[2].split('*')
            if len(dimensions)!=2:
                return 'error','Do not understand Display Window in display.cfg for '+dname,0,0,0,0
            
            if not fields[0].isdigit():
                return 'error','x is not a positive decimal in display.cfg for '+dname,0,0,0,0
            else:
                x=float(fields[0])
            
            if not fields[1].isdigit():
                return 'error','y is not a positive decimal in display.cfg for '+dname,0,0,0,0
            else:
                y=float(fields[1])
                
            if not self.is_scale(dimensions[0]):
                return 'error','width1 is not a positive decimal in display.cfg for '+dname,0,0,0,0
            else:
                width=float(dimensions[0])
                
            if not self.is_scale(dimensions[1]):
                return 'error','height is not a positive decimal in display.cfg for '+dname,0,0,0,0
            else:
                height=float(dimensions[1])

            return 'normal','',x,y,width,height


    def is_scale(self,s):
        try:
            sf=float(s)
            if sf > 0.0 and sf <=1:
                return True
            else:
                return False
        except ValueError:
            return False

    def get_driver_name(self,display_id):
        if not self.display_in_config(DisplayManager.display_reverse_map[display_id]):
            return 'error','display not in display.cfg '+ dname,''
        if not self.item_in_config(DisplayManager.display_reverse_map[display_id],'touch-driver'):
                return 'error','touch driver not in display.cfg for '+ DisplayManager.display_reverse_map[display_id],''
        driver_name=self.get_item_in_config(DisplayManager.display_reverse_map[display_id],'touch-driver')
        driver_name=driver_name.strip()
        if len(driver_name)==0:
            return 'null','',driver_name   
        if len(driver_name)<2 or driver_name[0] !='"' or driver_name[-1] != '"':
            return 'error','driver-name must begin and end with ":  '+driver_name,''
        inside = driver_name.strip('"')
        empty = inside.strip()
        if len(empty)==0:
            return 'null','',driver_name
        return 'normal','',driver_name


# ***********************************************
# HDMI Monitor Commands for DSI and HDMI
# ************************************************

    def handle_monitor_command(self,args):
        #fields=command_text.split()
        #args = fields[1:]
        # print ('args',args)
        if len(args) == 0:
            return 'error','no arguments for monitor command'
        if len (args) == 2:
            command = args[0]
            display= args[1].upper()
            if display not in DisplayManager.display_map:
                return 'error', 'Monitor Command - Display not known: '+ display
            display_num=DisplayManager.display_map[display]
            if display_num not in DisplayManager.displays:
                return 'error', 'Monitor Command - Display not connected: '+ display 
            display_ref=str(display_num)
        else:
            command= args[0]
            display_ref = ''
            
        # print (command,display_ref)
        if command == 'reset':
            for display in DisplayManager.displays:
                display_ref=str(display)
                os.system('vcgencmd display_power 1 '+ display_ref + ' >/dev/null')
            return 'normal',''
            
        elif command == 'on':
            os.system('vcgencmd display_power 1 '+ display_ref + ' >/dev/null')
            return 'normal',''
            
        elif command == 'off':
            os.system('vcgencmd display_power 0 '+ display_ref + '  >/dev/null')
            return 'normal',''
        else:
            return 'error', 'Illegal Monitor command: '+ command



# ***********************************************
# Touchscreen Backlight Commands
# ************************************************    
    def do_backlight_command(self,text):
        """
        try:
            from rpi_backlight import Backlight
        except:
            return 'error','rpi-backlight not installed'
        """
        backlight=Backlight()
        fields=text.split()
        # print (fields)
        if len(fields)<2:
            return 'error','too few fields in backlight command: '+ text
        # on, off, inc val, dec val, set val fade val duration
        #                                      1   2    3
        if fields[1]=='on':
            backlight.power = True
            return 'normal',''      
        if fields[1]=='off':
            backlight.power = False
            return 'normal',''
        if fields[1] in ('inc','dec','set'):
            if len(fields)<3:
                return 'error','too few fields in backlight command: '+ text
            if not fields[2].isdigit():
                return'error','field is not a positive integer: '+text
            if fields[1]=='set':
                val=int(fields[2])
                if val>100:
                    val = 100
                elif val<0:
                    val=0
                # print (val)
                backlight.brightness = val
                return 'normal',''            
            if fields[1]=='inc':
                val = backlight.brightness + int(fields[2])
                if val>100:
                    val = 100
                # print (val)
                backlight.brightness= val
                return 'normal',''
            if fields[1]=='dec':
                val = backlight.brightness - int(fields[2])
                if val<0:
                    val = 0
                # print (val)
                backlight.brightness= val
                return 'normal',''
        if fields[1] =='fade':
            if len(fields)<4:
                return 'error','too few fields in backlight command: '+ text
            if not fields[2].isdigit():
                return'error','backlight field is not a positive integer: '+text            
            if not fields[3].isdigit():
                return'error','backlight field is not a positive integer: '+text
            val=int(fields[2])
            if val>100:
                val = 100
            elif val<0:
                val=0
            with backlight.fade(duration=fields[3]):
                backlight.brightness=val
                return 'normal',''
        return 'error','unknown backlight command: '+text



class Backlight():
    
    def __init__(self):
        self._brightness=100
        self._power = True
        

    def get_power(self):
        return self._power

    def set_power(self, power):
        self._power=power
        # print (self._power)

    power = property(get_power, set_power)

    def get_brightness(self):
        return self._brightness

    def set_brightness(self, brightness):
        self._brightness=brightness
        # print (self._brightness)

    brightness = property(get_brightness, set_brightness)    



    
# **************************
# Test Harness
# **************************   

# dummy debug monitor
class Mon(object):
    
    def err(self,inst,message):
        print ('ERROR: ',message)

    def log(self,inst,message):
        print ('LOG: ',message)

    def warn(self,inst,message):
        print ('WARN: ',message)
        
        

class PiPresents(object):

    def __init__(self):
        
        self.mon=Mon()
        self.ref0=None
        self.ref1=None
    
                
        # ********************
        # SET UP THE GUI
        # ********************
        

        self.options={'fullscreen':True}
        

        # set up the displays and create a canvas for each display
        self.dm=DisplayManager()
        self.pp_dir='/home/pi/pipresents'
        status,message,self.root=self.dm.init(self.options,self.end)
        if status !='normal':
            self.mon.err(self,message)
            sys.exit(111) 
            
        self.canvas0=None
        self.canvas1=None

        status,message,self.dsi_id,canvas_id=self.dm.id_of_canvas('DSI0')
        if status == 'normal':
            self.canvas0=canvas_id
            self.canvas0.create_text(20,20,anchor=NW,text='F4 to close',font='arial 14',fill='yellow')
            self.canvas0.create_text(20,40,anchor=NW,text='display id: ' + str(self.dsi_id),font='arial 14',fill='yellow')
            self.canvas0.create_text(20,60,anchor=NW,text='canvas for display 0:  ' + str(self.canvas0),font='arial 14',fill='yellow')  
            width0,height0=self.dm.canvas_dimensions(self.dsi_id)
            self.canvas0.create_text(20,80,anchor=NW,text='Canvas width/height: '+str(width0)+' '+str(height0),font='arial 14',fill='yellow')
            self.canvas0.create_text(20,100,anchor=NW,text='Display Rotation: '+ self.dm.real_display_orientation(self.dsi_id),font='arial 14',fill='yellow')

            self.matrix0,ms0=self.dm.touch_matrix_for(self.dsi_id)
            self.canvas0.create_text(20,120,anchor=NW,text=self.matrix_text(self.matrix0),font='arial 14',fill='yellow')
            self.canvas0.create_text(width0/2,height0/2,text='*',font='arial 16',fill='yellow')
            self.canvas0.bind('<Button-1>',self.click_pressed)
            #self.canvas0.bind('<Motion>',self.click_pressed)
            self.canvas0.bind("<F4>", self.end_event)
            print ('set up DSI0 as Canvas0',self.dsi_id,canvas_id)
        
        status,message,self.hdmi0_id,canvas_id=self.dm.id_of_canvas('HDMI0')
        if status == 'normal':
        
            self.canvas1=canvas_id
            width1,height1=self.dm.canvas_dimensions(self.hdmi0_id)
            self.canvas1.create_text(20,20,anchor=NW,text='F4 to close',font='arial 14',fill='yellow') 
            self.canvas1.create_text(20,40,anchor=NW,text='display id: ' + str(self.hdmi0_id),font='arial 14',fill='yellow')
            self.canvas1.create_text(20,60,anchor=NW,text='canvas for display 1:  ' + str(self.canvas1),font='arial 14',fill='yellow')            
            self.canvas1.create_text(20,80,anchor=NW,text='Canvas width/height: '+str(width1)+' '+str(height1),font='arial 14',fill='yellow')
            self.canvas1.create_text(20,100,anchor=NW,text='Display Rotation: '+ self.dm.real_display_orientation(self.hdmi0_id),font='arial 14',fill='yellow')
            self.matrix1,ms1=self.dm.touch_matrix_for(self.hdmi0_id)
            self.canvas1.create_text(20,120,anchor=NW,text=self.matrix_text(self.matrix1),font='arial 14',fill='yellow')

            self.canvas1.create_text(width1/2,height1/2,text='*',font='arial 14',fill='yellow')
            
            # self.canvas1.bind('<Motion>',self.click_pressed)
            self.canvas1.bind('<Button-1>',self.click_pressed)
            self.canvas1.bind("<F4>", self.end_event)
            print ('set up HDMI0 as Canvas1',self.hdmi0_id,canvas_id)
            
            
        status,message,self.hdmi1_id,canvas_id=self.dm.id_of_canvas('HDMI1')
        if status == 'normal':
            # reuse canvas0 because cannot have DSI0 and HDMI0
            self.canvas0=canvas_id
            self.canvas0.create_text(20,20,anchor=NW,text='F4 to close',font='arial 14',fill='yellow')
            self.canvas0.create_text(20,40,anchor=NW,text='display id: ' + str(self.hdmi1_id),font='arial 14',fill='yellow')
            self.canvas0.create_text(20,60,anchor=NW,text='canvas for display 0:  ' + str(self.canvas0),font='arial 14',fill='yellow')  
            width3,height3=self.dm.canvas_dimensions(self.hdmi1_id)
            self.canvas0.create_text(20,80,anchor=NW,text='Canvas width/height: '+str(width3)+' '+str(height3),font='arial 14',fill='yellow')
            self.canvas0.create_text(20,100,anchor=NW,text='Display Rotation: '+ self.dm.real_display_orientation(self.hdmi1_id),font='arial 14',fill='yellow')

            self.matrix0,ms0=self.dm.touch_matrix_for(self.hdmi1_id)
            self.canvas0.create_text(20,120,anchor=NW,text=self.matrix_text(self.matrix0),font='arial 14',fill='yellow')
            self.canvas0.create_text(width3/2,height3/2,text='*',fill='yellow')
            self.canvas0.bind('<Button-1>',self.click_pressed)
            # self.canvas0.bind('<Motion>',self.click_pressed)
            self.canvas0.bind("<F4>", self.end_event)
            print ('set up HDMI1 as Canvas0',self.hdmi1_id,canvas_id)
        
        # start Tkinters event loop
        self.root.mainloop( )

    def click_pressed(self,event):
        x= event.x
        y= event.y
        widget=event.widget
        #print ('click',widget,x,y)

        if self.canvas0 != None:
            if self.ref0 !=None:
                self.canvas0.delete(self.ref0)
                self.ref0=None
            if widget== self.canvas0:
                text0 = 'x,y:  '+ str(x) + " " + str(y)              
            else:
                text0 = 'Clicked on other display'
            self.ref0=self.canvas0.create_text(100,300,anchor=NW,text=text0,fill='yellow',font='arial 20')
            
        if self.canvas1 != None:       
            if self.ref1 !=None:
                self.canvas1.delete(self.ref1)
                self.ref1=None
            if widget== self.canvas1:
                text1 = 'x,y:  '+ str(x) + " " + str(y)
            else:
                text1 = 'Clicked on other display'

            self.ref1=self.canvas1.create_text(100,300,anchor=NW,text=text1,fill='yellow',font='arial 20')
            

        #status,message=self.dm.do_backlight_command('backlight set 50')            

        # print (status,message)

    def matrix_text(self,c):
        # convert to string
        cstr=['','','','','','','','','']
        i=0
        while i <9:
            cstr[i]= '{:f}'.format(c[i])
            i+=1
        chunks=self.chunks(cstr,3)
        cstr33=''
        for chunk in chunks:
                line = '   '.join(chunk)
                cstr33 += '\n'+line
        return cstr33


    def chunks(self,lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def end_event(self,event):
        self.end()           

    def end(self):
        self.mon.log(self,"Pi Presents aborted: ")
        if self.root is not None:
            self.root.destroy()

        self.mon.log(self,"Pi Presents  exiting normally, bye")
        sys.exit(100)



if __name__ == '__main__':
    pp=PiPresents()
    
