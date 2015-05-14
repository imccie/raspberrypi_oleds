#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2015 Richard Hull
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Example usage:
#
#   from oled.device import ssd1306, sh1106
#   from oled.render import canvas
#   from PIL import ImageFont, ImageDraw
#
#   font = ImageFont.load_default()
#   device = ssd1306(port=1, address=0x3C)
#
#   with canvas(device) as draw:
#      draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)
#      draw.text(30, 40, "Hello World", font=font, fill=255)
#
# As soon as the with-block scope level is complete, the graphics primitives
# will be flushed to the device.
#
# Creating a new canvas is effectively 'carte blanche': If you want to retain
# an existing canvas, then make a reference like:
#
#    c = canvas(device)
#    for X in ...:
#        with c as draw:
#            draw.rectangle(...)
#
# As before, as soon as the with block completes, the canvas buffer is flushed
# to the device

import smbus
import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI

class device(object):
    """
    Base class for OLED driver classes
    """

    def __init__(self, port=1, address=0x3C, cmd_mode=0x00, data_mode=0x40):
        self.cmd_mode = cmd_mode
        self.data_mode = data_mode
        self.bus = smbus.SMBus(port)
        self.addr = address

    def command(self, *cmd):
        """
        Sends a command or sequence of commands through to the
        device - maximum allowed is 32 bytes in one go.
        """
        assert(len(cmd) <= 32)
        self.bus.write_i2c_block_data(self.addr, self.cmd_mode, list(cmd))

    def data(self, data):
        """
        Sends a data byte or sequence of data bytes through to the
        device - maximum allowed in one transaction is 32 bytes, so if
        data is larger than this it is sent in chunks.
        """
        for i in xrange(0, len(data), 32):
            self.bus.write_i2c_block_data(self.addr,
                                          self.data_mode,
                                          list(data[i:i+32]))

class device_spi(object):
    """
    Base class for OLED driver classes
    """

    def __init__(self, width=128, height=64, dc=None, sclk=None, din=None, cs=None,
				 gpio=None, spi=None ):
        self._spi = None
        self.width = width
        self.height = height
        self._pages = height/8
        self._buffer = [0]*(width*self._pages)
        # Default to platform GPIO if not provided.
        self._gpio = gpio
        if self._gpio is None:
            self._gpio = GPIO.get_platform_gpio()
        # Setup reset pin.
        if spi is not None:
            #self._log.debug('Using hardware SPI')
            self._spi = spi
            self._spi.set_clock_hz(8000000)
        # Handle software SPI
        if self._spi is not None:
            if dc is None:
                raise ValueError('DC pin must be provided when using SPI.')
            self._dc = dc
            self._gpio.setup(self._dc, GPIO.OUT)

    def command(self, *cmd):
        """
        Sends a command or sequence of commands through to the
        device - maximum allowed is 32 bytes in one go.
        """
        self._gpio.set_low(self._dc)
        for t in cmd:
            self._spi.write([t])
        #assert(len(cmd) <= 32)
        #self.bus.write_i2c_block_data(self.addr, self.cmd_mode, list(cmd))

    def data(self, data):
        """
        Sends a data byte or sequence of data bytes through to the
        device - maximum allowed in one transaction is 32 bytes, so if
        data is larger than this it is sent in chunks.
        """
        self._gpio.set_high(self._dc)
        for t in data:
		    self._spi.write([t])


class sh1106(device_spi):
    """dc=None, sclk=None, din=None, cs=None,
				 gpio=None, spi=None
    A device encapsulates the I2C connection (address/port) to the SH1106
    OLED display hardware. The init method pumps commands to the display
    to properly initialize it. Further control commands can then be
    called to affect the brightness. Direct use of the command() and
    data() methods are discouraged.
    """

    def __init__(self, dc=25, spi=SPI.SpiDev(0, 0, max_speed_hz=8000000) ):
        super(sh1106, self).__init__(128,64,dc=dc, spi=spi)
        self.width = 128
        self.height = 64
        self.pages = self.height / 8

        self.command(
            const.DISPLAYOFF,
            const.MEMORYMODE,
            const.SETHIGHCOLUMN,      0xB0, 0xC8,
            const.SETLOWCOLUMN,       0x10, 0x40,
            const.SETCONTRAST,        0x7F,
            const.SETSEGMENTREMAP,
            const.NORMALDISPLAY,
            const.SETMULTIPLEX,       0x3F,
            const.DISPLAYALLON_RESUME,
            const.SETDISPLAYOFFSET,   0x00,
            const.SETDISPLAYCLOCKDIV, 0xF0,
            const.SETPRECHARGE,       0x22,
            const.SETCOMPINS,         0x12,
            const.SETVCOMDETECT,      0x20,
            const.CHARGEPUMP,         0x14,
            const.DISPLAYON)

    def display(self, image):
        """
        Takes a 1-bit image and dumps it to the SH1106 OLED display.
        """
        assert(image.mode == '1')
        assert(image.size[0] == self.width)
        assert(image.size[1] == self.height)

        page = 0xB0
        pix = list(image.getdata())
        step = self.width * 8
        for y in xrange(0, self.pages * step, step):

            # move to given page, then reset the column address
            self.command(page, 0x02, 0x10)
            page += 1

            buf = []
            for x in xrange(self.width):
                byte = 0
                for n in xrange(0, step, self.width):
                    byte |= (pix[x + y + n] & 0x01) << 8
                    byte >>= 1

                buf.append(byte)

            self.data(buf)

