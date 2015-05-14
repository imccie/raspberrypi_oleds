# -*- coding: utf-8 -*-
#----------------------------------------------------------------------
# ssd1351.py from https://github.com/boxysean/py-gaugette
# ported by boxysean
#
# This library works with 
#   Adafruit's 128x128 SPI RGB OLED   https://www.adafruit.com/products/1431
#
# The code is based heavily on Adafruit's Arduino library
#   https://github.com/adafruit/Adafruit-SSD1351-library
# written by Limor Fried/Ladyada for Adafruit Industries.
#
# Some important things to know about this device and SPI:
#
# SPI and GPIO calls are made through an abstraction library that calls
# the appropriate library for the platform.
# For the RaspberryPi:
#     wiring2
#     spidev
#
# Presently untested / not supported for BBBlack
#
#----------------------------------------------------------------------

import ssd1351 as ssd
import time
import Image
import ImageFont
import ImageDraw
import math
import numpy
import commands
import os

def get_cpu_temp():
    tempFile = open( "/sys/class/thermal/thermal_zone0/temp" )
    cpu_temp = tempFile.read()
    tempFile.close()
    return float(cpu_temp)/1000


def get_gpu_temp():
    gpu_temp = commands.getoutput( '/opt/vc/bin/vcgencmd measure_temp' ).replace( 'temp=',''  ).replace('\'C', '' )
    return  float(gpu_temp)
    # Uncomment the next line if you want the temp in Fahrenheit
    # return float(1.8* gpu_temp)+32
# Color definitions
BLACK    = 0x0000
BLUE     = 0x001F
RED      = 0xF800
GREEN    = 0x07E0
CYAN     = 0x07FF
MAGENTA  = 0xF81F
YELLOW   = 0xFFE0 
WHITE    = 0xFFFF

disp = ssd.SSD1351()
disp.begin()
c = 0

# Create image buffer.
# Make sure to create image with mode '1' for 1-bit color.
#image = Image.new('1', (128, 128))

im=Image.open("/home/test.jpg")
imi=im.convert('RGB')
disp.image(list(imi.getdata()))
time.sleep(30)
image = Image.new('RGB',(128,128))

# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.
# Some nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('Minecraftia.ttf', 8)

# Create drawing object.
draw = ImageDraw.Draw(image)

# Define text and get total width.
text = 'wujing7@chinaunicom.cn http://www.chinaunicom.cn'
maxwidth, unused = draw.textsize(text, font=font)
# Set animation and sine wave parameters.
amplitude = 128/4
offset = 128/2 - 4
velocity = -2
startpos = 128

# Animate text moving in sine wave.
print 'Press Ctrl-C to quit.'
pos = startpos
ii=128
ic=0
icc=0
fps=0
siz=12
col=1
font2 = ImageFont.truetype("/usr/share/fonts/truetype/msyhl.ttc",siz)

while True:
    #if col<=65530:
    #    col=col+100
    #else:
    #    col=1#
#
 #   print col
    #break
    # Clear image buffer by drawing a black filled box.

    draw.rectangle((0,0,128,128), outline=0, fill=0x000000)
    # Enumerate characters and draw them offset vertically based on a sine wave.
    x = pos
    #text=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
    text=time.strftime("%S",time.localtime(time.time()))
    if text=="10":
        icc=0
    else:
        icc=icc+1
        if ic<=icc:
            ic=icc
    fps=ic/60
    #text=u"我最最亲爱的妮妮,我爱你到永远!爱你的老爸."
    text=os.popen('uptime').read()
    #runs=os.popen('uptime')
    #text=text+str(runs)
    for i, c in enumerate(text):
        # Stop drawing if off the right side of screen.
        if x > 128:
            break
        # Calculate width but skip drawing if off the left side of screen.
        if x < -10:
            char_width, char_height = draw.textsize(c, font=font2)
            x += char_width
            continue
        # Calculate offset from sine wave.
        y = offset+math.floor(amplitude*math.sin(x/float(128)*4*math.pi))
        # Draw text.
        draw.text((x, y), c, font=font2, fill=4321)

        # Increment x position based on chacacter width.
        char_width, char_height = draw.textsize(c, font=font2)
        x += char_width

    # Draw the image buffer.

    draw.text((ii,100),u"当前系统时间"+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))+str(ii),font=font2,fill=43220)
    draw.text((0,0),"CPU:"+str(get_cpu_temp())+",GPU:"+str(get_gpu_temp()),font=font,fill=43215)
    draw.text((0,8),"af="+str(ic)+",ic="+str(icc)+",f="+str(fps),font=font,fill=54321)
    ii=ii-1
    if ii<=-228:
        ii=126
    disp.normal_display()
    pix=list(image.getdata())
    disp.image(pix)
    #disp.image(pix[:128*64])
    #disp.image(numpy.array(image))

    #disp.display()
    # Move position for next frame.
    pos += velocity
    # Start over if text has scrolled completely off left side of screen.
    if pos < -maxwidth:
        pos = startpos
    # Pause briefly before drawing next frame.
    #time.sleep(1)


while True:
   # disp.clear_display()
   # disp.draw_text(0,0,'wujing 2015 2010',0xFF00FF) # should be purple
    #disp.draw_text3(64,0,"test form cc",ImageFont.load_default())

    # disp.dump_buffer()
    #disp.command(0xa4)
   # time.sleep(2)
    break
    disp.clear_display()
    print 'red'
    disp.fillScreen(0xFF0000) # this really is red
    time.sleep(0.001)

    disp.clear_display()
    print 'green'
    disp.fillScreen(0x00ff00)
    time.sleep(0.001)
    
    disp.clear_display()
    print 'blue'
    # disp.fillScreen(0b000000000000000011111111)
    disp.fillScreen(0x0000ff)
    time.sleep(0.001)

    disp.clear_display()
    print 'white'
    # disp.fillScreen(0b000000000000000011111111)
    disp.fillScreen(0xffffff)
    time.sleep(0.001)



