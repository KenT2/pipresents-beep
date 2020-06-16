import os
import copy
from pp_utils import Monitor

class BeepsManager(object):

    pp_home=''
    pp_profile=''

    def __init__(self):
        self.mon=Monitor()

    def init(self,pp_home,pp_profile):
        BeepsManager.pp_home=pp_home
        BeepsManager.pp_profile = pp_profile
        
    #  parse beeps from beeps field in a show
    def parse_beeps(self,beeps_text):
        beeps=[]
        lines = beeps_text.split('\n')
        num_lines=0
        for line in lines:
            if line.strip() == '':
                continue
            num_lines+=1
            error_text,beep=self.parse_beep(line.strip())
            if error_text != '':
                return 'error',error_text,beeps
            beeps.append(copy.deepcopy(beep))
        return 'normal','',beeps

    def parse_beep(self,line):
        fields = line.split()
        if len(fields) not in (2,3) :
            return "incorrect number of fields in beep "+line,['','']
        symbol=fields[0]
        beep_file=fields[1]
        if len(fields) == 3:
            device=fields[2]
        else:
            device=''
        location=self.complete_path(beep_file)
        if not os.path.exists(location):
            return 'beep file does not exist: '+ location,['','']
        else:
            return '',[symbol,location,device]
  

    def handle_input_event(self,symbolic_name,beeps_list):
        for beep in beeps_list:
            if symbolic_name== beep[0]:
                self.do_beep(beep[1],beep[2])
                return

    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=BeepsManager.pp_home+track_file[1:]
        elif track_file[0] == "@":
            track_file=BeepsManager.pp_profile+track_file[1:]
        return track_file 


    def do_beep(self,path,device):
        self.mon.log(self,'Do Beep: '+ path + ' ' +device)
        #print ('play beep',path,device)
        # determine which audio system is in use, linux system was introduced in May 2020
        # The test of .asoundrc does not work if there is a USB sound card plugged in
        if os.path.exists ('/home/pi/.asoundrc'):        
            audio_sys='linux'
        else:
            audio_sys='pi'
            
        #uncomment to force old audio system
        #audio_sys='pi'
        
        if audio_sys=='pi':
            #print ('old audio',device)
            if device != "":
                if device in ('hdmi','hdmi0'):
                    os.system("amixer -q -c 0 cset numid=3 2")
                elif device == 'hdmi1':
                    os.system("amixer -q -c 0 cset numid=3 3")                    
                elif device in ('local','A/V'):
                    os.system("amixer -q -c 0 cset numid=3 1")
            fields = path.split('.')
            if fields[1] == 'mp3':
                #print ('old mp3')
                os.system('mpg123 -q '+ path)
            else:
                #print ('old aplay')
                os.system("aplay -q " + path)
        else:
            # new audio
            fields = path.split('.')
            if fields[1] != 'mp3':
                driver_option=''
                #print ('device',device)
                if device != "":
                    if device in ('hdmi','hdmi0'):
                        driver_option=' -D plughw:b1 '
                    elif device == 'hdmi1':
                        driver_option=' -D plughw:b2 '
                    elif device in ('USB','alsa'):
                        driver_option=' -D plughw:Device '
                    elif device in ('A/V','local'):
                        driver_option=' -D plughw:Headphones '
                    else:
                        driver_option = ''
                #print ('new audio wav',device,driver_option)
                os.system("aplay -q " + driver_option + ' ' + path)
            else:
                driver_option=''
                if device != "":
                    if device in ('hdmi','hdmi0'):
                        driver_option=' -o alsa:plughw:b1 '
                    elif device == 'hdmi1':
                        driver_option=' -o alsa:plughw:b2 '
                    elif device in ('USB','alsa'):
                        driver_option=' -o alsa:plughw:Device '
                    elif device in ('A/V','local'):
                        driver_option=' -o alsa:plughw:Headphones '
                    else:
                        driver_option = ''
                #print ('new audio mp3',driver_option)
                os.system('mpg123 -q '+ driver_option + ' ' + path)
