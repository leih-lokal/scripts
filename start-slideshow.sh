#!/bin/bash

# Convert PDF to pictures
# pdftoppm -png /home/pi/slideshow/raspberry-pi-fenster.pdf /home/pi/slideshow/

# Start slideshow
feh -Y -x -q -D 5 -B black -F -Z -z -r slideshow/

### OLD ###
# (Okular stopped working on Pi due to some shared library error)
# sleep 5
# counter=1
# while [ $counter -le 5 ]
# do
#    sleep 3
#        sudo -u pi okular /home/pi/raspberry-pi-fenster.pdf --presentation
# done
#
# echo Abgestürzt, bitte Stecker ziehen und neu einstecken.
# read EINGABE
