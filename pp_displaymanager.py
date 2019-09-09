#! /usr/bin/env python3

import os
import sys
import subprocess
from subprocess import run,call
from tkinter import Tk, Canvas,Toplevel,NW


class DisplayManager(object):
    
    # 2*HDMI  3     displays connected
    # HDMI0  DSI    0 - MainLCD - official DSI touchscreen
    # HDMI0  DSI    1 -         - Auxilliary LCD ?whats this
    # HDMI0  HDMI0  2 - HDMI0 -   HDMI port 0
    # HDMI0  DSI    3 - Composite  - TV
    # HDMI0  DSI    4 -         - Force LCD
    # HDMI0  HDMI0  5 -         - Force TV
    # HDMI0  HDMI0  6 -         - Force non-default display
    # HDMI1  HDMI0  7 - HDMI1   - HDMI Port 1
    # HDMI0  HDMI0  8 ????
    
    display_map = {'DSI0':0,'HDMI0':2,'HDMI':2,'A/V':3,'HDMI1':7 }    # lookup display Id by display name e.g. HDMI1>7
    display_reverse_map = {0:'DSI0',2:'HDMI0',3:'A/V',7:'HDMI1' }  # lookup display name by Id  e.g. 2>HDMI0

    # position and size of window without -f command line option
    # format <dispay_id>:<proportion>
    # 2 is HDMI0 7 is HDMI 1
    nonfull_window_width = {0:0.45,2:0.45,3:0.45,7:0.45} # proportion of width
    nonfull_window_height= {0:0.7,2:0.7,3:0.7,7:0.7} # proportion of height
    nonfull_window_x = {0:0,2:0,3:100,7:0} # position of top left corner
    nonfull_window_y=  {0:0,2:0,3:0,7:0} # position of top left corner
    
    
    # Class Variables
    num_displays = 0   # number of displays found
    displays=[]         # list of dispay Id's  e.g.[2,7]

    # display paramters by Display Id
    # dimensions of the real displays
    
    real_display_width={}    
    real_display_height={}
    
    # dimensiions modified by --screensize
    display_width={}    
    display_height={}
    
    # dimennsions of the window in non-fullscreen mode (as modified by non-full window width/height)
    window_width=dict()
    window_height=dict()
    window_x_offset = {0:0,2:0,3:0,7:0}   # only 2 and 7 should be modified
    
    # canvas parameters by Display Id
    canvas_obj=dict()     # Tkinter widget
    canvas_width=dict()
    canvas_height=dict()
    
    
    #called by all classes using DisplayManager
    def __init__(self):
        return
        
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
        return DisplayManager.display_width[display_id],DisplayManager.display_height[display_id]

    def real_display_dimensions(self,display_id):
        return DisplayManager.real_display_width[display_id],DisplayManager.real_display_height[display_id]



    # called by pipresents.py  only when PP starts
    def init(self,options,close_callback):
        # primary is the Display Name that is to be Tk-root e.g. HDMI0
        
        # clear class variables
        DisplayManager.window_width=dict()
        DisplayManager.window_height=dict()
        DisplayManager.canvas_obj=dict()
        DisplayManager.canvas_width=dict()
        DisplayManager.canvas_height=dict()

        self.model=self.pi_model()

        # find connected displays and get their paramters
        status,message=self.find_displays(options)
        if status=='error':
            return status,message,None
        
        # get the display to be called Tk
        if len(DisplayManager.displays)==0:
            return 'error','No displays connected',None
        
        # primary display needs to be 0 if DSI0 is used otherwise Tkinter crashes
        # also optionally set to  2 if HDMI0 and HDMI1 as HDMI0 is the main dislay
        #primary_id is assigned to Tk() main window
        # develop_id is windowed if not fullscreen
        if self.model<4:
            if DisplayManager.num_displays>1:
                #HDMI0 is in tvservice -l but useless
                primary_id=0
                self.develop_id=0
            else:
                primary_id=DisplayManager.displays[0]
                self.develop_id=primary_id
        #Model 4
        elif len(DisplayManager.displays)==1:
            primary_id=DisplayManager.displays[0]
            self.develop_id = primary_id

        elif 0 in DisplayManager.displays and 2 in DisplayManager.displays:
            primary_id=0
            self.develop_id=2
        elif 2 in DisplayManager.displays and 7 in DisplayManager.displays:
            primary_id=2
            self.develop_id=2
        

        for this_id in DisplayManager.displays:
            if self.model ==3 and DisplayManager.num_displays>1 and this_id !=0:
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



            # calculate offset to place HDMI1 display or DSI0 on second screen by making x be the width of HDMI0 display
            window_x_offset=0
            if 2 in DisplayManager.displays and 7 in DisplayManager.displays:
                if this_id == 7:
                    window_x_offset=DisplayManager.real_display_width[2]
                    DisplayManager.window_x_offset[2]=window_x_offset
            if 0 in DisplayManager.displays and 2 in DisplayManager.displays:
                if this_id == 2:
                    window_x_offset=DisplayManager.real_display_width[0]
                    DisplayManager.window_x_offset[2]=window_x_offset


    
            # set window dimensions and decorations
            
            if options['fullscreen'] is False and this_id == self.develop_id:
                window_width=DisplayManager.real_display_width[this_id]*DisplayManager.nonfull_window_width[this_id]
                window_height= DisplayManager.real_display_height[this_id]*DisplayManager.nonfull_window_height[this_id]
                window_x=DisplayManager.nonfull_window_x[this_id]+ window_x_offset
                window_y=DisplayManager.nonfull_window_y[this_id]
                # print ('Window Position not FS', this_id,window_x,window_y)
                tk_window.geometry("%dx%d%+d%+d" % (window_width,window_height,window_x,window_y))

            else:
                # fullscreen for displays that are not develop_id
                window_width=DisplayManager.display_width[this_id]
                # krt changed
                window_height=DisplayManager.display_height[this_id]
                window_x=window_x_offset
                window_y=0
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
            
            canvas_height=DisplayManager.display_height[this_id]
            canvas_width=DisplayManager.display_width[this_id]
            tk_canvas = Canvas(tk_window, bg='black')
    
            if options['fullscreen'] is False:
                tk_canvas.config(height=canvas_height,
                                   width=canvas_width,
                                   highlightcolor='yellow',
                                   highlightthickness=1)
            else:
                tk_canvas.config(height=canvas_height,
                                 width=canvas_width,
                                 highlightthickness=0,
                                highlightcolor='yellow')
                
            tk_canvas.place(x=0,y=0)
            # self.canvas.config(bg='black')

            
            DisplayManager.canvas_obj[this_id]=tk_canvas
            DisplayManager.canvas_width[this_id]=canvas_width
            DisplayManager.canvas_height[this_id]=canvas_height

            tk_window.focus_set()
            tk_canvas.focus_set()
            
            
        
        # set the scaling for the official DSI touchscreen and HDMI0
        # Touchscreen must be left of HDMI0
        # HDMI0 must be left of HDMI1
        
        if DisplayManager.num_displays==1 and DisplayManager.displays[0]==0:
            # touchscreen by itself
            self.set_touch_scale('single',0,-1)
        elif DisplayManager.num_displays==1 and DisplayManager.displays[0]==2:
            # HDMI0 by itself by itself
            self.set_touch_scale('single',2,-1)            
        elif 0 in DisplayManager.displays and 2 in DisplayManager.displays:
            self.set_touch_scale('left',0,2)
        elif 2 in DisplayManager.displays and 7 in DisplayManager.displays:
            self.set_touch_scale('left',2,7)
            
            
        self.print_displays()
        
        return status,message,root
        
 
        
    def find_displays(self,options):
        self.options=options
        DisplayManager.num_displays=0
        DisplayManager.displays=[]        
        DisplayManager.real_display_width=dict()
        DisplayManager.real_display_height=dict()
        DisplayManager.display_width=dict()
        DisplayManager.display_height=dict()

        # get number of displays and ther Dispy ID's from tvservice
        l_reply=subprocess.run(['tvservice','-l'],stdout=subprocess.PIPE)
        l_reply_list=l_reply.stdout.decode('utf-8').split('\n')
        DisplayManager.num_displays=int(l_reply_list[0].split(' ')[0])

        real_display0_width=0
        for line in range(1,DisplayManager.num_displays+1):
            # print (l_reply_list[line])
            disp_list=l_reply_list[line].split(' ')
            disp_id=disp_list[2][:1]
            if int(disp_id) not in DisplayManager.display_reverse_map:
                return 'error','Display Id not known: '+ l_reply_list[line]
            DisplayManager.displays.append(int(disp_id))

            # Pi3 tvservice -l
            # 2 attached device(s), display ID's are : 
            # Display Number 0, type Main LCD
            # Display Number 2, type HDMI 0

            # tvservice -s -vx
            # pi 3 - state 0xa [HDMI CEA (16) RGB lim 16:9], 1920x1080 @ 60.00Hz, progressive
            # pi3t - state 0xa [HDMI CEA (16) RGB lim 16:9], 1920x1080 @ 60.00Hz, progressive
            # pi 4 - state 0xa [HDMI CUSTOM RGB lim 16:9], 1920x1080 @ 60.00Hz, progressive

            # pi 3 - state 0x400000 [LCD], 800x480 @ 60.00Hz, progressive

            #     tvservice
            #     name
            # 0 - MainLCD - official DSI touchscreen
            # 1 -         - Auxilliary LCD ?whats this
            # 2 - HDMI0 -   HDMI port 0
            #             - HDMI,  deprecated, resolves to HDMI0 (2)
            # 3 - Composite  - TV
            # 4 -         - Force LCD
            # 5 -         - Force TV
            # 6 -         - Force non-default display
            # 7 - HDMI1   - HDMI Port 1

            # get dimensions of this display from tvservice
            command=['tvservice','-s','-v'+ disp_id]
            s_reply=subprocess.run(command,stdout=subprocess.PIPE)
            s_reply_list=s_reply.stdout.decode('utf-8').split(',')
            s_tt_list=s_reply_list[1].strip().split(' ')
            s_dim_list=s_tt_list[0].split('x')
            # get real display width and height
            DisplayManager.real_display_width[int(disp_id)]=int(s_dim_list[0])
            DisplayManager.real_display_height[int(disp_id)]=int(s_dim_list[1])
            # display width and height as modified by --screensize0/1
            if options['screensize'+str(line-1)] =='':
                DisplayManager.display_width[int(disp_id)]=int(s_dim_list[0])
                DisplayManager.display_height[int(disp_id)]=int(s_dim_list[1])     
            else:
                reason,message,DisplayManager.display_width[int(disp_id)],DisplayManager.display_height[int(disp_id)]=self.parse_screensize(options['screensize'+str(line-1)])
                if reason =='error':
                    return 'error',message
        return 'normal',''


    # set the touch scale for the official touchscreen
    def set_touch_scale(self,position,left_display,right_display):

        if self.model<4:
            # for < Model 4 touchscreen scale is not influenced by presence of HDMI display
            args_single= ['xinput', 'set-prop', 'FT5406 memory based driver', '--type=float', 'Coordinate Transformation Matrix',
            '1', '0', '0', '0', '1', '0', '0' ,'0' ,'1']
            if 0 in DisplayManager.displays:
                # do only for DSI0 not for HDMI0
                subprocess.call(args_single)
                return
        # Pi 4    
        elif DisplayManager.num_displays==2:
            # print (DisplayManager.real_display_width[left_display],DisplayManager.real_display_width[right_display])
            c00 =str(DisplayManager.real_display_width[left_display]/(DisplayManager.real_display_width[right_display]+DisplayManager.real_display_width[left_display]))
            c12= str(DisplayManager.real_display_height[left_display]/max(DisplayManager.real_display_height[left_display],DisplayManager.real_display_height[right_display]))
            args_left= ['xinput', 'set-prop', 'FT5406 memory based driver', '--type=float', 'Coordinate Transformation Matrix',
                c00, '0', '0', '0',c12, '0', '0' ,'0' ,'1']
                
        else:
            args_single= ['xinput', 'set-prop', 'FT5406 memory based driver', '--type=float', 'Coordinate Transformation Matrix',
            '1', '0', '0', '0', '1', '0', '0' ,'0' ,'1']
            
        if position == 'single':
            if 0 in DisplayManager.displays:
                # do only for DSI0 not for HDMI0
                subprocess.call(args_single)
        else:
            if 0 in DisplayManager.displays:
                # do only for DSI0 not for HDMI0
                subprocess.call(args_left)
        

    def parse_screensize(self,size_text):
        fields=size_text.split('*')
        if len(fields)!=2:
            return 'error','do not understand --screensize comand option',0,0
        elif fields[0].isdigit()  is False or fields[1].isdigit()  is False:
            return 'error','dimensions are not positive integers in --screensize',0,0
        else:
            return 'normal','',int(fields[0]),int(fields[1])


