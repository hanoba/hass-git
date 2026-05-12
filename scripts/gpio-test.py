#!/usr/bin/python3

import time
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
 
# Broadcom Layout verwenden (wie GPIO-Nummern)
GPIO.setmode(GPIO.BCM)

# GPIO 22 auf Output setzen
PIN1=27   #4
PIN2=17
T=0.01
GPIO.setup(PIN1, GPIO.OUT)
GPIO.setup(PIN2, GPIO.OUT)

# Dauersschleife
while 1:
  GPIO.output(PIN1, GPIO.LOW)
  GPIO.output(PIN2, GPIO.HIGH)
  time.sleep(T)

  GPIO.output(PIN1, GPIO.HIGH)
  GPIO.output(PIN2, GPIO.LOW)
  time.sleep(T)
