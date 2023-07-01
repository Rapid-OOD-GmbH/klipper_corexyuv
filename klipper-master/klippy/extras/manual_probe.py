# Helper script for manual z height probing
#
# Copyright (C) 2019  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging, bisect

class ManualProbe:
    def __init__(self, config):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/__init__")
        self.printer = config.get_printer()
        # Register commands
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_move = self.printer.load_object(config, "gcode_move")
        self.gcode.register_command('MANUAL_PROBE', self.cmd_MANUAL_PROBE,
                                    desc=self.cmd_MANUAL_PROBE_help)
        # Endstop value for cartesian printers with separate Z axis
        zconfig = config.getsection('stepper_z')
        self.z_position_endstop = zconfig.getfloat('position_endstop', None,
                                                   note_valid=False)
        # Endstop values for linear delta printers with vertical A,B,C towers
        a_tower_config = config.getsection('stepper_a')
        self.a_position_endstop = a_tower_config.getfloat('position_endstop',
                                                          None,
                                                          note_valid=False)
        b_tower_config = config.getsection('stepper_b')
        self.b_position_endstop = b_tower_config.getfloat('position_endstop',
                                                          None,
                                                          note_valid=False)
        c_tower_config = config.getsection('stepper_c')
        self.c_position_endstop = c_tower_config.getfloat('position_endstop',
                                                          None,
                                                          note_valid=False)
        # Conditionally register appropriate commands depending on printer
        # Cartestian printers with separate Z Axis
        if self.z_position_endstop is not None:
            self.gcode.register_command(
                'Z_ENDSTOP_CALIBRATE', self.cmd_Z_ENDSTOP_CALIBRATE,
                desc=self.cmd_Z_ENDSTOP_CALIBRATE_help)
            self.gcode.register_command(
                'Z_OFFSET_APPLY_ENDSTOP',
                self.cmd_Z_OFFSET_APPLY_ENDSTOP,
                desc=self.cmd_Z_OFFSET_APPLY_ENDSTOP_help)
        # Linear delta printers with A,B,C towers
        if 'delta' == config.getsection('printer').get('kinematics'):
            self.gcode.register_command(
                'Z_OFFSET_APPLY_ENDSTOP',
                self.cmd_Z_OFFSET_APPLY_DELTA_ENDSTOPS,
                desc=self.cmd_Z_OFFSET_APPLY_ENDSTOP_help)
        self.reset_status()
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/__init__")
    def manual_probe_finalize(self, kin_pos):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/manual_probe_finalize")
        if kin_pos is not None:
            self.gcode.respond_info("Z position is %.3f" % (kin_pos[2],))
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/manual_probe_finalize")
    def reset_status(self):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/reset_status")
        self.status = {
            'is_active': False,
            'z_position': None,
            'z_position_lower': None,
            'z_position_upper': None
        }
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/reset_status")
    def get_status(self, eventtime):
	logging.info("[log](+/-)extras/manual_probe.py/ManualProbe/get_status")
        return self.status
    cmd_MANUAL_PROBE_help = "Start manual probe helper script"
    def cmd_MANUAL_PROBE(self, gcmd):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/cmd_MANUAL_PROBE")
        ManualProbeHelper(self.printer, gcmd, self.manual_probe_finalize)
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/cmd_MANUAL_PROBE")
    def z_endstop_finalize(self, kin_pos):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/z_endstop_finalize")
        if kin_pos is None:
	    logging.info("[log](-)extras/manual_probe.py/ManualProbe/z_endstop_finalize")
            return
        z_pos = self.z_position_endstop - kin_pos[2]
        self.gcode.respond_info(
            "stepper_z: position_endstop: %.3f\n"
            "The SAVE_CONFIG command will update the printer config file\n"
            "with the above and restart the printer." % (z_pos,))
        configfile = self.printer.lookup_object('configfile')
        configfile.set('stepper_z', 'position_endstop', "%.3f" % (z_pos,))
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/z_endstop_finalize")
    cmd_Z_ENDSTOP_CALIBRATE_help = "Calibrate a Z endstop"
    def cmd_Z_ENDSTOP_CALIBRATE(self, gcmd):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/cmd_Z_ENDSTOP_CALIBRATE")
        ManualProbeHelper(self.printer, gcmd, self.z_endstop_finalize)
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/cmd_Z_ENDSTOP_CALIBRATE")
    def cmd_Z_OFFSET_APPLY_ENDSTOP(self,gcmd):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/cmd_Z_OFFSET_APPLY_ENDSTOP")
        offset = self.gcode_move.get_status()['homing_origin'].z
        configfile = self.printer.lookup_object('configfile')
        if offset == 0:
            self.gcode.respond_info("Nothing to do: Z Offset is 0")
        else:
            new_calibrate = self.z_position_endstop - offset
            self.gcode.respond_info(
                "stepper_z: position_endstop: %.3f\n"
                "The SAVE_CONFIG command will update the printer config file\n"
                "with the above and restart the printer." % (new_calibrate))
            configfile.set('stepper_z', 'position_endstop',
                "%.3f" % (new_calibrate,))
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/cmd_Z_OFFSET_APPLY_ENDSTOP")
    def cmd_Z_OFFSET_APPLY_DELTA_ENDSTOPS(self,gcmd):
	logging.info("[log](+)extras/manual_probe.py/ManualProbe/cmd_Z_OFFSET_APPLY_DELTA_ENDSTOPS")
        offset = self.gcode_move.get_status()['homing_origin'].z
        configfile = self.printer.lookup_object('configfile')
        if offset == 0:
            self.gcode.respond_info("Nothing to do: Z Offset is 0")
        else:
            new_a_calibrate = self.a_position_endstop - offset
            new_b_calibrate = self.b_position_endstop - offset
            new_c_calibrate = self.c_position_endstop - offset
            self.gcode.respond_info(
                "stepper_a: position_endstop: %.3f\n"
                "stepper_b: position_endstop: %.3f\n"
                "stepper_c: position_endstop: %.3f\n"
                "The SAVE_CONFIG command will update the printer config file\n"
                "with the above and restart the printer." % (new_a_calibrate,
                                                             new_b_calibrate,
                                                             new_c_calibrate))
            configfile.set('stepper_a', 'position_endstop',
                "%.3f" % (new_a_calibrate,))
            configfile.set('stepper_b', 'position_endstop',
                "%.3f" % (new_b_calibrate,))
            configfile.set('stepper_c', 'position_endstop',
                "%.3f" % (new_c_calibrate,))
	logging.info("[log](-)extras/manual_probe.py/ManualProbe/cmd_Z_OFFSET_APPLY_DELTA_ENDSTOPS")
    cmd_Z_OFFSET_APPLY_ENDSTOP_help = "Adjust the z endstop_position"