## awk '/^Revision/ {sub("^1000", "", $3); print $3}' /proc/cpuinfo 

    def pi_model(self):
        command=['cat', '/proc/device-tree/model']
        l_reply=subprocess.run(command,stdout=subprocess.PIPE)
        l_reply_list=l_reply.stdout.decode('utf-8').split(' ')
        return int(l_reply_list[2])
    
            
    def print_displays(self):
        print ('Pi Model',self.model)
        print ('Number of Displays',DisplayManager.num_displays)
        print ('Displays Connected',DisplayManager.displays)
        print ('Development Display',self.develop_id)
        print ('Display Dimensions - real',DisplayManager.real_display_width,DisplayManager.real_display_height)
        print ('Window x offset',DisplayManager.window_x_offset)
        print ('Window Dimensions - non-full',DisplayManager.window_width,DisplayManager.window_height)
        print ('Display Dimensions - screensize',DisplayManager.display_width,DisplayManager.display_height)
        print ('Canvas Widget',DisplayManager.canvas_obj)
        print ('Canvas Dimensions',DisplayManager.canvas_width,DisplayManager.canvas_height)
        print ('Maps',DisplayManager.display_map,DisplayManager.display_reverse_map)

# **************************
# Test Harness
# **************************

# dummy debug monitor
class Mon(object):
    
    def err(self,inst,message):
        print (message)

    def log(self,inst,message):
        print (message)


