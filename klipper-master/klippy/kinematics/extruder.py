# Code for handling printer nozzle extruders
#
# Copyright (C) 2016-2022  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import math, logging
import stepper, chelper

class ExtruderStepper:
    def __init__(self, config):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/__init__")
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.pressure_advance = self.pressure_advance_smooth_time = 0.
        self.config_pa = config.getfloat('pressure_advance', 0., minval=0.)
        self.config_smooth_time = config.getfloat(
                'pressure_advance_smooth_time', 0.040, above=0., maxval=.200)
        # Setup stepper
        self.stepper = stepper.PrinterStepper(config)
        ffi_main, ffi_lib = chelper.get_ffi()
        self.sk_extruder = ffi_main.gc(ffi_lib.extruder_stepper_alloc(),
                                       ffi_lib.free)
        self.stepper.set_stepper_kinematics(self.sk_extruder)
        self.motion_queue = None
        # Register commands
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)
        gcode = self.printer.lookup_object('gcode')
        if self.name == 'extruder':
            gcode.register_mux_command("SET_PRESSURE_ADVANCE", "EXTRUDER", None,
                                       self.cmd_default_SET_PRESSURE_ADVANCE,
                                       desc=self.cmd_SET_PRESSURE_ADVANCE_help)
        gcode.register_mux_command("SET_PRESSURE_ADVANCE", "EXTRUDER",
                                   self.name, self.cmd_SET_PRESSURE_ADVANCE,
                                   desc=self.cmd_SET_PRESSURE_ADVANCE_help)
        gcode.register_mux_command("SET_EXTRUDER_ROTATION_DISTANCE", "EXTRUDER",
                                   self.name, self.cmd_SET_E_ROTATION_DISTANCE,
                                   desc=self.cmd_SET_E_ROTATION_DISTANCE_help)
        gcode.register_mux_command("SYNC_EXTRUDER_MOTION", "EXTRUDER",
                                   self.name, self.cmd_SYNC_EXTRUDER_MOTION,
                                   desc=self.cmd_SYNC_EXTRUDER_MOTION_help)
        gcode.register_mux_command("SET_EXTRUDER_STEP_DISTANCE", "EXTRUDER",
                                   self.name, self.cmd_SET_E_STEP_DISTANCE,
                                   desc=self.cmd_SET_E_STEP_DISTANCE_help)
        gcode.register_mux_command("SYNC_STEPPER_TO_EXTRUDER", "STEPPER",
                                   self.name, self.cmd_SYNC_STEPPER_TO_EXTRUDER,
                                   desc=self.cmd_SYNC_STEPPER_TO_EXTRUDER_help)
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/__init__")
    def _handle_connect(self):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/_handle_connect")
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.register_step_generator(self.stepper.generate_steps)
        self._set_pressure_advance(self.config_pa, self.config_smooth_time)
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/_handle_connect")
    def get_status(self, eventtime):
	logging.info("[log](+/-)kinematics/extruder.py/ExtruderStepper/get_status")
        return {'pressure_advance': self.pressure_advance,
                'smooth_time': self.pressure_advance_smooth_time,
                'motion_queue': self.motion_queue}
    def find_past_position(self, print_time):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/find_past_position")
        mcu_pos = self.stepper.get_past_mcu_position(print_time)
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/find_past_position")
        return self.stepper.mcu_to_commanded_position(mcu_pos)
    def sync_to_extruder(self, extruder_name):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/sync_to_extruder")
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.flush_step_generation()
        if not extruder_name:
            self.stepper.set_trapq(None)
            self.motion_queue = None
	    logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/sync_to_extruder")
            return
        extruder = self.printer.lookup_object(extruder_name, None)
        if extruder is None or not isinstance(extruder, PrinterExtruder):
            raise self.printer.command_error("'%s' is not a valid extruder."
                                             % (extruder_name,))
        self.stepper.set_position([extruder.last_position, 0., 0.])
        self.stepper.set_trapq(extruder.get_trapq())
        self.motion_queue = extruder_name
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/sync_to_extruder")
    def _set_pressure_advance(self, pressure_advance, smooth_time):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/_set_pressure_advance")
        old_smooth_time = self.pressure_advance_smooth_time
        if not self.pressure_advance:
            old_smooth_time = 0.
        new_smooth_time = smooth_time
        if not pressure_advance:
            new_smooth_time = 0.
        toolhead = self.printer.lookup_object("toolhead")
        toolhead.note_step_generation_scan_time(new_smooth_time * .5,
                                                old_delay=old_smooth_time * .5)
        ffi_main, ffi_lib = chelper.get_ffi()
        espa = ffi_lib.extruder_set_pressure_advance
        espa(self.sk_extruder, pressure_advance, new_smooth_time)
        self.pressure_advance = pressure_advance
        self.pressure_advance_smooth_time = smooth_time
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/_set_pressure_advance")
    cmd_SET_PRESSURE_ADVANCE_help = "Set pressure advance parameters"
    def cmd_default_SET_PRESSURE_ADVANCE(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/cmd_default_SET_PRESSURE_ADVANCE")
        extruder = self.printer.lookup_object('toolhead').get_extruder()
        if extruder.extruder_stepper is None:
            raise gcmd.error("Active extruder does not have a stepper")
        strapq = extruder.extruder_stepper.stepper.get_trapq()
        if strapq is not extruder.get_trapq():
            raise gcmd.error("Unable to infer active extruder stepper")
        extruder.extruder_stepper.cmd_SET_PRESSURE_ADVANCE(gcmd)
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/cmd_default_SET_PRESSURE_ADVANCE")
    def cmd_SET_PRESSURE_ADVANCE(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/cmd_SET_PRESSURE_ADVANCE")
        pressure_advance = gcmd.get_float('ADVANCE', self.pressure_advance,
                                          minval=0.)
        smooth_time = gcmd.get_float('SMOOTH_TIME',
                                     self.pressure_advance_smooth_time,
                                     minval=0., maxval=.200)
        self._set_pressure_advance(pressure_advance, smooth_time)
        msg = ("pressure_advance: %.6f\n"
               "pressure_advance_smooth_time: %.6f"
               % (pressure_advance, smooth_time))
        self.printer.set_rollover_info(self.name, "%s: %s" % (self.name, msg))
        gcmd.respond_info(msg, log=False)
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/cmd_SET_PRESSURE_ADVANCE")
    cmd_SET_E_ROTATION_DISTANCE_help = "Set extruder rotation distance"
    def cmd_SET_E_ROTATION_DISTANCE(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/cmd_SET_E_ROTATION_DISTANCE")
        rotation_dist = gcmd.get_float('DISTANCE', None)
        if rotation_dist is not None:
            if not rotation_dist:
                raise gcmd.error("Rotation distance can not be zero")
            invert_dir, orig_invert_dir = self.stepper.get_dir_inverted()
            next_invert_dir = orig_invert_dir
            if rotation_dist < 0.:
                next_invert_dir = not orig_invert_dir
                rotation_dist = -rotation_dist
            toolhead = self.printer.lookup_object('toolhead')
            toolhead.flush_step_generation()
            self.stepper.set_rotation_distance(rotation_dist)
            self.stepper.set_dir_inverted(next_invert_dir)
        else:
            rotation_dist, spr = self.stepper.get_rotation_distance()
        invert_dir, orig_invert_dir = self.stepper.get_dir_inverted()
        if invert_dir != orig_invert_dir:
            rotation_dist = -rotation_dist
        gcmd.respond_info("Extruder '%s' rotation distance set to %0.6f"
                          % (self.name, rotation_dist))
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/cmd_SET_E_ROTATION_DISTANCE")
    cmd_SYNC_EXTRUDER_MOTION_help = "Set extruder stepper motion queue"
    def cmd_SYNC_EXTRUDER_MOTION(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/cmd_SYNC_EXTRUDER_MOTION")
        ename = gcmd.get('MOTION_QUEUE')
        self.sync_to_extruder(ename)
        gcmd.respond_info("Extruder '%s' now syncing with '%s'"
                          % (self.name, ename))
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/cmd_SYNC_EXTRUDER_MOTION")
    cmd_SET_E_STEP_DISTANCE_help = "Set extruder step distance"
    def cmd_SET_E_STEP_DISTANCE(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/cmd_SET_E_STEP_DISTANCE")
        step_dist = gcmd.get_float('DISTANCE', None, above=0.)
        if step_dist is not None:
            toolhead = self.printer.lookup_object('toolhead')
            toolhead.flush_step_generation()
            rd, steps_per_rotation = self.stepper.get_rotation_distance()
            self.stepper.set_rotation_distance(step_dist * steps_per_rotation)
        else:
            step_dist = self.stepper.get_step_dist()
        gcmd.respond_info("Extruder '%s' step distance set to %0.6f"
                          % (self.name, step_dist))
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/cmd_SET_E_STEP_DISTANCE")
    cmd_SYNC_STEPPER_TO_EXTRUDER_help = "Set extruder stepper"
    def cmd_SYNC_STEPPER_TO_EXTRUDER(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/ExtruderStepper/cmd_SYNC_STEPPER_TO_EXTRUDER")
        ename = gcmd.get('EXTRUDER')
        self.sync_to_extruder(ename)
        gcmd.respond_info("Extruder '%s' now syncing with '%s'"
                          % (self.name, ename))
	logging.info("[log](-)kinematics/extruder.py/ExtruderStepper/cmd_SYNC_STEPPER_TO_EXTRUDER")

# Tracking for hotend heater, extrusion motion queue, and extruder stepper
class PrinterExtruder:
    def __init__(self, config, extruder_num):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/__init__")
        self.printer = config.get_printer()
        self.name = config.get_name()
        self.last_position = 0.
        # Setup hotend heater
        shared_heater = config.get('shared_heater', None)
        pheaters = self.printer.load_object(config, 'heaters')
        gcode_id = 'T%d' % (extruder_num,)
        if shared_heater is None:
            self.heater = pheaters.setup_heater(config, gcode_id)
        else:
            config.deprecate('shared_heater')
            self.heater = pheaters.lookup_heater(shared_heater)
        # Setup kinematic checks
        self.nozzle_diameter = config.getfloat('nozzle_diameter', above=0.)
        filament_diameter = config.getfloat(
            'filament_diameter', minval=self.nozzle_diameter)
        self.filament_area = math.pi * (filament_diameter * .5)**2
        def_max_cross_section = 4. * self.nozzle_diameter**2
        def_max_extrude_ratio = def_max_cross_section / self.filament_area
        max_cross_section = config.getfloat(
            'max_extrude_cross_section', def_max_cross_section, above=0.)
        self.max_extrude_ratio = max_cross_section / self.filament_area
        logging.info("Extruder max_extrude_ratio=%.6f", self.max_extrude_ratio)
        toolhead = self.printer.lookup_object('toolhead')
        max_velocity, max_accel = toolhead.get_max_velocity()
        self.max_e_velocity = config.getfloat(
            'max_extrude_only_velocity', max_velocity * def_max_extrude_ratio
            , above=0.)
        self.max_e_accel = config.getfloat(
            'max_extrude_only_accel', max_accel * def_max_extrude_ratio
            , above=0.)
        self.max_e_dist = config.getfloat(
            'max_extrude_only_distance', 50., minval=0.)
        self.instant_corner_v = config.getfloat(
            'instantaneous_corner_velocity', 1., minval=0.)
        # Setup extruder trapq (trapezoidal motion queue)
        ffi_main, ffi_lib = chelper.get_ffi()
        self.trapq = ffi_main.gc(ffi_lib.trapq_alloc(), ffi_lib.trapq_free)
        self.trapq_append = ffi_lib.trapq_append
        self.trapq_finalize_moves = ffi_lib.trapq_finalize_moves
        # Setup extruder stepper
        self.extruder_stepper = None
        if (config.get('step_pin', None) is not None
            or config.get('dir_pin', None) is not None
            or config.get('rotation_distance', None) is not None):
            self.extruder_stepper = ExtruderStepper(config)
            self.extruder_stepper.stepper.set_trapq(self.trapq)
        # Register commands
        gcode = self.printer.lookup_object('gcode')
        if self.name == 'extruder':
            toolhead.set_extruder(self, 0.)
            gcode.register_command("M104", self.cmd_M104)
            gcode.register_command("M109", self.cmd_M109)
        gcode.register_mux_command("ACTIVATE_EXTRUDER", "EXTRUDER",
                                   self.name, self.cmd_ACTIVATE_EXTRUDER,
                                   desc=self.cmd_ACTIVATE_EXTRUDER_help)
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/__init__")
    def update_move_time(self, flush_time):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/update_move_time")
        self.trapq_finalize_moves(self.trapq, flush_time)
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/update_move_time")
    def get_status(self, eventtime):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/get_status")
        sts = self.heater.get_status(eventtime)
        sts['can_extrude'] = self.heater.can_extrude
        if self.extruder_stepper is not None:
            sts.update(self.extruder_stepper.get_status(eventtime))
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/get_status")
        return sts
    def get_name(self):
	logging.info("[log](+/-)kinematics/extruder.py/PrinterExtruder/get_name")
        return self.name
    def get_heater(self):
	logging.info("[log](+/-)kinematics/extruder.py/PrinterExtruder/get_heater")
        return self.heater
    def get_trapq(self):
	logging.info("[log](+/-)kinematics/extruder.py/PrinterExtruder/get_trapq")
        return self.trapq
    def stats(self, eventtime):
	logging.info("[log](+/-)kinematics/extruder.py/PrinterExtruder/stats")
        return self.heater.stats(eventtime)
    def check_move(self, move):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/check_move")
        axis_r = move.axes_r[3]
        if not self.heater.can_extrude:
            raise self.printer.command_error(
                "Extrude below minimum temp\n"
                "See the 'min_extrude_temp' config option for details")
        if (not move.axes_d[0] and not move.axes_d[1]) or axis_r < 0.:
            # Extrude only move (or retraction move) - limit accel and velocity
            if abs(move.axes_d[3]) > self.max_e_dist:
                raise self.printer.command_error(
                    "Extrude only move too long (%.3fmm vs %.3fmm)\n"
                    "See the 'max_extrude_only_distance' config"
                    " option for details" % (move.axes_d[3], self.max_e_dist))
            inv_extrude_r = 1. / abs(axis_r)
            move.limit_speed(self.max_e_velocity * inv_extrude_r,
                             self.max_e_accel * inv_extrude_r)
        elif axis_r > self.max_extrude_ratio:
            if move.axes_d[3] <= self.nozzle_diameter * self.max_extrude_ratio:
                # Permit extrusion if amount extruded is tiny
		logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/check_move")
                return
            area = axis_r * self.filament_area
            logging.debug("Overextrude: %s vs %s (area=%.3f dist=%.3f)",
                          axis_r, self.max_extrude_ratio, area, move.move_d)
            raise self.printer.command_error(
                "Move exceeds maximum extrusion (%.3fmm^2 vs %.3fmm^2)\n"
                "See the 'max_extrude_cross_section' config option for details"
                % (area, self.max_extrude_ratio * self.filament_area))
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/check_move")
    def calc_junction(self, prev_move, move):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/calc_junction")
        diff_r = move.axes_r[3] - prev_move.axes_r[3]
        if diff_r:
	    logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/calc_junction")
            return (self.instant_corner_v / abs(diff_r))**2
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/calc_junction")
        return move.max_cruise_v2
    def move(self, print_time, move):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/move")
        axis_r = move.axes_r[3]
        accel = move.accel * axis_r
        start_v = move.start_v * axis_r
        cruise_v = move.cruise_v * axis_r
        can_pressure_advance = False
        if axis_r > 0. and (move.axes_d[0] or move.axes_d[1]):
            can_pressure_advance = True
        # Queue movement (x is extruder movement, y is pressure advance flag)
        self.trapq_append(self.trapq, print_time,
                          move.accel_t, move.cruise_t, move.decel_t,
                          move.start_pos[3], 0., 0.,
                          1., can_pressure_advance, 0.,
                          start_v, cruise_v, accel)
        self.last_position = move.end_pos[3]
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/move")
    def find_past_position(self, print_time):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/find_past_position")
        if self.extruder_stepper is None:
	    logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/find_past_position")
            return 0.
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/find_past_position")
        return self.extruder_stepper.find_past_position(print_time)
    def cmd_M104(self, gcmd, wait=False):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/cmd_M104")
        # Set Extruder Temperature
        temp = gcmd.get_float('S', 0.)
        index = gcmd.get_int('T', None, minval=0)
        if index is not None:
            section = 'extruder'
            if index:
                section = 'extruder%d' % (index,)
            extruder = self.printer.lookup_object(section, None)
            if extruder is None:
                if temp <= 0.:
		    logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/cmd_M104")
                    return
                raise gcmd.error("Extruder not configured")
        else:
            extruder = self.printer.lookup_object('toolhead').get_extruder()
        pheaters = self.printer.lookup_object('heaters')
        pheaters.set_temperature(extruder.get_heater(), temp, wait)
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/cmd_M104")
    def cmd_M109(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/cmd_M109")
        # Set Extruder Temperature and Wait
        self.cmd_M104(gcmd, wait=True)
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/cmd_M109")
    cmd_ACTIVATE_EXTRUDER_help = "Change the active extruder"
    def cmd_ACTIVATE_EXTRUDER(self, gcmd):
	logging.info("[log](+)kinematics/extruder.py/PrinterExtruder/cmd_ACTIVATE_EXTRUDER")
        toolhead = self.printer.lookup_object('toolhead')
        if toolhead.get_extruder() is self:
            gcmd.respond_info("Extruder %s already active" % (self.name,))
	    logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/cmd_ACTIVATE_EXTRUDER")
            return
        gcmd.respond_info("Activating extruder %s" % (self.name,))
        toolhead.flush_step_generation()
        toolhead.set_extruder(self, self.last_position)
        self.printer.send_event("extruder:activate_extruder")
	logging.info("[log](-)kinematics/extruder.py/PrinterExtruder/cmd_ACTIVATE_EXTRUDER")

# Dummy extruder class used when a printer has no extruder at all
class DummyExtruder:
    def __init__(self, printer):
	logging.info("[log](+)kinematics/extruder.py/DummyExtruder/__init__")
        self.printer = printer
	logging.info("[log](-)kinematics/extruder.py/DummyExtruder/__init__")
    def update_move_time(self, flush_time):
	logging.info("[log](+)kinematics/extruder.py/DummyExtruder/update_move_time")
        pass
	logging.info("[log](-)kinematics/extruder.py/DummyExtruder/update_move_time")
    def check_move(self, move):
	logging.info("[log](+)kinematics/extruder.py/DummyExtruder/check_move")
        raise move.move_error("Extrude when no extruder present")
	logging.info("[log](-)kinematics/extruder.py/DummyExtruder/check_move")
    def find_past_position(self, print_time):
	logging.info("[log](+/-)kinematics/extruder.py/DummyExtruder/find_past_position")
        return 0.
    def calc_junction(self, prev_move, move):
	logging.info("[log](+/-)kinematics/extruder.py/DummyExtruder/calc_junction")
        return move.max_cruise_v2
    def get_name(self):
	logging.info("[log](+/-)kinematics/extruder.py/DummyExtruder/get_name")
        return ""
    def get_heater(self):
	logging.info("[log](+)kinematics/extruder.py/DummyExtruder/get_heater")
        raise self.printer.command_error("Extruder not configured")
	logging.info("[log](-)kinematics/extruder.py/DummyExtruder/get_heater")
    def get_trapq(self):
	logging.info("[log](+)kinematics/extruder.py/DummyExtruder/get_trapq")
        raise self.printer.command_error("Extruder not configured")
	logging.info("[log](-)kinematics/extruder.py/DummyExtruder/get_trapq")

def add_printer_objects(config):
    logging.info("[log](+)kinematics/extruder.py/add_printer_objects")
    printer = config.get_printer()
    for i in range(99):
        section = 'extruder'
        if i:
            section = 'extruder%d' % (i,)
        if not config.has_section(section):
            break
        pe = PrinterExtruder(config.getsection(section), i)
        printer.add_object(section, pe)
    logging.info("[log](-)kinematics/extruder.py/add_printer_objects")
