# Code for supporting multiple steppers in single filament extruder.
#
# Copyright (C) 2019 Simo Apell <simo.apell@live.fi>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
from kinematics import extruder

class PrinterExtruderStepper:
    def __init__(self, config):
	logging.info("[log](+)extras/extruder_stepper.py/PrinterExtruderStepper/__init__")
        self.printer = config.get_printer()
        self.extruder_stepper = extruder.ExtruderStepper(config)
        self.extruder_name = config.get('extruder')
        self.printer.register_event_handler("klippy:connect",
                                            self.handle_connect)
	logging.info("[log](-)extras/extruder_stepper.py/PrinterExtruderStepper/__init__")
    def handle_connect(self):
	logging.info("[log](+)extras/extruder_stepper.py/PrinterExtruderStepper/handle_connect")
        self.extruder_stepper.sync_to_extruder(self.extruder_name)
	logging.info("[log](-)extras/extruder_stepper.py/PrinterExtruderStepper/handle_connect")
    def get_status(self, eventtime):
	logging.info("[log](+/-)extras/extruder_stepper.py/PrinterExtruderStepper/get_status")
        return self.extruder_stepper.get_status(eventtime)

def load_config_prefix(config):
    logging.info("[log](+/-)extras/extruder_stepper.py/load_config_prefix")
    return PrinterExtruderStepper(config)
