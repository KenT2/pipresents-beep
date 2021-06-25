import time
import copy
import os
import configparser
import pigpio
from pp_utils import Monitor
import subprocess


class pp_pigpiodriver(object):
    """
   pp_pigpiodriver provides GPIO facilties for Pi presents
      - based on pigpio not RPI.GPIO so has improved de-bouncing and faster under high load conditions
     - configures and binds GPIO pins from data in .cfg file 
     - reads and debounces inputs pins, provides callbacks on state changes which generate input events
     - generates repeated events if buttons held in one state.
    - changes the state of output pins as required by calling programs
    """
 
 
# constants for buttons

# configuration from pigpio.cfg
    PIN=0                # pin on RPi board GPIO connector e.g. P1-11 >11
    DIRECTION = 1 # in/out/none
    NAME = 2      # symbolic name for output
    RISING_NAME=3             # symbolic name of rising edge inout event
    FALLING_NAME=4      # symbolic name of falling edge input event
    ONE_NAME=5     # symbolic name of one state input event
    ZERO_NAME = 6   # symbolic name of zero state input event
    REPEAT =  7   # number of tick intervals between repeated state events If zero or blank then repeats are disabled
    STEADY = 8       # input must be steady for this number of milliseconds for a state change to be registered.
    PULL = 9                  # internal pullup up/down/none
    LINKED_NAME = 10     # symbolic name of output pin that follows the input
    LINKED_INVERT = 11   # invert the linked pin
    
# derived
    BCM=12               #GPIO/BCM number of  pin

# dynamic data
    PRESSED = 13     # variable - debounced state true if 0 volts
    REPEAT_COUNT = 14 # counter of tick intervals for repeat.

    
    TEMPLATE = ['',   # pin
                '',              # direction
                '',              # name
                '','','','',       #input names
                0,             # repeat 
                0,             # steady
                '',             #pull
                '',             #linked pin
                False,          # linked invert
                0,              #BCM
                False,0]   #dynamics
    
# for A and B
#    PINLIST = ('P1-03','P1-05','P1-07','P1-08',
#               'P1-10','P1-11','P1-12','P1-13','P1-15','P1-16','P1-18','P1-19',
#               'P1-21','P1-22','P1-23','P1-24','P1-26')

# for A+ and B+ seems to work for A and B
    PINLIST = ('P1-03','P1-05','P1-07','P1-08',
               'P1-10','P1-11','P1-12','P1-13','P1-15','P1-16','P1-18','P1-19',
               'P1-21','P1-22','P1-23','P1-24','P1-26',
                'P1-29','P1-31','P1-32','P1-33','P1-35','P1-36','P1-37','P1-38','P1-40')


    # !!!!FOR TYPE 3  - 40 pin GPIO socket (board revision 16 or greater)
    # Requires remapping for earlier versions of Pi
    BOARDMAP = {'P1-03':2,'P1-05':3,'P1-07':4,'P1-08':14,
               'P1-10':15,'P1-11':17,'P1-12':18,'P1-13':27,'P1-15':22,'P1-16':23,'P1-18':24,'P1-19':10,
               'P1-21':9,'P1-22':25,'P1-23':11,'P1-24':8,'P1-26':7,
                'P1-29':5,'P1-31':6,'P1-32':12,'P1-33':13,'P1-35':19,'P1-36':16,'P1-37':26,'P1-38':20,'P1-40':21}



