from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

setup(name              = 'ssd1351',
      version           = '0.1',
      author            = 'AKA',
      author_email      = 'aka@akamediasystem.com',
      description       = 'Library to allow Beaglebone Black to address ssd1351 OLED displays using  Adafruit_BBIO libraries.',
      license           = 'MIT',
      url               = 'https://github.com/AKAMEDIASYSTEM/py-ssd1351',
      #install_requires  = ['Adafruit_BBIO'],
      packages          = find_packages())