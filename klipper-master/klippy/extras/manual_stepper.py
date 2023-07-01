# Support for a manual controlled stepper
#
# Copyright (C) 2019-2021  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import stepper, chelper, logging
from . import force_move

class ManualStepper:
    def __init__(self, config):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/__init__")
        self.printer = config.get_printer()
        if config.get('endstop_pin', None) is not None:
            self.can_home = True
            self.rail = stepper.PrinterRail(
                config, need_position_minmax=False, default_position_endstop=0.)
            self.steppers = self.rail.get_steppers()
        else:
            self.can_home = False
            self.rail = stepper.PrinterStepper(config)
            self.steppers = [self.rail]
        self.velocity = config.getfloat('velocity', 5., above=0.)
        self.accel = self.homing_accel = config.getfloat('accel', 0., minval=0.)
        self.next_cmd_time = 0.
        # Setup iterative solver
        ffi_main, ffi_lib = chelper.get_ffi()
        self.trapq = ffi_main.gc(ffi_lib.trapq_alloc(), ffi_lib.trapq_free)
        self.trapq_append = ffi_lib.trapq_append
        self.trapq_finalize_moves = ffi_lib.trapq_finalize_moves
        self.rail.setup_itersolve('cartesian_stepper_alloc', b'x')
        self.rail.set_trapq(self.trapq)
        # Register commands
        stepper_name = config.get_name().split()[1]
        gcode = self.printer.lookup_object('gcode')
        gcode.register_mux_command('MANUAL_STEPPER', "STEPPER",
                                   stepper_name, self.cmd_MANUAL_STEPPER,
                                   desc=self.cmd_MANUAL_STEPPER_help)
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/__init__")
    def sync_print_time(self):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/sync_print_time")
        toolhead = self.printer.lookup_object('toolhead')
        print_time = toolhead.get_last_move_time()
        if self.next_cmd_time > print_time:
            toolhead.dwell(self.next_cmd_time - print_time)
        else:
            self.next_cmd_time = print_time
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/sync_print_time")
    def do_enable(self, enable):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/do_enable")
        self.sync_print_time()
        stepper_enable = self.printer.lookup_object('stepper_enable')
        if enable:
            for s in self.steppers:
                se = stepper_enable.lookup_enable(s.get_name())
                se.motor_enable(self.next_cmd_time)
        else:
            for s in self.steppers:
                se = stepper_enable.lookup_enable(s.get_name())
                se.motor_disable(self.next_cmd_time)
        self.sync_print_time()
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/do_enable")
    def do_set_position(self, setpos):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/do_set_position")
        self.rail.set_position([setpos, 0., 0.])
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/do_set_position")
    def do_move(self, movepos, speed, accel, sync=True):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/do_move")
        self.sync_print_time()
        cp = self.rail.get_commanded_position()
        dist = movepos - cp
        axis_r, accel_t, cruise_t, cruise_v = force_move.calc_move_time(
            dist, speed, accel)
        self.trapq_append(self.trapq, self.next_cmd_time,
                          accel_t, cruise_t, accel_t,
                          cp, 0., 0., axis_r, 0., 0.,
                          0., cruise_v, accel)
        self.next_cmd_time = self.next_cmd_time + accel_t + cruise_t + accel_t
        self.rail.generate_steps(self.next_cmd_time)
        self.trapq_finalize_moves(self.trapq, self.next_cmd_time + 99999.9)
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.note_kinematic_activity(self.next_cmd_time)
        if sync:
            self.sync_print_time()
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/do_move")
    def do_homing_move(self, movepos, speed, accel, triggered, check_trigger):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/do_homing_move")
        if not self.can_home:
            raise self.printer.command_error(
                "No endstop for this manual stepper")
        self.homing_accel = accel
        pos = [movepos, 0., 0., 0.]
        endstops = self.rail.get_endstops()
        phoming = self.printer.lookup_object('homing')
        phoming.manual_home(self, endstops, pos, speed,
                            triggered, check_trigger)
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/do_homing_move")
    cmd_MANUAL_STEPPER_help = "Command a manually configured stepper"
    def cmd_MANUAL_STEPPER(self, gcmd):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/cmd_MANUAL_STEPPER")
        enable = gcmd.get_int('ENABLE', None)
        if enable is not None:
            self.do_enable(enable)
        setpos = gcmd.get_float('SET_POSITION', None)
        if setpos is not None:
            self.do_set_position(setpos)
        speed = gcmd.get_float('SPEED', self.velocity, above=0.)
        accel = gcmd.get_float('ACCEL', self.accel, minval=0.)
        homing_move = gcmd.get_int('STOP_ON_ENDSTOP', 0)
        if homing_move:
            movepos = gcmd.get_float('MOVE')
            self.do_homing_move(movepos, speed, accel,
                                homing_move > 0, abs(homing_move) == 1)
        elif gcmd.get_float('MOVE', None) is not None:
            movepos = gcmd.get_float('MOVE')
            sync = gcmd.get_int('SYNC', 1)
            self.do_move(movepos, speed, accel, sync)
        elif gcmd.get_int('SYNC', 0):
            self.sync_print_time()
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/cmd_MANUAL_STEPPER")
    # Toolhead wrappers to support homing
    def flush_step_generation(self):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/flush_step_generation")
        self.sync_print_time()
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/flush_step_generation")
    def get_position(self):
	logging.info("[log](+/-)extras/manual_stepper.py/ManualStepper/get_position")
        return [self.rail.get_commanded_position(), 0., 0., 0.]
    def set_position(self, newpos, homing_axes=()):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/get_position")
        self.do_set_position(newpos[0])
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/get_position")
    def get_last_move_time(self):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/get_last_move_time")
        self.sync_print_time()
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/get_last_move_time")
        return self.next_cmd_time
    def dwell(self, delay):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/dwell")
        self.next_cmd_time += max(0., delay)
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/dwell")
    def drip_move(self, newpos, speed, drip_completion):
	logging.info("[log](+)extras/manual_stepper.py/ManualStepper/drip_move")
        self.do_move(newpos[0], speed, self.homing_accel)
	logging.info("[log](-)extras/manual_stepper.py/ManualStepper/drip_move")
    def get_kinematics(self):
	logging.info("[log](+/-)extras/manual_stepper.py/ManualStepper/get_kinematics")
        return self
    def get_steppers(self):
	logging.info("[log](+/-)extras/manual_stepper.py/ManualStepper/get_steppers")
        return self.steppers
    def calc_position(self, stepper_positions):
	logging.info("[log](+/-)extras/manual_stepper.py/ManualStepper/calc_position")
        return [stepper_positions[self.rail.get_name()], 0., 0.]

def load_config_prefix(config):
    logging.info("[log](+/-)extras/manual_stepper.py/ManualStepper/load_config_prefix")
    return ManualStepper(config)