# CLASS VARIABLES  (pp_pigpiodriver.)
    BACKMAP= {}    #index to pins list from bcm number which is received from pigpio 
    pins=[]         # list to hold a list of config/dynamic data for each pin, held in the order of PINLIS which is arbriatary
    driver_active=False
    title=''
    

    # executed by main program and by each object using gpio
    def __init__(self):
        self.mon=Monitor()


     # executed once from main program   
    def init(self,filename,filepath,widget,pp_dir,pp_home,pp_profile,button_callback=None):
        # instantiate arguments
        self.widget=widget
        self.filename=filename
        self.filepath=filepath
        self.button_callback=button_callback
        pp_pigpiodriver.driver_active = False
        self.tick_interval_timer=None

        # read gpio.cfg file.
        reason,message=self._read(self.filename,self.filepath)
        if reason =='error':
            return 'error',message
        if self.config.has_section('DRIVER') is False:
            return 'error','No DRIVER section in '+self.filepath
        
        #read information from DRIVER section
        pp_pigpiodriver.title=self.config.get('DRIVER','title')
        button_tick_text = self.config.get('DRIVER','tick-interval')
        if button_tick_text.isdigit():
            if int(button_tick_text)>0:
                self.button_tick=int(button_tick_text)  # in mS
            else:
                return 'error','tick-interval is not a positive integer'
        else:
            return 'error','tick-interval is not an integer'            

        
        # construct the GPIO pin list from the configuration file
        for index, pin_def in enumerate(pp_pigpiodriver.PINLIST):
            pin=copy.deepcopy(pp_pigpiodriver.TEMPLATE)
            pin_bits = pin_def.split('-')
            pin_num=pin_bits[1:]
            pin[pp_pigpiodriver.PIN]=int(pin_num[0])
            if self.config.has_section(pin_def) is False:
                self.mon.warn(self, "no pin definition for "+ pin_def)
                pin[pp_pigpiodriver.DIRECTION]='None'            
            else:
                pin[pp_pigpiodriver.BCM]=pp_pigpiodriver.BOARDMAP[pin_def]
                # create back map
                pp_pigpiodriver.BACKMAP[pin[pp_pigpiodriver.BCM]]=index 
                           
                # unused pin
                if self.config.get(pin_def,'direction') == 'none':
                    pin[pp_pigpiodriver.DIRECTION]='none'
                else:

                    pin[pp_pigpiodriver.DIRECTION]=self.config.get(pin_def,'direction')
                    if pin[pp_pigpiodriver.DIRECTION] == 'in':
                        # input pin
                        pin[pp_pigpiodriver.RISING_NAME]=self.config.get(pin_def,'rising-name')
                        pin[pp_pigpiodriver.FALLING_NAME]=self.config.get(pin_def,'falling-name')
                        pin[pp_pigpiodriver.ONE_NAME]=self.config.get(pin_def,'one-name')
                        pin[pp_pigpiodriver.ZERO_NAME]=self.config.get(pin_def,'zero-name')

                        if self.config.has_option(pin_def,'linked-output'):
                            # print self.config.get(pin_def,'linked-output')
                            pin[pp_pigpiodriver.LINKED_NAME]=self.config.get(pin_def,'linked-output')
                            if  self.config.get(pin_def,'linked-invert') == 'yes':
                                pin[pp_pigpiodriver.LINKED_INVERT]=True
                            else:
                                pin[pp_pigpiodriver.LINKED_INVERT]=False
                        else:
                            pin[pp_pigpiodriver.LINKED_NAME]= ''
                            pin[pp_pigpiodriver.LINKED_INVERT]=False
                                               
                        if pin[pp_pigpiodriver.FALLING_NAME] == 'pp-shutdown':
                           pp_pigpiodriver.shutdown_index=index
                        if self.config.get(pin_def,'repeat') != '':
                            pin[pp_pigpiodriver.REPEAT]=int(self.config.get(pin_def,'repeat'))
                        else:
                            pin[pp_pigpiodriver.REPEAT]=-1
                        pin[pp_pigpiodriver.STEADY]=int(self.config.get(pin_def,'steady'))*1000
                        
                        if self.config.get(pin_def,'pull-up-down') == 'up':
                            pin[pp_pigpiodriver.PULL]=pigpio.PUD_UP
                        elif self.config.get(pin_def,'pull-up-down') == 'down':
                            pin[pp_pigpiodriver.PULL]=pigpio.PUD_DOWN
                        else:
                            pin[pp_pigpiodriver.PULL]=pigpio.PUD_OFF
                    else:
                        # output pin
                        pin[pp_pigpiodriver.NAME]=self.config.get(pin_def,'name')
            
            pp_pigpiodriver.pins.append(copy.deepcopy(pin))
            
        #self.print_pins()

        # start pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected:
            return 'error',pp_pigpiodriver.title + ' daemon not running\nHint: sudo pigpiod'

        # set up the GPIO inputs and outputs
        for index, pin in enumerate(pp_pigpiodriver.pins):
            bcm = pin[pp_pigpiodriver.BCM]
            if pin[pp_pigpiodriver.DIRECTION] == 'in':
                self.pi.set_mode(bcm,pigpio.INPUT)
                self.pi.set_pull_up_down(bcm,pin[pp_pigpiodriver.PULL])
                self.pi.set_glitch_filter(bcm, pin[pp_pigpiodriver.STEADY])
                self.pi.callback(bcm, pigpio.EITHER_EDGE,self.event_callback)
                #print ('in',bcm, pin[pp_pigpiodriver.STEADY])
                
            elif  pin[pp_pigpiodriver.DIRECTION] == 'out':
                self.pi.set_mode(bcm,pigpio.OUTPUT)
                self.pi.write(bcm,0)
                #print ('OUT',bcm)
                
        self._reset_input_state()
        
        pp_pigpiodriver.driver_active=True

        # init timer
        self.tick_Interval_timer=None
        return 'normal',pp_pigpiodriver.title + ' active'

    def print_pins(self):
        for pin in pp_pigpiodriver.pins:
            print (pin)
        print (pp_pigpiodriver.BACKMAP)


    # called by main program only         
    def start(self):
        # loop to handle repeating buttons
        self._do_repeat()
        self.tick_interval_timer=self.widget.after(self.button_tick,self.start)


    # called by main program only                
    def terminate(self):
        if pp_pigpiodriver.driver_active is True:
            if self.tick_interval_timer is not None:
                self.widget.after_cancel(self.tick_interval_timer)
            self._reset_outputs()
            self.pi.stop()
            pp_pigpiodriver.driver_active=False


