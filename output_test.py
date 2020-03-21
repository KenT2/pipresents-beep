#! /usr/bin/env python3

"""
!!!! THIS PROGRAM COULD DAMAGE YOUR PI IF GPIO IS NOT CORRECTLY CONNECTED
To Run - python3 output_test.py from a terminal window

Out of the box no outputs change state.
The commented out pins = [......] statement is a list of all the pins that can be used by Pi Presents
Modify the uncommented pins = [] to add the pins to be toggled.

Running the program will change the state of the selected pins every 3 seconds
A log will be written to the terminal window.
To exit type CTRL-C
 
"""

# pins=[3,5,7,8,10,11,12,13,15,16,18,19, 21, 22, 23, 24, 26,29,31,32,33,35,36,37,38,40]

pins=[]

import sys
if sys.version_info[0] != 3:
        sys.stdout.write("ERROR: Pi Presents requires python 3\nHint: python3 output_test.py .......\n")
        exit(102)

import RPi.GPIO as GPIO
from time import sleep


def write_pins(value):
    for pin in pins:
        print('Pin ',pin,value)
        GPIO.output(pin,value)


ON_VALUE= GPIO.HIGH
OFF_VALUE=GPIO.LOW



GPIO.setwarnings(False)
GPIO.cleanup()

GPIO.setmode(GPIO.BOARD)

if pins == []:
    print ('ERROR: No pins selected\nRead the instructions by opening output_test.py in an editor\n')
    exit()

for pin in pins:
    GPIO.setup(pin,GPIO.OUT)

while True:
        print('\n***** ON ******')
        write_pins(ON_VALUE)
        sleep (3)
        print('\n***** OFF *****')
        write_pins(OFF_VALUE)
        sleep(3)



