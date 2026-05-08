#!/usr/bin/python3

import time
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
 
# Broadcom Layout verwenden (wie GPIO-Nummern)
GPIO.setmode(GPIO.BCM)

# GPIO 22 auf Output setzen
GPIO.setup(22, GPIO.OUT)

# Dauersschleife
while 1:
  # Relais ausschalten und 1 Sekunde warten
  GPIO.output(22, GPIO.LOW)
  time.sleep(1)
    # Relais ausschalten und 1 Sekunde warten
  GPIO.output(22, GPIO.HIGH)
  time.sleep(1)
