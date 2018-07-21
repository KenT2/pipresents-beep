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
        if len(fields) != 2:
            return "incorrect number of fields in beep "+line,['','']
        symbol=fields[0]
        beep_file=fields[1]
        location=self.complete_path(beep_file)
        if not os.path.exists(location):
            return 'beep file does not exist: '+ location,['','']
        else:
            return '',[symbol,location]
  

    def handle_input_event(self,symbolic_name,beeps_list):
        for beep in beeps_list:
            if symbolic_name== beep[0]:
                self.do_beep(beep[1])
                return

    def complete_path(self,track_file):
        #  complete path of the filename of the selected entry
        if track_file != '' and track_file[0]=="+":
            track_file=BeepsManager.pp_home+track_file[1:]
        elif track_file[0] == "@":
            track_file=BeepsManager.pp_profile+track_file[1:]
        return track_file 

    def do_beep(self,path):
        # print 'Beep '+path
        self.mon.log(self,'Do Beep: '+ path)
        fields = path.split('.')
        if fields[1] == 'mp3':
            os.system("mpg123 -q " + path)
        else:
            os.system("aplay -q " + path)


