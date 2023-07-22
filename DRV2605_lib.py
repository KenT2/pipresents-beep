"""
 modified from the Pimoroni DRV2605 library which supports only LRA
  it has been extended to allow use of ERM actuators and audio input
"""

import time
import math
#krt
import smbus
#krt
from i2cdevice import Device, Register, BitField
from i2cdevice.adapter import Adapter, LookupAdapter

__version__ = '0.0.3'

DRV2605_ADDR = 0x5a

#krt
class ScaleAdapter(Adapter):
    
    def __init__(self):
        pass
        
    def _encode(self,value):
        #convert from real value to register value
        # real_val = (reg_val* 1.8) / 255
        # reg val = real_val/1.8*255
        res= int(float(value)/1.8*255)
        #print ('scale: ',res)
        return res


class WaitTimeAdapter():
    def _encode(self, value):
        return (value // 10) | 0x80

    def _decode(self, value):
        return (value & 0x7F) * 10


class WaitMillis():
    def __init__(self, wait_time):
        self.wait_time = wait_time


class PlayWaveform():
    def __init__(self, waveform):
        self.waveform = waveform


class DRV2605():
    def __init__(self, i2c_addr=DRV2605_ADDR, i2c_dev=None):
        self._i2c_addr = i2c_addr
        self._i2c_dev = i2c_dev
        self._drv2605 = Device(DRV2605_ADDR, i2c_dev=self._i2c_dev, registers=(
            Register('STATUS', 0x00, fields=(
                BitField('device_id', 0b11100000),
                BitField('diagnostic', 0b00001000),
                BitField('over_temp', 0b00000010),
                BitField('over_current', 0b00000001),
            )),
            Register('MODE', 0x01, fields=(
                BitField('reset', 0b10000000),
                BitField('standby', 0b01000000),
                BitField('mode', 0b00000111, adapter=LookupAdapter({
                    'Internal Trigger': 0,          # Waveforms are fired by setting the GO bit in register 0x0C
                    'Edge Trigger': 1,              # A rising edge on INT/TRIG sets the GO bit, a second rising edge cancels the waveform
                    'Level Trigger': 2,             # A rising edge on INT/TRIG sets the GO bit, a falling edge cancels the waveform
                    'PWM/Analog In': 3,             # A PWM or Analog signal is accepted on INT/TRIG and used as a direct driving source
                    'Audio In': 4,                  # An AC-coupled audio signal is accepted on INT/TRIG and turned into meaningful vibration
                                                    # (AC_COUPLE and N_PWM_ANALOG should also be set)
                    'Real-time Playback': 5,        # The contents of the REALTIME_PLAYBACK register are used as a waveform
                    'Diagnostics': 6,               # Perform a diagnostic test on the actuator- triggered by setting the GO bit
                    'Auto Calibration': 7           # Perform an auto-calibration- triggered by setting the GO bit
                })),
            )),
            Register('REALTIME_PLAYBACK', 0x02, fields=(
                BitField('input', 0xFF),
            )),
            Register('LIBRARY_SELECTION', 0x03, fields=(
                BitField('high_impedance', 0b00010000),
                BitField('library', 0b00000111, adapter=LookupAdapter({
                    'Empty': 0,
                    'TS2200 A': 1,                  # Rated 1.3v, Overdrive 3v, 40ms to 60ms rise, 20ms to 40ms brake
                    'TS2200 B': 2,                  # Rated 3v, Overdrive 3v, 40ms to 60ms rise, 5ms to 15ms brake
                    'TS2200 C': 3,                  # Rated 3v, Overdrive 3v, 60ms to 80ms rise, 10ms to 20ms brake
                    'TS2200 D': 4,                  # Rated 3v, Overdrive 3v, 100ms to 140ms rise, 15ms to 25ms brake
                    'TS2200 E': 5,                  # Rated 3v, Overdrive 3v, > 140ms rise, > 30ms brake
                    'LRA': 6,                       # Linear Resonance
                    'TS2200 F': 7                   # Rated 4.5v, Overdrive 5v, 35ms to 45ms rise, 10ms to 20ms brake
                })),
            )),
            # When the wait bit is set, the value of its corresponding
            # waveform becomes a timed delay.
            # Delay time = 10 ms x waveformN
            Register('WAVEFORM_SEQUENCER', 0x04, fields=(
                BitField('step1_wait', 0xFF << 56, adapter=WaitTimeAdapter()),
                BitField('step1_waveform', 0xFF << 56),
                BitField('step2_wait', 0xFF << 48, adapter=WaitTimeAdapter()),
                BitField('step2_waveform', 0xFF << 48),
                BitField('step3_wait', 0xFF << 40, adapter=WaitTimeAdapter()),
                BitField('step3_waveform', 0xFF << 40),
                BitField('step4_wait', 0xFF << 32, adapter=WaitTimeAdapter()),
                BitField('step4_waveform', 0xFF << 32),
                BitField('step5_wait', 0xFF << 24, adapter=WaitTimeAdapter()),
                BitField('step5_waveform', 0xFF << 24),
                BitField('step6_wait', 0xFF << 16, adapter=WaitTimeAdapter()),
                BitField('step6_waveform', 0xFF << 16),
                BitField('step7_wait', 0xFF << 8, adapter=WaitTimeAdapter()),
                BitField('step7_waveform', 0xFF << 8),
                BitField('step8_wait', 0xFF << 0, adapter=WaitTimeAdapter()),
                BitField('step8_waveform', 0xFF << 0),
            ), bit_width=8 * 8),
            Register('GO', 0x0C, fields=(
                BitField('go', 0b00000001),
            )),
            Register('TIME_OFFSET', 0x0D, fields=(
                BitField('overdrive', 0xFF000000),
                BitField('positive_sustain', 0x00FF0000),
                BitField('negative_sustain', 0x0000FF00),
                BitField('brake', 0x000000FF)
            ), bit_width=8 * 4),
            Register('AUDIO_CONTROL', 0x11, fields=(
                BitField('peak_detection_time_ms', 0b00001100, adapter=LookupAdapter({
                    10: 0,
                    20: 1,
                    30: 2,
                    40: 3
                })),
                BitField('low_pass_filter_hz', 0b00000011, adapter=LookupAdapter({
                    100: 0,
                    125: 1,
                    150: 2,
                    200: 3
                }))
            )),
            #KRT
            Register('AUDIO_INPUT_LEVEL', 0x12, fields=(
                BitField('minimum', 0xFF00,adapter=ScaleAdapter()),        # input level v = (minimum * 1.8) / 255 TODO create an adapter
                BitField('maximum', 0x00FF,adapter=ScaleAdapter())         # input level v = (maximum * 1.8) / 255 TODO create an adapter
            ), bit_width=8 * 2),
            Register('AUDIO_OUTPUT_DRIVE', 0x14, fields=(
                BitField('minimum', 0xFF00),        # max drive % = (maximum / 255) x 100 TODO create an adapter
                BitField('maximum', 0x00FF)         # max drive % = (maximum / 255) x 100 TODO create an adapter
            ), bit_width=8 * 2),
            Register('VOLTAGE', 0x16, fields=(
                BitField('rated', 0xFF00),
                BitField('overdrive_clamp', 0x00FF)
            ), bit_width=8 * 2),
            Register('AUTO_CALIBRATION_RESULT', 0x18, fields=(
                BitField('compensation', 0xFF00),   # coef = 1 + compensation / 255
                BitField('back_emf', 0x00FF),       # back-emf v = back_emf / 255 * 1.22 / back_emf_gain
            ), bit_width=8 * 2),
            Register('FEEDBACK_CONTROL', 0x1A, fields=(
                BitField('mode', 0b10000000, adapter=LookupAdapter({
                    'ERM': 0,
                    'LRA': 1
                })),
                BitField('feedback_brake_factor', 0b01110000, adapter=LookupAdapter({
                    1: 0,
                    2: 1,
                    3: 2,
                    4: 3,
                    6: 4,
                    8: 5,
                    16: 6,
                    0: 7
                })),
                BitField('loop_gain', 0b00001100, adapter=LookupAdapter({
                    'low': 0,
                    'medium': 1,
                    'high': 2,
                    'very high': 3
                })),
                BitField('back_emf_gain', 0b00000011, adapter=LookupAdapter({
                    0.255: 0,                       # ERM mode
                    0.7875: 1,
                    1.365: 2,
                    3.0: 3,
                    3.75: 0,                        # LRA mode
                    7.5: 1,
                    15.0: 2,
                    22.5: 3
                }))
            )),
            Register('CONTROL1', 0x1B, fields=(
                BitField('startup_boost', 0b10000000),
                #KRT
                BitField('ac_couple', 0b00100000,adapter=LookupAdapter({
                    'Off': 0,
                    'On': 1 })),
                BitField('drive_time', 0b00011111)
            )),
            Register('CONTROL2', 0x1C, fields=(
                BitField('bidir_input', 0b10000000),
                BitField('brake_stabalize', 0b01000000),
                BitField('sample_time', 0b00110000),
                BitField('blanking_time', 0b00001100),
                BitField('idiss_time', 0b00000011)
            )),
            Register('CONTROL3', 0x1D, fields=(
                BitField('noise_gate_threshold', 0b11000000, adapter=LookupAdapter({
                    'Disabled': 0,
                    '2%': 1,
                    '4%': 2,
                    '8%': 3})),
                BitField('erm_open_loop', 0b00100000, adapter=LookupAdapter({
                    'Closed Loop': 0,
                    'Open Loop': 1})),
                BitField('supply_compensation_disable', 0b00010000, adapter=LookupAdapter({
                    'Enabled': 0,
                    'Disabled': 1})),
                BitField('data_format_rtp', 0b00001000, adapter=LookupAdapter({
                    'Signed': 0,
                    'Unsigned': 1})),
                BitField('lra_drive_mode', 0b00000100, adapter=LookupAdapter({
                    'Once': 0,
                    'Twice': 1})),
                BitField('pwm_input_mode', 0b00000010, adapter=LookupAdapter({
                    'PWM': 0,
                    'Analog': 1})),
                BitField('lra_open_loop', 0b00000001, adapter=LookupAdapter({
                    'Auto-resonance': 0,
                    'Open Loop': 1
                }))
            )),
            Register('CONTROL4', 0x1E, fields=(
                BitField('zero_crossing_detection_time', 0b11000000, adapter=LookupAdapter({
                    100: 0,
                    200: 1,
                    300: 2,
                    390: 3
                })),
                BitField('auto_calibration_time', 0b00110000, adapter=LookupAdapter({
                    150: 0,                     # 150ms to 350ms
                    250: 1,                     # 250ms to 450ms
                    500: 2,                     # 500ms to 700ms
                    1000: 3                     # 1000ms to 1200ms
                })),
                # BitField('otp_status', 0b00000100),
                # BitField('otp_program', 0b0000001)
            )),
            Register('CONTROL5', 0x1F, fields=(
                BitField('auto_open_loop_attempts', 0b11000000, adapter=LookupAdapter({
                    3: 0,
                    4: 1,
                    5: 2,
                    6: 3
                })),
                BitField('auto_open_loop_transition', 0b00100000),
                BitField('playback_interval_ms', 0b00010000, adapter=LookupAdapter({
                    5: 0,
                    1: 1
                })),
                BitField('blanking_time', 0b00001100),
                BitField('idiss_time', 0b00000011)
            )),
            Register('LRA_OPEN_LOOP_PERIOD', 0x20, fields=(
                BitField('period', 0x7F),       # period (us) = period * 98.46
            )),
            Register('VOLTAGE', 0x21, fields=(
                BitField('vbat', 0xFF),
            )),
            Register('LRA_RESONANCE', 0x22, fields=(
                BitField('period', 0xFF),       # period (us) = period * 98.46
            ))
        ))

    def reset(self):
        self._drv2605.set('MODE', standby=False, reset=True)
        time.sleep(0.1)
        while self._drv2605.get('MODE').reset:
            time.sleep(0.01)
        self._drv2605.set('MODE', standby=False)

    def set_feedback_mode(self, mode='LRA'):
        self._drv2605.set('FEEDBACK_CONTROL', mode=mode)

    def set_library(self, library='LRA'):
        #krt
        self._drv2605.set('LIBRARY_SELECTION', library=library)
        
    #krt    
    def set_erm_loop_mode(self,loop='Open Loop'):
        self._drv2605.set('CONTROL3', erm_open_loop=loop)

    def set_mode(self, mode):
        self._drv2605.set('MODE', mode=mode)

    def auto_calibrate(self,
                       loop_gain='high',
                       feedback_brake_factor=2,
                       auto_calibration_time=1000,
                       zero_crossing_detection_time=100,
                       idiss_time=1):
        mode = self._drv2605.get('MODE').mode
        self._drv2605.set('MODE', mode='Auto Calibration')
        self._drv2605.set('FEEDBACK_CONTROL',
                          loop_gain=loop_gain,
                          feedback_brake_factor=feedback_brake_factor)
        self._drv2605.set('CONTROL4',
                          auto_calibration_time=auto_calibration_time,
                          zero_crossing_detection_time=zero_crossing_detection_time)
        self._drv2605.set('CONTROL2', idiss_time=idiss_time)
        self._drv2605.set('GO', go=True)
        while self._drv2605.get('GO').go:
            time.sleep(0.01)
        self._drv2605.set('MODE', mode=mode)

    def set_realtime_input(self, value):
        """Set a single playback sample for realtime mode."""
        self._drv2605.set('REALTIME_PLAYBACK', input=value)

    def set_realtime_data_format(self, value):
        """Set the data format for realtime mode playback samples."""
        self._drv2605.set('CONTROL3', data_format_rtp=value)
    #krt    
    def set_ac_couple(self, value):
        """Set voltage offset for audio input."""
        self._drv2605.set('CONTROL1', ac_couple=value)  #On,Off
    
    #krt    
    def set_pwm_input_mode(self, value):
        """Set vibe amplitude determined by amplitude or pwm"""
        self._drv2605.set('CONTROL3', pwm_input_mode=value)  #Analog,PWM
    #krt    
    def set_max_audio_input(self,value):
        self._drv2605.set('AUDIO_INPUT_LEVEL', maximum=value) 
        
    #krt    
    def set_min_audio_input(self,value):
        self._drv2605.set('AUDIO_INPUT_LEVEL', minimum=value) 


    def set_sequence(self, *sequence):
        """Set a sequence to be played by the DRV2605.

        Accepts up to 8 arguments of type PlayWaveform or WaitMillis.

        """
        settings = {}
        for x, step in enumerate(sequence):
            if hasattr(step, 'wait_time'):
                settings['step{}_wait'.format(x + 1)] = step.wait_time
            elif hasattr(step, 'waveform'):
                settings['step{}_waveform'.format(x + 1)] = step.waveform
        self._drv2605.set('WAVEFORM_SEQUENCER', **settings)

    def go(self):
        """Trigger the current mode."""
        self._drv2605.set('GO', go=True)

    def stop(self):
        """Stop playback."""
        self._drv2605.set('GO', go=False)

    def busy(self):
        """Check if DRV2605 is busy."""
        return self._drv2605.get('GO').go


if __name__ == "__main__":
    import sys

    enable_calibration = True

    bus = smbus.SMBus(1)
    drv2605 = DRV2605(i2c_dev=bus)
    drv2605.reset()

    drv2605.set_feedback_mode('LRA')
    drv2605.set_library('LRA')

    if enable_calibration:
        drv2605.auto_calibrate()
        time.sleep(0.5)

    if len(sys.argv) > 1:
        drv2605.set_mode('Internal Trigger')
        pattern = int(sys.argv[1])

        print("Playing pattern: {}".format(sys.argv[1]))

        drv2605.set_sequence(
            PlayWaveform(pattern),
            WaitMillis(100),
            PlayWaveform(pattern),
            WaitMillis(100),
            PlayWaveform(pattern)
        )

        drv2605.go()
        while drv2605.busy():
            time.sleep(0.01)

    else:
        drv2605.set_mode('Real-time Playback')
        drv2605.set_realtime_data_format('Unsigned')
        drv2605.go()
        try:
            while True:
                d = time.time() * 10
                x = (math.sin(d) + 1) / 2
                x = int(x * 255)
                drv2605.set_realtime_input(x)
                print("Waveform: {}".format(x))
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        finally:
            drv2605.set_realtime_input(0)
            drv2605.stop()



            

        
