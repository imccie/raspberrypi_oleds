# -*- coding: utf-8 -*-
#
# !!! Needs psutil installing:
#
#    $ sudo pip install psutil
#
import time
import os
import sys
if os.name != 'posix':
    sys.exit('platform not supported')
import psutil

from datetime import datetime
from oled.device import ssd1306, sh1106,ssd1351
from oled.render import canvas
from PIL import ImageDraw, ImageFont
import Adafruit_GPIO.SPI as SPI
# TODO: custom font bitmaps for up/down arrows
# TODO: Load histogram

def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n

def cpu_usage():
    # load average, uptime
    uptime = datetime.now() - datetime.fromtimestamp(psutil.BOOT_TIME)
    av1, av2, av3 = os.getloadavg()
    return "Ld:%.1f %.1f %.1f Up: %s" \
            % (av1, av2, av3, str(uptime).split('.')[0])

def mem_usage():
    usage = psutil.phymem_usage()
    return "Mem: %s %.0f%%" \
            % (bytes2human(usage.used), 100 - usage.percent)


def disk_usage(dir):
    usage = psutil.disk_usage(dir)
    return "SD:  %s %.0f%%" \
            % (bytes2human(usage.used), usage.percent)

def network(iface):
    stat = psutil.network_io_counters(pernic=True)[iface]
    return "%s: Tx%s, Rx%s" % \
           (iface, bytes2human(stat.bytes_sent), bytes2human(stat.bytes_recv))

def stats(oled,i):
    font = ImageFont.load_default()
    font = ImageFont.truetype("/usr/share/fonts/truetype/msyhl.ttc",12)
    font2 = ImageFont.truetype('../fonts/C&C Red Alert [INET].ttf', 12)
    with canvas(oled) as draw:
        draw.text((i, 0), cpu_usage(), font=font2, fill=255)
        draw.text((i, 14), mem_usage(), font=font2, fill=255)
        draw.text((i, 26), disk_usage('/'), font=font2, fill=255)
        draw.text((i, 38), network('wlan0'), font=font2, fill=255)
        draw.text((i, 50), u"当前系统时间"+time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())),font=font, fill=255)

def main():
    oled = sh1106(dc=25, spi=SPI.SpiDev(0, 0, max_speed_hz=8000000))
    i=0
    t=False
    while True:
        stats(oled,i)
        time.sleep(0.01)
	if t==False:
		i=i-1
	if t==True:
		i=i+1
        if i<-100:
		t=True
	if i==0:
		t=False

if __name__ == "__main__":
    main()
