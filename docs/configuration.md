# Configuration
scanbot_config.ini is the Scanbot configuration file that is loaded on startup.

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

Alternatively, Scanbot can [SCP](https://en.wikipedia.org/wiki/Secure_copy_protocol) data to a server by setting the following two fields:

```
scp=true                    # Flag to turn feature on and off
scp_path=<user@host:path>   # ssh key must be set up for this to work
```

## Nanonis Configuration
The following optional fields relate to Nanonis configuration
```
topo_basename=<.sxm basename>   # base filename used when saving .sxm files. Defaults 
temp_calibration_curve=<path>   # Path to the temperature calibration curve so Scanbot can read STM temperature.
```