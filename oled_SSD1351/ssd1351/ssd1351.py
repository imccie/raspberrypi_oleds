# ----------------------------------------------------------------------
# ssd1351.py from https://github.com/boxysean/py-gaugette
# ported by boxysean
# modified to work with BBB and Adafruit_BBIO and *not* gaugette by AKA
#
# This library works with 
#   Adafruit's 128x128 SPI RGB OLED   https://www.adafruit.com/products/1431
#
# The code is based heavily on Adafruit's Arduino library
#   https://github.com/adafruit/Adafruit-SSD1351-library
# written by Limor Fried/Ladyada for Adafruit Industries.
#----------------------------------------------------------------------
from __future__ import division
import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as s_SPI
import font5x8
import time
import sys


class SSD1351:
    DELAYS_HWFILL = 3
    DELAYS_HWLINE = 1
    SPI_PORT = 0
    SPI_DEVICE = 0
    # SSD1351 Commands
    CMD_SETCOLUMN = 0x15
    CMD_SETROW = 0x75
    CMD_WRITERAM = 0x5C
    CMD_READRAM = 0x5D
    CMD_SETREMAP = 0xA0
    CMD_STARTLINE = 0xA1
    CMD_DISPLAYOFFSET = 0xA2
    CMD_DISPLAYALLOFF = 0xA4
    CMD_DISPLAYALLON = 0xA5
    CMD_NORMALDISPLAY = 0xA6
    CMD_INVERTDISPLAY = 0xA7
    CMD_FUNCTIONSELECT = 0xAB
    CMD_DISPLAYOFF = 0xAE
    CMD_DISPLAYON = 0xAF
    COM_SCAN_INC = 0xC0
    COM_SCAN_DEC = 0xC8
    CMD_PRECHARGE = 0xB1
    CMD_DISPLAYENHANCE = 0xB2
    CMD_CLOCKDIV = 0xB3
    CMD_SETVSL = 0xB4
    CMD_SETGPIO = 0xB5
    CMD_PRECHARGE2 = 0xB6
    CMD_SETGRAY = 0xB8
    CMD_USELUT = 0xB9
    CMD_PRECHARGELEVEL = 0xBB
    CMD_VCOMH = 0xBE
    CMD_CONTRASTABC = 0xC1
    CMD_CONTRASTMASTER = 0xC7
    CMD_MUXRATIO = 0xCA
    CMD_COMMANDLOCK = 0xFD
    CMD_HORIZSCROLL = 0x96
    CMD_STOPSCROLL = 0x9E
    CMD_STARTSCROLL = 0x9F
    SET_COM_PINS = 0xDA

    SSD1351WIDTH = 128
    SSD1351HEIGHT = 128
    '''
    # the below are ssd1306 commands
    EXTERNAL_VCC   = 0x1
    SWITCH_CAP_VCC = 0x2
        
    SET_LOW_COLUMN        = 0x00
    SET_HIGH_COLUMN       = 0x10
    SET_MEMORY_MODE       = 0x20
    SET_COL_ADDRESS       = 0x21
    SET_PAGE_ADDRESS      = 0x22
    RIGHT_HORIZ_SCROLL    = 0x26
    LEFT_HORIZ_SCROLL     = 0x27
    VERT_AND_RIGHT_HORIZ_SCROLL = 0x29
    VERT_AND_LEFT_HORIZ_SCROLL = 0x2A
    DEACTIVATE_SCROLL     = 0x2E
    ACTIVATE_SCROLL       = 0x2F
    SET_START_LINE        = 0x40
    SET_CONTRAST          = 0x81
    CHARGE_PUMP           = 0x8D
    SEG_REMAP             = 0xA0
    SET_VERT_SCROLL_AREA  = 0xA3
    DISPLAY_ALL_ON_RESUME = 0xA4
    DISPLAY_ALL_ON        = 0xA5
    NORMAL_DISPLAY        = 0xA6
    INVERT_DISPLAY        = 0xA7
    DISPLAY_OFF           = 0xAE
    DISPLAY_ON            = 0xAF
    COM_SCAN_INC          = 0xC0
    COM_SCAN_DEC          = 0xC8
    SET_DISPLAY_OFFSET    = 0xD3
    SET_COM_PINS          = 0xDA
    SET_VCOM_DETECT       = 0xDB
    SET_DISPLAY_CLOCK_DIV = 0xD5
    SET_PRECHARGE         = 0xD9
    SET_MULTIPLEX         = 0xA8

    MEMORY_MODE_HORIZ = 0x00
    MEMORY_MODE_VERT  = 0x01
    MEMORY_MODE_PAGE  = 0x02
    '''
    # Device name will be /dev/spidev-{bus}.{device}
    # dc_pin is the data/commmand pin.  This line is HIGH for data, LOW for command.
    # We will keep d/c low and bump it high only for commands with data
    # reset is normally HIGH, and pulled LOW to reset the display

    def __init__(self, bus=0, device=0, dc_pin=25, reset_pin=17, buffer_rows=128, buffer_cols=128, rows=128, cols=128):
        self.cols = cols
        self.rows = rows
        self.buffer_rows = buffer_rows
        self.mem_bytes = self.buffer_rows * self.cols / 8  # total bytes in SSD1306 display ram
        self.dc_pin = dc_pin
        self.reset_pin = reset_pin
        self.spi = s_SPI.SpiDev(0, 0, max_speed_hz=8000000)
        self._gpio = GPIO.get_platform_gpio()
        self._rst = reset_pin
        self._gpio.setup(self._rst, GPIO.OUT)
        self._dc = dc_pin
        self._gpio.setup(self._dc, GPIO.OUT)
        self.font = font5x8.Font5x8
        self.col_offset = 0
        self.bitmap = self.SimpleBitmap(buffer_cols, buffer_rows)
        self.flipped = False

    def reset(self):
        self._gpio.set_high(self._rst)
        time.sleep(0.001)
        self._gpio.set_low(self._rst)
        time.sleep(0.010)
        self._gpio.set_high(self._rst)

    def command(self, cmd, cmddata=None):
        # already low
        #self.gpio.output(self.dc_pin, self.gpio.LOW)
        self._gpio.set_low(self._dc)
        if type(cmd) == list:
            self.spi.write(cmd)
        else:
            self.spi.write([cmd])

        if cmddata != None:
            if type(cmddata) == list:
                self.data(cmddata)
            else:
                self.data([cmddata])

    def data(self, bytes):
        #self.gpio.output(self.dc_pin, self.gpio.HIGH)
        #  chunk data to work around 255 byte limitation in adafruit implementation of writebytes
        # revisit - change to 1024 when Adafruit_BBIO is fixed.
        # max_xfer = 255 if gaugette.platform == 'beaglebone' else 1024
        # max_xfer = 1024 # whatever BBIO error existed seems fine now
        self._gpio.set_high(self._dc)
        max_xfer = 4096
        start = 0
        remaining = len(bytes)
        while remaining>0:
            count = remaining if remaining <= max_xfer else max_xfer
            remaining -= count
            #self.spi.write([200])
            self.spi.write(bytes[start:start+count])
            #self.spi.write(bytes[start:start+count])
            start += count
                #self.gpio.output(self.dc_pin, self.gpio.LOW)
        #self.spi.write([bytes])

    def image(self, image):
        pix = []
	self.goTo(0,0)
        for x,y in enumerate(image):
            if y==0:
                pix.append(0)
                pix.append(0)
            else:
                if type(y)==tuple:
                    cc=self.color565(y[0],y[1],y[2])
                    pix.append((cc >> 8))
                    pix.append(cc)
                else:
                    pix.append((y >> 8))
                    pix.append(y)

                #for x in bitmap[r]:
                #    pixels = pixels + [(x > 8) & 0xFF, x & 0xFF]
        self.command(self.CMD_SETCOLUMN, [0,127])
        self.command(self.CMD_SETROW, [0,127])
	self.command(self.CMD_WRITERAM)
        self.data(pix)


    def begin(self):
        time.sleep(0.001)  # 1ms
        self.reset()

        self.command(self.CMD_COMMANDLOCK, 0x12)  # Unlock OLED driver IC MCU interface from entering command
        self.command(self.CMD_COMMANDLOCK, 0xB1)  # Command A2,B1,B3,BB,BE,C1 accessible if in unlock state
        self.command([self.CMD_DISPLAYOFF,0x00])
        self.command([self.CMD_CLOCKDIV, 0xF1])  # 7:4 = Oscillator Frequency, 3:0 = CLK Div Ratio (A[3:0]+1 = 1..16)
        self.command(self.CMD_MUXRATIO, 0x7F)
        self.command(self.CMD_SETREMAP, 0x74) #0x74
        self.command(self.CMD_SETCOLUMN, [0x00, 0x7F])
        self.command(self.CMD_SETROW, [0x00, 0x7F])
        self.command(self.CMD_STARTLINE, 0x00)
        self.command(self.CMD_DISPLAYOFFSET, 0x00)
        self.command(self.CMD_SETGPIO, 0x00)
        self.command(self.CMD_FUNCTIONSELECT, 0x01)
        self.command([self.CMD_PRECHARGE, 0x32])
        self.command([self.CMD_VCOMH, 0x05])
        self.command(self.CMD_NORMALDISPLAY)
        self.command(self.CMD_CONTRASTABC, [0xC8, 0x80, 0xC8])
        self.command(self.CMD_CONTRASTMASTER, 0x0F)
        self.command(self.CMD_SETVSL, [0xA0, 0xB5, 0x55])
        self.command(self.CMD_SETVSL, 0xA0)
        self.command(self.CMD_PRECHARGE2, 0x01)
        self.command(self.CMD_DISPLAYON,0x01)

    def clear_display(self):
        self.bitmap.clear()

    def invert_display(self):
        self.command(self.CMD_INVERTDISPLAY)

    def flip_display(self, flipped=True):
        self.flipped = flipped
        if flipped:
            self.command(self.COM_SCAN_INC)
            self.command(self.CMD_SETREMAP, 0b10110110)
        else:
            self.command(self.COM_SCAN_DEC)
            self.command(self.SET_COM_PINS, 0x02)

    def normal_display(self):
        self.command(self.CMD_NORMALDISPLAY)

    def set_contrast(self, contrast=0x7f):
        self.command(self.SET_CONTRAST, contrast)

    def goTo(self, x, y):
        if x >= self.SSD1351WIDTH or y >= self.SSD1351HEIGHT:
            return

        # set x and y coordinate
        self.command(self.CMD_SETCOLUMN, [x, self.SSD1351WIDTH - 1])
        self.command(self.CMD_SETROW, [y, self.SSD1351HEIGHT - 1])
        self.command(self.CMD_WRITERAM)

    def scale(self, x, inLow, inHigh, outLow, outHigh):
        return int(((x - inLow) / float(inHigh) * outHigh) + outLow)

    def encode_color(self, color):
        red = (color >> 16) & 0xFF
        green = (color >> 8) & 0xFF
        blue = color & 0xFF
        print 'r g b are ', red, green, blue

        redScaled = int(self.scale(red, 0, 0xFF, 0, 0x1F))
        greenScaled = int(self.scale(green, 0, 0xFF, 0, 0x3F))
        blueScaled = int(self.scale(blue, 0, 0xFF, 0, 0x1F))

        print color, redScaled, greenScaled, blueScaled

        return (((redScaled << 6) | greenScaled) << 5) | blueScaled

    def color565(self, r, g, b):  # ints
        c = r >> 3
        c <<= 6
        c |= g >> 2
        c <<= 5
        c |= b >> 3
        return c

    def fillScreen(self, fillcolor):  # int
        self.fillRect(0, 0, self.SSD1351WIDTH, self.SSD1351HEIGHT, fillcolor)

    def fillRect(self, x, y, w, h, fillcolor):
        # Bounds check
        if x >= self.SSD1351WIDTH or y >= self.SSD1351HEIGHT:
            return

        if y + h > self.SSD1351HEIGHT:
            h = self.SSD1351HEIGHT - y - 1

        if x + w > self.SSD1351WIDTH:
            w = self.SSD1351WIDTH - x - 1

        # set location
        self.command(self.CMD_SETCOLUMN, [x, x + w - 1])
        self.command(self.CMD_SETROW, [y, y - h - 1])
        # fill!
        self.command(self.CMD_WRITERAM)

        fillcolor = self.encode_color(fillcolor)

        self.data([fillcolor >> 8, fillcolor] * (w * h))

    def drawPixel(self, x, y, color):
        if x >= self.SSD1351WIDTH or y >= self.SSD1351HEIGHT:
            return

        if x < 0 or y < 0:
            return

        color = self.encode_color(color)

        # set location
        self.goTo(x, y)
        self.data([color >> 8, color])

    def drawBitmap(self, x, y, bitmap):
        h = len(bitmap)
        w = len(bitmap[0])

        self.command(self.CMD_SETCOLUMN, [x, w])
        self.command(self.CMD_SETROW, [y, h])
        self.command(self.CMD_WRITERAM)

        pixels = []

        for r in range(y, y + h):
            if len(pixels) + 4 * w >= 1024:
                print "pixels!", pixels
                self.data(pixels)
                pixels = []

                #for x in bitmap[r]:
                #    pixels = pixels + [(x > 8) & 0xFF, x & 0xFF]

        print "pixels!", pixels
        self.data(pixels)

    # Diagnostic print of the memory buffer to stdout 
    def dump_buffer(self):
        self.bitmap.dump()

    def draw_text(self, x, y, string, color=0xFFFFFF):
        # print 'text is %s' % string
        font_bytes = self.font.bytes
        font_rows = self.font.rows
        font_cols = self.font.cols

        for c in string:
            p = ord(c) * font_cols
            for col in range(font_cols):
                mask = font_bytes[p]
                p += 1
                for row in range(8):
                    if (mask & 1) != 0:
                        self.drawPixel(x, y + row, color)
                        # self.bitmap.draw_pixel(x, y+row, self.encode_color(color))
                    else:
                        self.drawPixel(x, y + row, 0)
                        # self.bitmap.draw_pixel(x, y+row, 0)
                    mask >>= 1
                x += 1
            x += 1  # add a space between characters

    def draw_text_bg(self, x, y, string, color=0xFFFFFF, bg=0x000000):
        # print 'text is %s' % string
        font_bytes = self.font.bytes
        font_rows = self.font.rows
        font_cols = self.font.cols

        for c in string:
            p = ord(c) * font_cols
            for col in range(font_cols):
                mask = font_bytes[p]
                p += 1
                for row in range(8):
                    if (mask & 1) != 0:
                        self.drawPixel(x, y + row, color)
                        # self.bitmap.draw_pixel(x, y+row, self.encode_color(color))
                    else:
                        self.drawPixel(x, y + row, bg)
                        # self.bitmap.draw_pixel(x, y+row, 0)
                    mask >>= 1
                x += 1
            x += 1  # add a space between characters

    def draw_text2(self, x, y, string, color=0xFFFFFF, size=2, space=1):
        font_bytes = self.font.bytes
        font_rows = self.font.rows
        font_cols = self.font.cols
        for c in string:
            p = ord(c) * font_cols
            for col in range(0, font_cols):
                mask = font_bytes[p]
                p += 1
                py = y
                for row in range(0, 8):
                    for sy in range(0, size):
                        px = x
                        for sx in range(0, size):
                            if mask & 1:
                                self.bitmap.draw_pixel(px, py, self.encode_color(color))
                            else:
                                self.bitmap.draw_pixel(px, py, 0)
                            px += 1
                        py += 1
                    mask >>= 1
                x += size
            x += space

    def clear_block(self, x0, y0, dx, dy):
        self.bitmap.clear_block(x0, y0, dx, dy)

    def draw_text3(self, x, y, string, font):
        return self.bitmap.draw_text(x, y, string, font)

    def text_width(self, string, font):
        return self.bitmap.text_width(string, font)

    class SimpleBitmap:
        def __init__(self, cols, rows):
            self.rows = rows
            self.cols = cols
            # print rows, cols
            self.data = [([0] * self.cols) for i in range(self.rows)]

        def clear(self):
            for r in range(len(self.data)):
                for c in range(len(self.data[r])):
                    self.data[r][c] = 0

        # Diagnostic print of the memory buffer to stdout 
        def dump(self):
            for row in self.data:
                for col in row:
                    sys.stdout.write('X' if col else '.')
                sys.stdout.write('\n')

        def draw_pixel(self, x, y, color):
            if (x < 0 or x >= self.cols or y < 0 or y >= self.rows):
                return

            self.data[y][x] = color

        def clear_block(self, x0, y0, dx, dy):
            for x in range(x0, x0 + dx):
                for y in range(y0, y0 + dy):
                    self.draw_pixel(x, y, 0)

        def display(self, ssd1351):
            ssd1351.command(ssd1351.CMD_SETCOLUMN, [0, ssd1351.SSD1351WIDTH])
            ssd1351.command(ssd1351.CMD_SETROW, [0, ssd1351.SSD1351HEIGHT])
            ssd1351.command(ssd1351.CMD_WRITERAM)

            pixels = []

            ## something is wrong in here... not sure what!

            for r in range(ssd1351.SSD1351WIDTH):
                if len(pixels) + ssd1351.SSD1351HEIGHT >= 513:  # dump it out!
                    print "pixels!", pixels
                    ssd1351.data(pixels)
                    pixels = []

                pixels = pixels + self.data[r]

            print "pixels!", pixels
            ssd1351.data(pixels)