# ************************************************
# gpio input functions
# called by main program only
# ************************************************
    
    def _reset_input_state(self):
        for pin in pp_pigpiodriver.pins:
            pin[pp_pigpiodriver.PRESSED]=False
            if pin[pp_pigpiodriver.ZERO_NAME]!='' or pin[pp_pigpiodriver.ONE_NAME]!='':
                pin[pp_pigpiodriver.REPEAT_COUNT]=pin[pp_pigpiodriver.REPEAT]
            else:
                pin[pp_pigpiodriver.REPEAT_COUNT]=-1
            if pin[pp_pigpiodriver.LINKED_NAME] != '':
                linked_pin=self._output_pin_of(pin[pp_pigpiodriver.LINKED_NAME])
                if linked_pin!=-1:
                    linked_bcm=pp_pigpiodriver.pins[linked_pin][pp_pigpiodriver.BCM] 
                    print (linked_pin,linked_bcm,False, pp_pigpiodriver.pins[linked_pin][pp_pigpiodriver.LINKED_INVERT])
                    self.pi.write(linked_bcm,False ^ pin[pp_pigpiodriver.LINKED_INVERT])
 

    def event_callback(self,bcm,level,tick):
        # convert bcm back to index to pins list
        pin=pp_pigpiodriver.BACKMAP[bcm]
        #print (pin,bcm,level,tick)
        
        # callback on edges
        if pp_pigpiodriver.pins[pin][pp_pigpiodriver.DIRECTION] == 'in':
            if level==0:
                pp_pigpiodriver.pins[pin][pp_pigpiodriver.PRESSED]=True
                if pp_pigpiodriver.pins[pin][pp_pigpiodriver.ZERO_NAME]!='':
                    pp_pigpiodriver.pins[pin][pp_pigpiodriver.REPEAT_COUNT]=pp_pigpiodriver.pins[pin][pp_pigpiodriver.REPEAT]
                else:
                    pp_pigpiodriver.pins[pin][pp_pigpiodriver.REPEAT_COUNT]=-1
                                      
                if  pp_pigpiodriver.pins[pin][pp_pigpiodriver.FALLING_NAME] != '' and self.button_callback  is not  None:
                    self.button_callback(pp_pigpiodriver.pins[pin][pp_pigpiodriver.FALLING_NAME],pp_pigpiodriver.title)
            else:
                # rising edge
                pp_pigpiodriver.pins[pin][pp_pigpiodriver.PRESSED]=False
                if pp_pigpiodriver.pins[pin][pp_pigpiodriver.ONE_NAME]!='':
                    pp_pigpiodriver.pins[pin][pp_pigpiodriver.REPEAT_COUNT]=pp_pigpiodriver.pins[pin][pp_pigpiodriver.REPEAT]
                else:
                    pp_pigpiodriver.pins[pin][pp_pigpiodriver.REPEAT_COUNT]=-1
                if  pp_pigpiodriver.pins[pin][pp_pigpiodriver.RISING_NAME] != '' and self.button_callback  is not  None:
                    self.button_callback(pp_pigpiodriver.pins[pin][pp_pigpiodriver.RISING_NAME],pp_pigpiodriver.title)


            # linked pin
            if pp_pigpiodriver.pins[pin][pp_pigpiodriver.LINKED_NAME] != '':
                linked_pin=self._output_pin_of(pp_pigpiodriver.pins[pin][pp_pigpiodriver.LINKED_NAME])
                if linked_pin!=-1:
                    linked_bcm=pp_pigpiodriver.pins[linked_pin][pp_pigpiodriver.BCM] 
                    # print(linked_pin, linked_bcm, pp_pigpiodriver.pins[linked_pin][pp_pigpiodriver.PRESSED], pp_pigpiodriver.pins[linked_pin][pp_pigpiodriver.LINKED_INVERT])
                    self.pi.write(linked_bcm, pp_pigpiodriver.pins[pin][pp_pigpiodriver.PRESSED] ^ pp_pigpiodriver.pins[pin][pp_pigpiodriver.LINKED_INVERT])
  

    def _do_repeat(self):
        for index, pin in enumerate(pp_pigpiodriver.pins):
            if pin[pp_pigpiodriver.DIRECTION] == 'in' and pin[pp_pigpiodriver.REPEAT]>0 and pin[pp_pigpiodriver.REPEAT_COUNT]>-1:
                # print ('repeat pin', pin)
                # do state callbacks
                if pin[pp_pigpiodriver.REPEAT_COUNT] == 0:
                    if pin[pp_pigpiodriver.ZERO_NAME] != '' and pin[pp_pigpiodriver.PRESSED] is True and self.button_callback is not None:
                        self.button_callback(pin[pp_pigpiodriver.ZERO_NAME],pp_pigpiodriver.title)
                    if pin[pp_pigpiodriver.ONE_NAME] != '' and pin[pp_pigpiodriver.PRESSED] is False and self.button_callback is not None:
                        self.button_callback(pin[pp_pigpiodriver.ONE_NAME],pp_pigpiodriver.title)
                    pin[pp_pigpiodriver.REPEAT_COUNT]=pin[pp_pigpiodriver.REPEAT]
                else:
                    if pin[pp_pigpiodriver.REPEAT] != -1:
                        pin[pp_pigpiodriver.REPEAT_COUNT]-=1

    def get_input(self,channel):
            return False, None



