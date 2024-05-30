import os 
import sys
import logging 

from logging import Logger
from logging.handlers import TimedRotatingFileHandler 

class Log(Logger):
    def __init__(
        self,
        event_level='event',
        host_type=None,
        log_format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        *args,
        **kwargs
    ):
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        Logger.__init__(self, *args, **kwargs) #Initialize logger handle 
        self.addHandler(self.get_console_handler()) #Output Log to Console

        # with this pattern, it's rarely necessary to propagate the| error up to parent
        self.propagate = False

    def get_console_handler(self):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        return console_handler
