from collections import OrderedDict

class scanbot_config():
    label       = 0
    description = 1
    category    = 2
    value       = 3
    def __init__(self, module_dir="./"):
        self.config = OrderedDict(
                      # key                         : [label, description, category, default value] 
                      {# 'path'                      : ['Path',                          'Path to save data',                                                                'external', 'scanbot_data'],
                        'port_list'                 : ['TCP Ports',                     'Comma delimited ports (nanonis => Main Options => TCP Programming Interface)',     'tcp',      '6502,6503'],
                        'ip'                        : ['IP Address',                    'IP address of the pc controlling nanonis',                                         'tcp',      '127.0.0.1'],
                        'topo_basename'             : ['Topo basename',                 'Basename for .sxm files. Leave blank to use current value in nanonis',             'nanonis',  ''],
                        'safe_current'              : ['Crash Current (A)',             'When the current goes above this threhold the tip is considered crashed',          'safety',   '5e-9'],
                        'safe_retract_V'            : ['Crash Retract Voltage (V)',     'Voltage (V) applied to the Z piezo when retracting tip if a crash is detected',    'safety',   '200'],
                        'safe_retract_F'            : ['Crash Retract Frequency (Hz)',  'Frequency (Hz) applied to the Z piezo when retracting tip if a crash is detected', 'safety',   '1500'],
                        # 'piezo_z_max_V'             : ['Max Z Piezo Voltage (V)',       'Maximum voltage that Scanbot can apply to the Z piezo',                            'safety',   '200'],
                        # 'piezo_z_min_V'             : ['Min Z Piezo Voltage (V)',       'Minimum voltage that Scanbot can apply to the Z piezo',                            'safety',   '0'],
                        # 'piezo_xy_max_V'            : ['Max XY Piezo Voltage (V)',      'Maximum voltage that Scanbot can apply to the XY piezos',                          'safety',   '200'],
                        # 'piezo_xy_min_V'            : ['Min XY Piezo Voltage (V)',      'Minimum voltage that Scanbot can apply to the XY piezos',                          'safety',   '0'],
                        # 'piezo_z_max_F'             : ['Max Z Piezo Frequency (Hz)',    'Maximum frequency that Scanbot can apply to the Z piezo',                          'safety',   '5000'],
                        # 'piezo_z_min_F'             : ['Min Z Piezo Frequency (Hz)',    'Minimum frequency that Scanbot can apply to the Z piezo',                          'safety',   '500'],
                        # 'piezo_xy_max_F'            : ['Max XY Piezo Frequency (Hz)',   'Maximum frequency that Scanbot can apply to the XY piezos',                        'safety',   '5000'],
                        # 'piezo_xy_min_F'            : ['Min XY Piezo Frequency (Hz)',   'Minimum frequency that Scanbot can apply to the XY piezos',                        'safety',   '500'],
                        # 'hk_commands'               : ['0']                         # Flag to look for customised commands in hk_commands
                        'nanonis_version'           : ['Nanonis Version Number',        'Version of the host nanonis. See nanonis > help > info and take the RT Engine version number. Defaults to the latest version', 'tcp', '99999999'],
                      })
        
        try:
            with open(module_dir + 'scanbot_config.ini','r') as f:                  # Go through the config file to see what defaults need to be overwritten
                line = "begin"
                while(line):
                    line = f.readline()[:-1]
                    if(line.startswith('#')): print(line); continue                 # Comment
                    if(not '=' in line):
                        print("WARNING: invalid line in config file: " + line)
                        continue
                    key, value = line.split('=')                                    # Format for valid line is "Key=Value"
                    if(not key in self.config):                                     # Key must be one of config keys
                        print("WARNING: Invalid key in scanbot_config.ini: " + key)
                        continue
                    self.config[key][self.value] = value                            # Overwrite value
        except Exception as e:
            print(e)
            print("Config file not found, using defaults...")
    
    def setConfig(self,config):
        self.config = config