class PiPresents(object):

    def __init__(self):
        
        self.mon=Mon()
        self.ref0=None
        self.ref1=None
                
        # ********************
        # SET UP THE GUI
        # ********************
        
        #self.options={'screensize0':'400*400','screensize1':'400*400','fullscreen':False}
        self.options={'screensize0':'','screensize1':'','fullscreen':False}
        

        # set up the displays and create a canvas for each display
        self.dm=DisplayManager()
        status,message,self.root=self.dm.init(self.options,self.end)
        if status !='normal':
            self.mon.err(self,message)
            sys.exit(111) 
            
        self.canvas0=None
        self.canvas1=None

        status,message,self.dsi_id,canvas_id=self.dm.id_of_canvas('DSI0')
        if status == 'normal':
            self.canvas0=canvas_id
            self.canvas0.create_text(20,0,anchor=NW,text='F4 to close',fill='yellow')
            self.canvas0.create_text(20,20,anchor=NW,text='display id: ' + str(self.dsi_id),fill='yellow')
            self.canvas0.create_text(20,40,anchor=NW,text='canvas for this display:  ' + str(self.canvas0),fill='yellow')  
            width0,height0=self.dm.canvas_dimensions(self.dsi_id)
            self.canvas0.create_text(width0/2,height0/2,text='*',fill='yellow')
            # self.canvas0.bind('<Button-1>',self.click_pressed)
            self.canvas0.bind('<Motion>',self.click_pressed)
            self.canvas0.bind("<F4>", self.end_event)
        
        status,message,self.hdmi0_id,canvas_id=self.dm.id_of_canvas('HDMI0')
        if status == 'normal':
        
            self.canvas1=canvas_id
            width1,height1=self.dm.canvas_dimensions(self.hdmi0_id)
            self.canvas1.create_text(20,20,anchor=NW,text='F4 to close',fill='yellow') 
            self.canvas1.create_text(20,40,anchor=NW,text='display id: ' + str(self.hdmi0_id),fill='yellow')
            self.canvas1.create_text(20,60,anchor=NW,text='canvas for this display:  ' + str(self.canvas1),fill='yellow')            
            self.canvas1.create_text(width1/2,height1/2,text='*',fill='yellow')
            self.canvas1.bind('<Motion>',self.click_pressed)
            # self.canvas1.bind('<Button-1>',self.click_pressed)
            self.canvas1.bind("<F4>", self.end_event)
            
        status,message,self.hdmi1_id,canvas_id=self.dm.id_of_canvas('HDMI1')
        if status == 'normal':
            # reuse canvas0 because cannot have DSI0 and HDMI0
            self.canvas0=canvas_id
            self.canvas0.create_text(20,20,anchor=NW,text='F4 to close',fill='yellow')
            self.canvas0.create_text(20,40,anchor=NW,text='display id: ' + str(self.hdmi1_id),fill='yellow')
            self.canvas0.create_text(20,60,anchor=NW,text='canvas for this display:  ' + str(self.canvas0),fill='yellow')  
            width3,height3=self.dm.canvas_dimensions(self.hdmi1_id)
            self.canvas0.create_text(width3/2,height3/2,text='*',fill='yellow')
            # self.canvas0.bind('<Button-1>',self.click_pressed)
            self.canvas0.bind('<Motion>',self.click_pressed)
            self.canvas0.bind("<F4>", self.end_event)
        
        # start Tkinters event loop
        self.root.mainloop( )

    def click_pressed(self,event):
        x= event.x
        y= event.y
        text = str(x) + " " + str(y)
        if self.canvas0 != None:
            if self.ref0 !=None:
                self.canvas0.delete(self.ref0)
            self.ref0=self.canvas0.create_text(100,100,anchor=NW,text=text,fill='yellow')
        if self.canvas1 != None:       
            if self.ref1 !=None:
                self.canvas1.delete(self.ref1)
            self.ref1=self.canvas1.create_text(100,100,anchor=NW,text=text,fill='yellow')
            

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
    
