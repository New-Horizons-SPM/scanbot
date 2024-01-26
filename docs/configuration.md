# Configuration
When running Scanbot in browser, terminal, or Zulip modes, you must create the scanbot_config.ini configuration file which gets loaded from ~/scanbot on startup.
<strong>When running Scanbot as web app, see [here](../web-app/#configuration)</strong>.

## TCP Connection
For communicating with Nanonis V5 software, you must configure the TCP settings.
Scanbot requires at least two ports to perform correctly

```
ip=<IP Adress>          # IP adress of the machine running Nanonis. Defaults to local host 127.0.0.1
port_list=<P1,P2,...>   # Available ports. See Nanonis => Main Options => TCP Programming Interface.
```


## Data Storage
Data acquired during Scanbot's operation can be saved in a few ways by setting the ```upload_method``` field.

1. ```upload_method=path``` configures Scanbot to convert acquired images to PNG format and save them locally to a path specified by ```path=<path>```.
2. ```upload_method=zulip``` configures Scanbot to send PNGs via [Zulip](https://zulip.com/). The [zuliprc](https://zulip.com/api/running-bots) file must be included in the config as ```zuliprc=<path_to_zuliprc>```
3. ```upload_method=firebase``` configures Scanbot to upload PNGs to [Google Firebase Storage](https://firebase.google.com/docs/storage). 
If using firebase, set the ```firebase_storage_bucket=<bucket>``` field. Then then ```path=<path>``` field is used as the destination on Firebase.
For Zulip users, this Firebase link would be sent in lieu of a PNG file.
4. ```upload_method=no_upload``` prevents Scanbot from converting and saving the images it takes. **This is the default setting.**

Alternatively, Scanbot can [SCP](https://en.wikipedia.org/wiki/Secure_copy_protocol) data to a server by setting the following field:

```
scp_path=<user@host:path>   # ssh key must be set up for this to work
```

## Nanonis Configuration
The following optional fields relate to Nanonis configuration
```
topo_basename=<.sxm basename>   # base filename used when saving .sxm files. Defaults to whatever is in Nanonis if not provided. 
temp_calibration_curve=<path>   # Path to the temperature calibration curve so Scanbot can read STM temperature.
```

## Tip Crash Safety
The following fields set the parameters of the Z piezo when retracting the tip after a crash is detected.
```
safe_current=<current>              # A tunnelling current above this threshold is considered a tip crash
safe_retract_V=<Z_piezo_voltage>    # Voltage applied to the Z piezo when the tip is automatically retracted after a crash is detected
safe_retract_F=<Z_piezo_frequency>  # Frequency applied to the Z piezo when the tip is automatically retracted after a crash is detected
```

## Piezo Safety
The following fields configure the piezo voltage and frequency limits
```
piezo_z_max_V=<max_Z_piezo_voltage>     # Maximum voltage that can be applied to the Z piezo
piezo_z_min_V=<min_Z_piezo_voltage>     # Minimum voltage that can be applied to the Z piezo
piezo_xy_max_V=<max_XY_piezo_voltage>   # Maximum voltage that can be applied to the X or Y piezos
piezo_xy_min_V=<min_XY_piezo_voltage>   # Minimum voltage that can be applied to the X or Y piezos

piezo_z_max_F=<max_Z_piezo_frequency>   # Maximum frequency that can be applied to the Z piezo
piezo_z_min_F=<min_Z_piezo_frequency>   # Minimum frequency that can be applied to the Z piezo
piezo_xy_max_F=<max_XY_piezo_frequency> # Maximum frequency that can be applied to the X or Y piezos
piezo_xy_min_F=<min_XY_piezo_frequency> # Minimum frequency that can be applied to the X or Y piezos
```