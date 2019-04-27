import os

"""
Statsrecorder class interfaces to the device that is to save the the statistics records
It has been seperated from the remainder of Pi Presents so developers can use an alternative
statistice recording device e.g. Influxdb

"""


class Statsrecorder(object):
    
    stats_file=None
    delimiter=';'
    
    
    def __init__(self):
        # leave this empty, its called by every class that is monitored
        return
        
        
    def init(self,log_path):
        # called once when Pi Presents starts      
        # statistics file, open for appending so its not deleted
        bufsize=0
        if Statsrecorder.stats_file is None:
            Statsrecorder.stats_file=open(log_path+ os.sep+'pp_logs' + os.sep + 'pp_stats.txt','a',bufsize)
            sep='"'+Statsrecorder.delimiter+'"'
            
        # write header if file is empty
        if Statsrecorder.stats_file.tell()==0:
            Statsrecorder.stats_file.write('"'+'Date'+sep+'Time'+sep+'Show Type'+sep+'Show Ref'+ sep +'Show Title'+sep
                            +'Command'+sep+'Track Type'+sep+'Track Ref'+sep+'Track Title'+sep+'Location'+sep+'Profile"\n')

    def write_stats(self,current_datetime,profile,*args):
        # called to write a statistics record
        # * args = this type, this ref, this name, action, type, ref, name, location
        arg_string=''
        for arg in args:
           arg_string+= Statsrecorder.delimiter+'"'+arg + '"'
        Statsrecorder.stats_file.write ('"'+current_datetime.strftime('%Y-%m-%d') + '"' + Statsrecorder.delimiter+'"'+ current_datetime.strftime('%H:%M:%S') + '"' + arg_string + Statsrecorder.delimiter+'"'+ profile +'"'+"\n")  
        
        
        """
        show_type = args[0]
        show_ref = args[1]
        show_title = args[2]
        command = args[3]
        track_type = args[4]
        track_ref = args[5]
        track_title = args[6]
        location = args[7]
        print current_datetime,show_type,show_ref,show_title,command,track_type,track_ref,track_title,location,profile
        """

    def close(self):
        # called when Pi Presents exits for any reason.
        Statsrecorder.stats_file.close()