# ************************************************
# gpio output interface methods
# these can be called from many classes so need to operate on class variables
# ************************************************                            

    # execute an output event

    def handle_output_event(self,name,param_type,param_values,req_time):
        # print 'GPIO handle',name,param_type,param_values
        # does the symbolic name match any output pin
        pin= self._output_pin_of(name)
        if pin  == -1:
            return 'normal',pp_pigpiodriver.title + 'Symbolic name not recognised: ' + name
        
        #gpio only handles state parameters, ignore otherwise
        if param_type != 'state':
            return 'normal',pp_pigpiodriver.title + ' does not handle: ' + param_type
        
        to_state=param_values[0]
        if to_state not in ('on','off'):
            return 'error',pp_pigpiodriver.title + ', illegal parameter value for ' + param_type +': ' + to_state

        if to_state== 'on':
            state=1
        else:
            state=0
        bcm = pp_pigpiodriver.pins[pin][pp_pigpiodriver.BCM]
        #print ('pin P1-'+ str(pin)+ ' set  '+ str(state) + ' required: ' + str(req_time)+ ' actual: ' + str(int(time.time())))
        self.pi.write(bcm,state)
        return 'normal',pp_pigpiodriver.title + ' pin P1-'+ str(pin)+ ' set  '+ str(state) + ' required at: ' + str(req_time)+ ' sent at: ' + str(int(time.time()))


    def _reset_outputs(self):
        if pp_pigpiodriver.driver_active is True:
            for index, pin in enumerate(pp_pigpiodriver.pins):
                bcm = pin[pp_pigpiodriver.BCM]
                if pin[pp_pigpiodriver.DIRECTION] == 'out':
                    self.pi.write(bcm,0)


    def is_active(self):
        return pp_pigpiodriver.driver_active

# ************************************************
# internal functions
# these can be called from many classes so need to operate on class variables
# ************************************************


    def _output_pin_of(self,name):
        for index, pin in enumerate(pp_pigpiodriver.pins):
            #print (" in list" + pin[pp_pigpiodriver.NAME] + str(pin[pp_pigpiodriver.PIN] ))
            if pin[pp_pigpiodriver.NAME] == name and pin[pp_pigpiodriver.DIRECTION] == 'out':
                #print (" linked pin " + pin[pp_pigpiodriver.NAME] + ' ' + str(index))
                return index
        return -1



# ***********************************
# reading .cfg file
# ************************************

    def _read(self,filename,filepath):
        if os.path.exists(filepath):
            self.config = configparser.ConfigParser(inline_comment_prefixes = (';',))
            self.config.read(filepath)
            return 'normal',filename+' read'
        else:
            return 'error',filename+' not found at: '+filepath



if __name__ == '__main__':
    from tkinter import *
    
    def button_callback(symbol,source):
        print('callback',symbol,source)
        if symbol=='pp-stop':
            idd.terminate()
            exit()
        pass

    root = Tk()

    w = Label(root, text="pigpio based driver test harness")
    w.pack()

    idd=pp_pigpiodriver()
    reason,message=idd.init('gpio.cfg','/home/pi/pipresents/pp_resources/pp_templates/pigpio.cfg',root,
    '/home/pi/pipresents','/home/pi/pp_home','x',button_callback)
    print(reason,message)
    idd.start()
    root.mainloop()

