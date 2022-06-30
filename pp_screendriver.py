import os
import configparser
import copy
from tkinter import NW,CENTER
from PIL import Image
from PIL import ImageTk
from pp_utils import Monitor
from pp_displaymanager import DisplayManager

class ScreenDriver(object):
    image_obj=[]

    
    def __init__(self):
        self.mon=Monitor()
        self.dm=DisplayManager()
    


    # read screen.cfg    
    def read(self,pp_dir,pp_home,pp_profile):
        self.pp_dir=pp_dir
        self.pp_home=pp_home
        # try inside profile
        tryfile=pp_profile+os.sep+'pp_io_config'+os.sep+'screen.cfg'
        # self.mon.log(self,"Trying screen.cfg in profile at: "+ tryfile)
        if os.path.exists(tryfile):
            filename=tryfile
        else:
            #give congiparser an empty filename so it returns an empty config.
            filename=''
        ScreenDriver.config = configparser.ConfigParser(inline_comment_prefixes = (';',))
        ScreenDriver.config.read(filename)
        if filename != '':
            self.mon.log(self,"screen.cfg read from "+ filename)
        return 'normal','screen.cfg read'

    def click_areas(self):
        return ScreenDriver.config.sections()

    def get(self,section,item):
        return ScreenDriver.config.get(section,item)

    def is_in_config(self,section,item):
        return ScreenDriver.config.has_option(section,item)


    def parse_displays(self,text):
        return text.split(' ')
    
    # make click areas on the screen, bind them to their symbolic name, and create a callback if it is clicked.
    # click areas must be polygon as outline rectangles are not filled as far as find_closest goes
    # canvas is the PiPresents canvas
    
    def make_click_areas(self,callback):
        # called once at start
        #click_area_ids = dict()   #disctionary of ids access by click area name
        # contains - canvas_ids   list of canvases for the click area one for each display. used to index the other lists
        #            poly_ids     list of polygon objects with nones. one for each display
        #            image_ids    as above
        #            text_ids     as above

        #print (self.click_areas())
        self.callback=callback
        reason=''
        ScreenDriver.image_obj=[]
        ScreenDriver.click_area_names=[]
        ScreenDriver.canvas_ids=[]
        ScreenDriver.poly_ids=[]
        ScreenDriver.image_ids=[]
        ScreenDriver.text_ids=[]
        for area in self.click_areas():

            #print ('\nNAME',self.get(area,'name'))
            if not self.is_in_config(area,'displays'):
                reason='error'
                message='missing displays field in screen.cfg'
                break            
            displays_list=self.parse_displays(self.get(area,'displays'))
            # print ('\n\n',displays_list)
            reason,message,points = self.parse_points(self.get(area,'points'),self.get(area,'name'))
            if reason == 'error':
                break

            # calculate centre of polygon
            vertices = len(points)//2
            #print (area, 'vertices',vertices)
            sum_x=0
            sum_y=0
            for i in range(0,vertices):
                #print (i)
                sum_x=sum_x+int(points[2*i])
                #print (int(points[2*i]))
                sum_y=sum_y+int(points[2*i+1])
                #print (int(points[2*i+1]))
            polygon_centre_x=sum_x/vertices
            polygon_centre_y=sum_y/vertices
            
            for display_name in DisplayManager.display_map:
                if display_name in displays_list:
                    status,message,display_id,canvas=self.dm.id_of_canvas(display_name)
                    if status!='normal':
                        continue
                    ScreenDriver.click_area_names.append(area)
                    ScreenDriver.canvas_ids.append(canvas)
                    #print (display_id,canvas)
                    polygon_id=canvas.create_polygon(points,
                                               fill=self.get (area,'fill-colour'),
                                               outline=self.get (area,'outline-colour'),
                                               tags=("pp-click-area",self.get(area,'name')),
                                               state='hidden')
                    #print ('polygon',polygon_id,area,self.get(area,'name'),display_id,canvas)
                    ScreenDriver.poly_ids.append(polygon_id)
                    # image for the button
                    if not self.is_in_config(area,'image'):
                        reason='error'
                        message='missing image fields in screen.cfg'
                        break
                    image_name=self.get(area,'image')
                    if image_name !='':
                        image_width = int(self.get(area,'image-width'))
                        image_height = int(self.get(area,'image-height'))
                        image_path=self.complete_path(image_name)
                        if os.path.exists(image_path) is True:
                            self.pil_image=Image.open(image_path)
                        else:
                            image_path=self.pp_dir+os.sep+'pp_resources'+os.sep+'button.jpg'
                            if os.path.exists(image_path) is True:
                                self.mon.warn(self,'Default button image used for '+ area)
                                self.pil_image=Image.open(image_path)
                            else:
                                self.mon.warn(self,'Button image does not exist for '+ area)
                                self.pil_image=None
                                
                        if self.pil_image is not None:
                            self.pil_image=self.pil_image.resize((image_width-1,image_height-1))                 
                            photo_image_id=ImageTk.PhotoImage(self.pil_image)
                            # print (display_id, canvas,self.pil_image,photo_image_id,self.get(area,'name'))
                            image_id=canvas.create_image(polygon_centre_x,polygon_centre_y,
                                                     image=photo_image_id,
                                                     anchor=CENTER,
                                                    tags=('pp-click-area',self.get(area,'name')),
                                                    state='hidden')
                            del self.pil_image
                            ScreenDriver.image_obj.append(photo_image_id)
                            ScreenDriver.image_ids.append(image_id)
                            # print (ScreenDriver.image_obj)
                    else:
                        image_id=None
                        ScreenDriver.image_ids.append(None)
                    #print ('image',image_id)
                    # write the label at the centroid
                    if self.get(area,'text') != '':
                        text_id=canvas.create_text(polygon_centre_x,polygon_centre_y,
                                                text=self.get(area,'text'),
                                                fill=self.get(area,'text-colour'),
                                                font=self.get(area,'text-font'),
                                                tags=('pp-click-area',self.get(area,'name')),
                                                state='hidden')
                        ScreenDriver.text_ids.append(text_id)
                        #print ('text',text_id)
                    else:
                        ScreenDriver.text_ids.append(None)
                    canvas.bind('<Button-1>',self.click_pressed)
        if reason == 'error':
            return 'error',message
        else:
            # print('\nnames',ScreenDriver.click_area_names)
            # print('\ncanvas',ScreenDriver.canvas_ids)
            # print('\npoly',ScreenDriver.poly_ids)
            # print('\nimage',ScreenDriver.image_ids)
            # print('\ntext',ScreenDriver.text_ids)
            return 'normal','made click areas'

                                        
     # callback for click on screen
    def click_pressed(self,event):
        x= event.x
        y=event.y
        # fail to correct the pointer position on touch so set for mouse click
        # x,y,text=self.dm.correct_touchscreen_pointer(event,0,False)

        overlapping =  event.widget.find_overlapping(x-5,y-5,x+5,y+5)
        for item in overlapping:
            # print ScreenDriver.canvas.gettags(item)
            if ('pp-click-area' in event.widget.gettags(item)) and event.widget.itemcget(item,'state') == 'normal':
                self.mon.log(self, "Click on screen: "+ event.widget.gettags(item)[1])
                self.callback(event.widget.gettags(item)[1],'SCREEN')
                # need break as find_overlapping returns two results for each click, one with 'current' one without.
                break

    def is_click_area(self,test_area,canvas):
        click_areas=canvas.find_withtag('pp-click-area')
        #print ('click areas - ids',click_areas)
        for area in click_areas:
            if test_area in canvas.gettags(area):
                # print('test area link',test_area,'is in click areas for canvas',canvas)
                return True
        return False
                                                      

    # use links with the symbolic name of click areas to enable the click areas in a show
    def enable_click_areas(self,links,canvas):
        for link in links:
            if self.is_click_area(link[0],canvas) and link[1] != 'null':
                status,poly_id,image_id,text_id=self.ids_of_click_area(link[0],canvas)
                # print ('enabling click area ',link[0],status,poly_id,image_id,text_id)
                canvas.itemconfig(poly_id,state='normal')
                if image_id != None:
                    canvas.itemconfig(image_id,state='normal')
                if text_id != None:
                    canvas.itemconfig(text_id,state='normal')

    def hide_click_areas(self,links,canvas):
        # hide  click areas
        for link in links:
            if self.is_click_area(link[0],canvas) and link[1] != 'null':
                status,poly_id,image_id,text_id=self.ids_of_click_area(link[0],canvas)
                # print ('disabling click area ',link[0],status,poly_id,image_id,text_id)
                canvas.itemconfig(poly_id,state='hidden')
                if image_id != None:
                    canvas.itemconfig(image_id,state='hidden')
                if text_id != None:
                    canvas.itemconfig(text_id,state='hidden')


        # this does not seem to change the colour of the polygon
        # ScreenDriver.canvas.itemconfig('pp-click-area',state='hidden')
        canvas.update_idletasks( )

    def ids_of_click_area(self,area_name,canvas):
        #print (ScreenDriver.click_area_names)
        for index,name in enumerate(ScreenDriver.click_area_names):
            if area_name==name and ScreenDriver.canvas_ids[index]==canvas:
                # print (index,name,canvas)
                return True,ScreenDriver.poly_ids[index],ScreenDriver.image_ids[index],ScreenDriver.text_ids[index]
        print ('!!!! ERROR, click area lookup failed',area_name,canvas)
        return false,None,None,None
        

    def parse_points(self,points_text,area):
        if points_text.strip() == '':
            return 'error','No points in click area: '+area,[]
        if '+' in points_text:
            # parse  x+y+width*height
            fields=points_text.split('+')
            if len(fields) != 3:
                return 'error','Do not understand click area points: '+area,[]
            dimensions=fields[2].split('*')
            if len(dimensions)!=2:
                return 'error','Do not understand click area points: '+area,[]
            
            if not fields[0].isdigit():
                return 'error','x1 is not a positive integer in click area: '+area,[]
            else:
                x1=int(fields[0])
            
            if not fields[1].isdigit():
                return 'error','y1 is not a positive integer in click area: '+area,[]
            else:
                y1=int(fields[1])
                
            if not dimensions[0].isdigit():
                return 'error','width1 is not a positive integer in click area: '+area,[]
            else:
                width=int(dimensions[0])
                
            if not dimensions[1].isdigit():
                return 'error','height is not a positive integer in click area: '+area,[]
            else:
                height=int(dimensions[1])

            return 'normal','',[str(x1),str(y1),str(x1+width),str(y1),str(x1+width),str(y1+height),str(x1),str(y1+height)]
            
        else:
            # parse unlimited set of x,y,coords
            points=points_text.split()
            if len(points) < 6:
                return 'error','Less than 3 vertices in click area: '+area,[]
            if len(points)%2 != 0:
                return 'error','Odd number of points in click area: '+area,[]      
            for point in points:
                if not point.isdigit():
                    return 'error','point is not a positive integer in click area: '+area,[]
            return 'normal','parsed points OK',points


    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=self.pp_home+track_file[1:]
        elif track_file[0] == "@":
            track_file=self.pp_profile+track_file[1:]
        return track_file   
