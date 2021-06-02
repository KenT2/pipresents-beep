import os
from tkinter import Tk, StringVar,Frame,Label,Button,Scrollbar,Listbox,Entry,Text
from tkinter import Y,END,TOP,BOTH,LEFT,RIGHT,VERTICAL,SINGLE,NONE,NORMAL,DISABLED
import glob, os, shutil, time


class LiveListFetcher():
    
    """
    MODE (modify in code below) 
    async - updates to the live tracks directory will take place while the liveshow
            is running, potentially during playing of the track.
            This is the old behaviour. No special protocol is required but there is risk of
            the liveshow reporting an error and PP stopping.

           
    sync - files are moved from a cache directory into the live tracks directory 2.
    only between playing of the tracks so problems should  not occur.
    
    Syncing is only available for Live Tracks Directory 2. The location of this directory
    can be set in the profile or in the -l command line option.
    
    First change the mode, create a cache directory, and tell PP about it by modifying the code below.
    
    For syncing the protocol below is required:

        Place the required new tracks in the cache directory
        create a file named .lock in the cache directory.
        PP tests .lock between each track. If present:
            PP deletes all the tracks from the Live Tracks 2 directory and
            moves the new tracks from the cache directory to the Live Tracks 2 directory
            PP will then delete the .lock file
    
    The sender must not update the cache directory while the .lock file is present.
    
    Provided the two directories are on the same filesystem move is a very fast
     operation as it only changes directory entries and does not copy the files.
     Otherwise a copy may be performed which may be too slow for the reason
    described in the next paragraph.
     
    You could have a more sophisticated update_tracks() technique but it must be fast
     as it is a blocking operation and the remainder of PP, being cooperatively scheduled,
      may not like being blocked for more than a few mS.
      Experiment with your particular application
    """
    
    mode = 'async'
    # mode = 'sync'
    cache_dir = '/home/pi/PPCache/' 

    def __init__(self):
        # called at the start of a Liveshow or Artliveshow (they use the same Livelist Class)
        return
    
    def live_tracks(self,dir1,dir2):
        #called at start of liveshow or artliveshow to pass the directories
        # create_new_livelist tests both directories for changes
        # but uploader only use live_dir2
        # if the path does not exist then do not use it
        self.pp_live_dir = dir2
        
        # initial population of livelist from cache
        if os.path.exists(LiveListFetcher.cache_dir):
            if LiveListFetcher.mode == 'sync':
                if self.detect_signal(LiveListFetcher.cache_dir,'lock') is True:
                    self.update_tracks()
                    self.send_signal(LiveListFetcher.cache_dir,'lock',False)
                    return
            # self.send_signal(LiveListFetcher.cache_dir,'lock',False)


    def fetch_livelist(self):
        
        # called after each track by create_new_livelist()
        if LiveListFetcher.mode == 'async':
            # no lock protocol so just return
            # print ('async')
            return

        if not os.path.exists(LiveListFetcher.cache_dir):
            # no cache directory, just return
            return
                
        if LiveListFetcher.mode == 'sync':
            if self.detect_signal(LiveListFetcher.cache_dir,'lock') is True:
                self.update_tracks()
                self.send_signal(LiveListFetcher.cache_dir,'lock',False)
                return
        else:
             print('unknown Live List Fetcher mode: '+ LiveListFetcher.mode )
             return                  
    
    
    def update_tracks(self):
        #time.sleep(5)         # see what happens if the update takes a long time
        paths = glob.glob(self.pp_live_dir +'/*')
        for f in paths:
            # print ('deleting',f)
            os.remove(f)
        source_dir = LiveListFetcher.cache_dir 
        dest = self.pp_live_dir +'/'  
        files = os.listdir(source_dir)
        for f in files:
            if f[0] != '.':
                # print ('MOVING', f)
                shutil.move(source_dir+f, dest)

        
    def send_signal(self,directory,signal,state):
        if state == True:
            try:
                f = open(directory+'.'+signal,'x').close()
                # print ('sent ',directory,signal,state)
            except:
                # print(directory + '.'+ signal+ ' already exists')
                pass
        else:
            if os.path.exists(directory +'.'+signal):
                os.remove(directory + '.'+signal)
                # print ('sent ',directory,signal,state)
            else:
                # print( directory+'.'+signal+ ' already deleted')
                pass
        

    def detect_signal(self,directory,signal):
        if os.path.exists(directory+'.'+signal):
            # print (signal, 'is True')
            return True
        else:
            # print (signal, 'is False')
            return False

                
# **************************
# Test harness
# **************************

# !!!! create a cache directory first !!!
# and uncomment the print statements.


class PiPresents(object):


    def __init__(self):
        # root is the Tkinter root widget
        self.root = Tk()
        self.root.title("Livelist Fetcher")
        self.root.resizable(False,False)

        # define response to main window closing
        self.root.protocol ("WM_DELETE_WINDOW", self.app_exit)
        self.root.bind('<Break>',self.app_exit)


        self.llf=LiveListFetcher()
        self.llf.live_tracks('','/home/pi/pp_home/pp_live_tracks')
        
        self.root.after(1,self.do_track_loop)
        self.root.mainloop()
        
    def app_exit(self,event=None):
        self.root.destroy()
        exit()
        
    def do_track_loop(self):   
        self.llf.fetch_livelist()
        self.root.after(5000,self.do_track_loop)
        
if __name__ == '__main__':
    pp= PiPresents()
    
    