class ssd1351(device_spi):
    """dc=None, sclk=None, din=None, cs=None,
				 gpio=None, spi=None
    A device encapsulates the I2C connection (address/port) to the SH1106
    OLED display hardware. The init method pumps commands to the display
    to properly initialize it. Further control commands can then be
    called to affect the brightness. Direct use of the command() and
    data() methods are discouraged.
    """

    def __init__(self, dc=25, spi=SPI.SpiDev(0, 0, max_speed_hz=8000000) ):
        super(ssd1351, self).__init__(128,128,dc=dc, spi=spi)
        self.width = 128
        self.height = 128
        self.pages = self.height / 8

        self.command(
            s1_const.CMD_COMMANDLOCK,   0x12,
            s1_const.CMD_COMMANDLOCK,   0xB1,
            s1_const.CMD_DISPLAYOFF,
            s1_const.CMD_CLOCKDIV,  0xF1,
            s1_const.CMD_MUXRATIO,  127,
            s1_const.CMD_SETREMAP,  0x74,
            s1_const.CMD_SETCOLUMN, 0x00,0x7F,
            s1_const.CMD_SETROW,    0x00,0x7F,
            s1_const.CMD_STARTLINE, 0x00,
            s1_const.CMD_DISPLAYOFFSET, 0x00,
            s1_const.CMD_SETGPIO,   0x00,
            s1_const.CMD_FUNCTIONSELECT,    0x01,
            s1_const.CMD_PRECHARGE, 0x32,
            s1_const.CMD_VCOMH, 0x05,
            s1_const.CMD_NORMALDISPLAY,
            s1_const.CMD_CONTRASTABC,   0xC8,0x80,0xC8,
            s1_const.CMD_CONTRASTMASTER,    0x0F,
            s1_const.CMD_SETVSL,0xA0,0xB5,0x55,
            s1_const.CMD_PRECHARGE2,    0x01,
            s1_const.CMD_DISPLAYALLON)

    def display(self, image):
        """
        Takes a 1-bit image and dumps it to the SH1106 OLED display.
        """
        assert(image.mode == '1')
        assert(image.size[0] == self.width)
        assert(image.size[1] == self.height)

        page = 0xB0
        pix = list(image.getdata())
        step = self.width * 8
        for y in xrange(0, self.pages * step, step):

            # move to given page, then reset the column address
            self.command(page, 0x02, 0x10)
            page += 1

            buf = []
            for x in xrange(self.width):
                byte = 0
                for n in xrange(0, step, self.width):
                    byte |= (pix[x + y + n] & 0x01) << 8
                    byte >>= 1

                buf.append(byte)

            self.data(buf)

class ssd1306(device):
    """
    A device encapsulates the I2C connection (address/port) to the SSD1306
    OLED display hardware. The init method pumps commands to the display
    to properly initialize it. Further control commands can then be
    called to affect the brightness. Direct use of the command() and
    data() methods are discouraged.
    """
    def __init__(self, port=1, address=0x3C):
        super(ssd1306, self).__init__(port, address)
        self.width = 128
        self.height = 64
        self.pages = self.height / 8

        self.command(
            const.DISPLAYOFF,
            const.SETDISPLAYCLOCKDIV, 0x80,
            const.SETMULTIPLEX,       0x3F,
            const.SETDISPLAYOFFSET,   0x00,
            const.SETSTARTLINE,
            const.CHARGEPUMP,         0x14,
            const.MEMORYMODE,         0x00,
            const.SEGREMAP,
            const.COMSCANDEC,
            const.SETCOMPINS,         0x12,
            const.SETCONTRAST,        0xCF,
            const.SETPRECHARGE,       0xF1,
            const.SETVCOMDETECT,      0x40,
            const.DISPLAYALLON_RESUME,
            const.NORMALDISPLAY,
            const.DISPLAYON)

    def display(self, image):
        """
        Takes a 1-bit image and dumps it to the SSD1306 OLED display.
        """
        assert(image.mode == '1')
        assert(image.size[0] == self.width)
        assert(image.size[1] == self.height)

        self.command(
            const.COLUMNADDR, 0x00, self.width-1,  # Column start/end address
            const.PAGEADDR,   0x00, self.pages-1)  # Page start/end address

        pix = list(image.getdata())
        step = self.width * 8
        buf = []
        for y in xrange(0, self.pages * step, step):
            i = y + self.width-1
            while i >= y:
                byte = 0
                for n in xrange(0, step, self.width):
                    byte |= (pix[i + n] & 0x01) << 8
                    byte >>= 1

                buf.append(byte)
                i -= 1

        self.data(buf)


class const:
    CHARGEPUMP = 0x8D
    COLUMNADDR = 0x21
    COMSCANDEC = 0xC8
    COMSCANINC = 0xC0
    DISPLAYALLON = 0xA5
    DISPLAYALLON_RESUME = 0xA4
    DISPLAYOFF = 0xAE
    DISPLAYON = 0xAF
    EXTERNALVCC = 0x1
    INVERTDISPLAY = 0xA7
    MEMORYMODE = 0x20
    NORMALDISPLAY = 0xA6
    PAGEADDR = 0x22
    SEGREMAP = 0xA0
    SETCOMPINS = 0xDA
    SETCONTRAST = 0x81
    SETDISPLAYCLOCKDIV = 0xD5
    SETDISPLAYOFFSET = 0xD3
    SETHIGHCOLUMN = 0x10
    SETLOWCOLUMN = 0x00
    SETMULTIPLEX = 0xA8
    SETPRECHARGE = 0xD9
    SETSEGMENTREMAP = 0xA1
    SETSTARTLINE = 0x40
    SETVCOMDETECT = 0xDB
    SWITCHCAPVCC = 0x2

class s1_const:
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
