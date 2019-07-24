PI PRESENTS  - Version 1.4.3
============================

This repository contains the latest and greatest version Pi Presents. Use if you are happy with bleeding edge software that is under development.

VERSION 1.4.3 IS PYTHON 3


TO INSTALL PIPRESENTS-BEEP
=============================

Read the 'Installing Pi Presents Beep' section below.



TO UPGRADE FROM EARLIER VERSIONS OF PIPRESENTS-BEEP or PIPRESENTS-GAPLESS
======================================================
To upgrade follow the instructions in the 'Updating Pi Presents' section below. Then follow any instructions in the Release Notes.


PI PRESENTS
===========

Pi Presents is a toolkit for producing interactive multimedia applications for museums, visitor centres, and more.

There are a number of Digital Signage solutions for the Raspberry Pi which are generally browser based, limited to slideshows, non-interactive, and driven from a central server enabling the content to be modified frequently.

Pi Presents is different, it is stand alone, multi-media, highly interactive, diverse in it set of control paradigms – slideshow, cursor controlled menu, radio button, and hyperlinked show, and able to interface with users or machines over several types of interface. It is aimed primarly at curated applications in museums, science centres, and visitor centres.

Being so flexible Pi Presents needs to be configured for your application. This is achieved using a simple to use graphical editor and needs no Python programming. There are numerous tutorial examples and a comprehensive manual.

There are two current versions of Pi Presents. ‘Gapless’ is the current stable version which is not being developed except for bug fixes. 'Beep' is a continuation of Gapless which is being developed to add new features.

For a detailed list of applications and features see here:

          https://pipresents.wordpress.com/features/



Licence
=======

See the licence.md file. Pi Presents is Careware to help support a small museum charity of which I am a Trustee http://www.museumoftechnology.org.uk  Particularly if you are using Pi Presents in a profit making situation a donation would be appreciated.


Installing Pi Presents Beep
===============================

The full manual in English is here https://github.com/KenT2/pipresents-beep/blob/master/manual.pdf. It will be downloaded with Pi Presents.


Requirements
-------------

	* must use the latest version of Raspbian Stretch or Buster with Desktop (not the Lite version)
	* must be run from the PIXEL desktop.
	* must be installed and run from user Pi
        * must have Python 3 installed (which Raspbian does)


Set the GPU Memory size to 256MB
---------------------------------
Using the Raspbian menu preferences>raspberry pi configuration>performance, increase the GPU Memory to 256.


Ensure Raspbian is up to date.
-------------------------------
Pi Presents MUST have the latest version of omxplayer and of Raspbian, get this by

		sudo apt-get update
		sudo apt-get upgrade

Install required packages 
-----------------------------
         sudo apt-get install python3-pil.imagetk
         sudo apt-get install unclutter
         sudo apt-get install mplayer
         sudo apt-get install uzbl
         sudo apt-get install python3-pexpect
		 
Install optional packages
------------------------------
         sudo pip3 install evdev  (if you are using the input device I/O plugin)
         sudo apt-get install mpg123 (for .mp3 beeps)

	   
Download Pi Presents Beep
----------------------------

From a terminal window open in your home directory type:

         wget https://github.com/KenT2/pipresents-beep/tarball/master -O - | tar xz     # -O is a capital Ohhh...

There should now be a directory 'KenT2-pipresents-beep-xxxx' in your /home/pi directory. Copy or rename the directory to pipresents

Run Pi Presents to check the installation is successful. From a terminal window opened in the home directory type:

         python3 /home/pi/pipresents/pipresents.py

You will see a window with an error message which is because you have no profiles.Click OK to exit Pi Presents.


Download and try an Example Profile
-----------------------------------

Examples are in the github repository pipresents-beep-examples.

Open a terminal window in your home directory and type:

         wget https://github.com/KenT2/pipresents-beep-examples/tarball/master -O - | tar xz

There should now be a directory 'KenT2-pipresents-beep-examples-xxxx' in the /home/pi directory. Open the directory and move the 'pp_home' directory and its contents to the /home/pi directory.

From the terminal window type:

         python3 /home/pi/pipresents/pipresents.py -p pp_mediashow_1p4
		 
to see a repeating multimedia show

Exit this with CTRL-BREAK or closing the window, then:

          python3 /home/pi/pipresents/pipresents.py -p pp_mediashow_1p4 -f -b
		  
to display full screen and to disable screen blanking


Now read the manual to try other examples.


Updating Pi Presents from earlier Versions of Pi Presents Beep or Pi Presents Gapless
======================================================================================

Install Python 3 version of some packages:

      sudo apt-get install python3-pil.imagetk
      sudo apt-get install python3-pexpect
      sudo pip3 install evdev

The Python 2 versions of these packages can be left installed

Open a terminal window in the /home/pi and type:

         wget https://github.com/KenT2/pipresents-beep/tarball/master -O - | tar xz

There should now be a directory 'KenT2-pipresents-beep-xxxx' in the /home/pi directory

Rename the existing pipresents directory to old-pipresents

Rename the new directory to pipresents.

Copy pp_editor.cfg, pp_web.cfg, pp_email.cfg, pp_oscmonitor.cfg, and pp_oscremote.cfg from the old to new /pipresents/pp_config directory.


Getting examples for this version.
----------------------------------

Examples are in the github repository pipresents-beep-examples.

Rename the existing pp_home directory to old_pp_home.

Open a terminal window in your home directory and type:

         wget https://github.com/KenT2/pipresents-beep-examples/tarball/master -O - | tar xz

There should now be a directory 'KenT2-pipresents-beep-examples-xxxx' in the /home/pi directory.

Open the directory and move the 'pp_home' directory and its contents to the /home/pi directory.

These examples are compatible with the version of Pi Presents you have just downloaded. In addition you can update profiles from earlier 1.4.x or 1.3.x versions by simply opening them in the editor (make a backup copy first).

You can use the update>update all menu option of the editor to update all profiles in a single directory at once.

Lastly you will need to do some manual updating of some of the field values as specified in  ReleaseNotes.txt. Start at the paragraph in ReleaseNotes.txt that introduces your previous version and work forwards



Bug Reports and Feature Requests
================================
I am keen to develop Pi Presents further and would welcome bug reports and ideas for additional features and uses.

Please use the Issues tab on Github https://github.com/KenT2/pipresents-beep/issues.

For more information on how Pi Presents is being used, Hints and Tips on how to use it and all the latest news hop over to the Pi Presents website https://pipresents.wordpress.com/

