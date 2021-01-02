import os
import copy
from pp_utils import Monitor
from pp_audiomanager import AudioManager

class BeepPlayer(object):

    pp_home=''
    pp_profile=''

    def __init__(self):
        self.mon=Monitor()

    def init(self,pp_home,pp_profile):
        BeepPlayer.pp_home=pp_home
        BeepPlayer.pp_profile = pp_profile



    def play_animate_beep(self,location,device):
        # check location
        path=self.complete_path(location)
        if not os.path.exists(path):
            return 'error','beep file does not exist: '+ path

        status,message=self.do_beep(path,device)
        if status=='error':
            return 'error',message
        return 'normal',''



    def play_show_beep(self,command_text):
        fields = command_text.split()
        if len(fields) not in (2,3) :
            return 'error',"incorrect number of fields in beep command" + line
        symbol=fields[0]
        location=fields[1]
        if len(fields) == 3:
            device=fields[2]
        else:
            device=''

        path=self.complete_path(location)
        if not os.path.exists(path):
            return 'error','beep file does not exist: '+ path

        status,message=self.do_beep(path,device)
        if status == 'error':
            return 'error',message
        return 'normal',''



    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=BeepPlayer.pp_home+track_file[1:]
        elif track_file[0] == "@":
            track_file=BeepPlayer.pp_profile+track_file[1:]
        return track_file


    def do_beep(self,path,device):
        self.am=AudioManager()
        self.mon.log(self,'Do Beep: '+ path + ' ' +device)

        #print ('play beep',path,device)
        audio_sys=self.am.get_audio_sys()

        if audio_sys=='cset':
            #print ('cset',device)
            if device != "":
                if device in ('hdmi','hdmi0'):
                    os.system("amixer -q -c 0 cset numid=3 2")
                elif device == 'hdmi1':
                    os.system("amixer -q -c 0 cset numid=3 3")
                elif device in ('local','A/V'):
                    os.system("amixer -q -c 0 cset numid=3 1")
            fields = path.split('.')
            if fields[1] == 'mp3':
                #print ('cset mp3')
                os.system('mpg123 -q '+ path)
            else:
                #print ('cset aplay')
                os.system("aplay -q " + path)
            return 'normal',''

        elif audio_sys=='alsa':
            #print ('alsa',device)
            # alsa audio
            fields = path.split('.')
            if fields[1] != 'mp3':
                # other than mp3
                driver_option=''
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
                #print ('alsa wav',device,driver_option)
                os.system("aplay -q " + driver_option + ' ' + path)

            else:   #mp3
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
                #print ('alsa mp3',driver_option)
                os.system('mpg123 -q '+ driver_option + ' ' + path)

            return 'normal',''

        elif audio_sys == "pulse":

            status,message,sink=self.am.get_sink(device)
            if status =='error':
                return 'error',message
            if not self.am.sink_connected(sink):
                return 'error','sound device not connected - '+device
            fields = path.split('.')
            if fields[1] != 'mp3':
                # other than mp3
                if sink != '':
                    driver_option=' --device='+ sink +' --stream-name=pipresents '
                else:
                    driver_option=' --stream-name=pipresents '
                #print ('pulse wav',device)
                os.system('paplay ' + driver_option + path)
                return 'normal',''
            else:
                #mp3
                if sink =='':
                    driver_option = ' -o pulse '
                else:
                    driver_option= ' -o pulse -a ' + sink
                #print ('pulse mp3',device)
                command = 'mpg123 -q ' + driver_option + ' ' + path
                # print (command)
                os.system (command)
                return 'normal',''

        else:
            print ('bad audio system',audio_sys)
            return 'error','bad audio system'



