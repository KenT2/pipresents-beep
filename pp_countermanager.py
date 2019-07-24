import os
import configparser

class CounterManager(object):



    # *******************************************************************
    # use these functions to access the value of a counter or counters
    # *******************************************************************
    
    def get_counter(self,name):
        if name not in CounterManager.counters:
            return'error','counter does not exist - '+ name
        return 'normal',str(CounterManager.counters[name])

    def str_counters(self):
        values_string=''
        for key,value in list(CounterManager.counters.items()):
            values_string += key +' '+str(value) + '\n'
        return values_string

    # *******************************************************************
    # use this function to print all counters to the terminal window
    # *******************************************************************
    def print_counters(self):
        print('Counter Values:')
        for key,value in list(CounterManager.counters.items()):
            print('      ',key,value)

            

# **********************************************************************

    # dictionary of counter values
    counters = {}
    counters_path='' # path to file
       

    def parse_counter_command(self,fields):
        # counter name set    value
        # counter name inc    value
        # counter name dec    value
        # counter name delete

        if len(fields) < 2:
                return'error','too few fields in counter command - ' + ' '.join(fields)            
        name=fields[0]
        command=fields[1]
        
        if command =='set':
            value=fields[2]
            if not value.isdigit():
                return'error','value is not a positive integer - ' + ' '.join(fields)
            CounterManager.counters[name]=int(value)
            self.save_counters()
            # self.print_command(fields)
            # self.print_counters()

            return 'normal',''
        
        elif command in ('inc','dec'):
            if name not in CounterManager.counters:
                return'error','counter does not exist - '+ ' '.join(fields)
            value=fields[2]
            if not value.isdigit():
                return'error','value is not a positive integer - '+ ' '.join(fields)

            if command=='inc':
                CounterManager.counters[name]+=int(value)
            else:
                CounterManager.counters[name]-=int(value)
            self.save_counters()
            # self.print_command(fields)
            # self.print_counters()
            return 'normal','' 
            
        
        elif command =='delete':
            if name not in CounterManager.counters:
                return'normal','counter does not exist - '+ ' '.join(fields)
            del CounterManager.counters[name]
            self.save_counters()
            # self.print_command(fields)
            # self.print_counters()
            return 'normal',''
        
        else:
            return'error','illegal counter comand - '+ ' '.join(fields)


            

    def print_command(self,fields):
        print('\nCounter Command: ' + ' '.join(fields))


    def init(self,counters_path,store_enable,load,counter_data):
        CounterManager.store_enable=store_enable
        CounterManager.counters_path=counters_path
        if store_enable is False:
            # just clear the counters
            CounterManager.counters.clear()
            # print ('store = false just clear')
            return 'normal','store not enabled - counters cleared'
        else:
            # storing
            if load is True:
                # load the content of the file from start show
                #create an empty counters file if it does not exist
                if  not os.path.exists(counters_path):
                    #create the file
                    f=open(counters_path,'w')
                    f.close()
                # create a file to store counters and init it
                config=configparser.ConfigParser(inline_comment_prefixes = (';',))
                config.add_section('counters')
                with open(counters_path,'w') as f:
                    config.write(f)
                    #add the text from the counters field of the profile
                    f.write(counter_data)
                    # print('store and load - file written')
            else:
                # load false
                # print ('load false, store true -  do nothing')
                if  not os.path.exists(counters_path):
                    return 'error','counter file not found '+ counters_path
            return self.read_counters(counters_path)



    def read_counters(self,counters_path):
        config=configparser.ConfigParser(inline_comment_prefixes = (';',))
        if not os.path.exists(CounterManager.counters_path):
            return 'error','Counter file not found - '+ CounterManager.counters_path
        try:
            config.read(CounterManager.counters_path)
        except configparser.Error as e:
            return 'error',str(e)
        if config.has_section('counters'):
            for item in config.items('counters'):
                key=item[0]
                val=item[1]
                try:
                    intval=int(val)
                except:
                    return 'error', 'counter value is not an integer '+ val
                CounterManager.counters[key]=intval
            return 'normal','counter file read '+ CounterManager.counters_path
        else:
            # print ('section missing')
            return 'error','counters section not found'

            
    def save_counters(self):
        if CounterManager.store_enable is True:
            config=configparser.ConfigParser(inline_comment_prefixes = (';',))
            config.add_section('counters')
            for key in CounterManager.counters.keys():
                config.set('counters', key, str(CounterManager.counters[key]))
            with open (CounterManager.counters_path,'w') as f:
                config.write(f)
                # print ('write counters path '+CounterManager.counters_path)
            return 'normal','counter file written '+ CounterManager.counters_path
        else:
            return 'normal','counters not saved'



if __name__ == '__main__':
    cm=CounterManager()
    # cm.init_store('/home/pi/counters.cfg')
    print (cm.init('/home/pi/counters/counters.cfg',True,True,'fred =1\nbill=-1'))
    cm.print_counters()
    status,message=cm.save_counters()
    print (status + ': ' + message)