# Verify that a manual probe isn't already in progress
def verify_no_manual_probe(printer):
    logging.info("[log](+)extras/manual_probe.py/verify_no_manual_probe")
    gcode = printer.lookup_object('gcode')
    try:
        gcode.register_command('ACCEPT', 'dummy')
    except printer.config_error as e:
        raise gcode.error(
            "Already in a manual Z probe. Use ABORT to abort it.")
    gcode.register_command('ACCEPT', None)
    logging.info("[log](-)extras/manual_probe.py/verify_no_manual_probe")

Z_BOB_MINIMUM = 0.500
BISECT_MAX = 0.200

# Helper script to determine a Z height
class ManualProbeHelper:
    def __init__(self, printer, gcmd, finalize_callback):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/verify_no_manual_probe")
        self.printer = printer
        self.finalize_callback = finalize_callback
        self.gcode = self.printer.lookup_object('gcode')
        self.toolhead = self.printer.lookup_object('toolhead')
        self.manual_probe = self.printer.lookup_object('manual_probe')
        self.speed = gcmd.get_float("SPEED", 5.)
        self.past_positions = []
        self.last_toolhead_pos = self.last_kinematics_pos = None
        # Register commands
        verify_no_manual_probe(printer)
        self.gcode.register_command('ACCEPT', self.cmd_ACCEPT,
                                    desc=self.cmd_ACCEPT_help)
        self.gcode.register_command('NEXT', self.cmd_ACCEPT)
        self.gcode.register_command('ABORT', self.cmd_ABORT,
                                    desc=self.cmd_ABORT_help)
        self.gcode.register_command('TESTZ', self.cmd_TESTZ,
                                    desc=self.cmd_TESTZ_help)
        self.gcode.respond_info(
            "Starting manual Z probe. Use TESTZ to adjust position.\n"
            "Finish with ACCEPT or ABORT command.")
        self.start_position = self.toolhead.get_position()
        self.report_z_status()
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/verify_no_manual_probe")
    def get_kinematics_pos(self):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/get_kinematics_pos")
        toolhead_pos = self.toolhead.get_position()
        if toolhead_pos == self.last_toolhead_pos:
	    logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/get_kinematics_pos")
            return self.last_kinematics_pos
        self.toolhead.flush_step_generation()
        kin = self.toolhead.get_kinematics()
        kin_spos = {s.get_name(): s.get_commanded_position()
                    for s in kin.get_steppers()}
        kin_pos = kin.calc_position(kin_spos)
        self.last_toolhead_pos = toolhead_pos
        self.last_kinematics_pos = kin_pos
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/get_kinematics_pos")
        return kin_pos
    def move_z(self, z_pos):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/move_z")
        curpos = self.toolhead.get_position()
        try:
            z_bob_pos = z_pos + Z_BOB_MINIMUM
            if curpos[2] < z_bob_pos:
                self.toolhead.manual_move([None, None, z_bob_pos], self.speed)
            self.toolhead.manual_move([None, None, z_pos], self.speed)
        except self.printer.command_error as e:
            self.finalize(False)
            raise
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/move_z")
    def report_z_status(self, warn_no_change=False, prev_pos=None):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/report_z_status")
        # Get position
        kin_pos = self.get_kinematics_pos()
        z_pos = kin_pos[2]
        if warn_no_change and z_pos == prev_pos:
            self.gcode.respond_info(
                "WARNING: No change in position (reached stepper resolution)")
        # Find recent positions that were tested
        pp = self.past_positions
        next_pos = bisect.bisect_left(pp, z_pos)
        prev_pos = next_pos - 1
        if next_pos < len(pp) and pp[next_pos] == z_pos:
            next_pos += 1
        prev_pos_val = next_pos_val = None
        prev_str = next_str = "??????"
        if prev_pos >= 0:
            prev_pos_val = pp[prev_pos]
            prev_str = "%.3f" % (prev_pos_val,)
        if next_pos < len(pp):
            next_pos_val = pp[next_pos]
            next_str = "%.3f" % (next_pos_val,)
        self.manual_probe.status = {
            'is_active': True,
            'z_position': z_pos,
            'z_position_lower': prev_pos_val,
            'z_position_upper': next_pos_val,
        }
        # Find recent positions
        self.gcode.respond_info("Z position: %s --> %.3f <-- %s"
                                % (prev_str, z_pos, next_str))
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/report_z_status")
    cmd_ACCEPT_help = "Accept the current Z position"
    def cmd_ACCEPT(self, gcmd):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/cmd_ACCEPT")
        pos = self.toolhead.get_position()
        start_pos = self.start_position
        if pos[:2] != start_pos[:2] or pos[2] >= start_pos[2]:
            gcmd.respond_info(
                "Manual probe failed! Use TESTZ commands to position the\n"
                "nozzle prior to running ACCEPT.")
            self.finalize(False)
	    logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/cmd_ACCEPT")
            return
        self.finalize(True)
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/cmd_ACCEPT")
    cmd_ABORT_help = "Abort manual Z probing tool"
    def cmd_ABORT(self, gcmd):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/cmd_ABORT")
        self.finalize(False)
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/cmd_ABORT")
    cmd_TESTZ_help = "Move to new Z height"
    def cmd_TESTZ(self, gcmd):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/cmd_TESTZ")
        # Store current position for later reference
        kin_pos = self.get_kinematics_pos()
        z_pos = kin_pos[2]
        pp = self.past_positions
        insert_pos = bisect.bisect_left(pp, z_pos)
        if insert_pos >= len(pp) or pp[insert_pos] != z_pos:
            pp.insert(insert_pos, z_pos)
        # Determine next position to move to
        req = gcmd.get("Z")
        if req in ('+', '++'):
            check_z = 9999999999999.9
            if insert_pos < len(self.past_positions) - 1:
                check_z = self.past_positions[insert_pos + 1]
            if req == '+':
                check_z = (check_z + z_pos) / 2.
            next_z_pos = min(check_z, z_pos + BISECT_MAX)
        elif req in ('-', '--'):
            check_z = -9999999999999.9
            if insert_pos > 0:
                check_z = self.past_positions[insert_pos - 1]
            if req == '-':
                check_z = (check_z + z_pos) / 2.
            next_z_pos = max(check_z, z_pos - BISECT_MAX)
        else:
            next_z_pos = z_pos + gcmd.get_float("Z")
        # Move to given position and report it
        self.move_z(next_z_pos)
        self.report_z_status(next_z_pos != z_pos, z_pos)
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/cmd_TESTZ")
    def finalize(self, success):
	logging.info("[log](+)extras/manual_probe.py/ManualProbeHelper/finalize")
        self.manual_probe.reset_status()
        self.gcode.register_command('ACCEPT', None)
        self.gcode.register_command('NEXT', None)
        self.gcode.register_command('ABORT', None)
        self.gcode.register_command('TESTZ', None)
        kin_pos = None
        if success:
            kin_pos = self.get_kinematics_pos()
        self.finalize_callback(kin_pos)
	logging.info("[log](-)extras/manual_probe.py/ManualProbeHelper/finalize")

def load_config(config):
    logging.info("[log](+/-)extras/manual_probe.py/ManualProbeHelper/load_config")
    return ManualProbe(config)
