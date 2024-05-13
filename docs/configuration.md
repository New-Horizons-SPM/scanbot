<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6MK4DRHXWM"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-6MK4DRHXWM');
</script>
# Configuration (Terminal Mode)
When running Scanbot in a terminal, you must create the scanbot_config.ini configuration file which gets loaded from ~/scanbot on startup.
<strong>When running Scanbot as web app, see [here](../web-app/#configuration)</strong>.

## TCP Connection
For communicating with Nanonis V5 software, you must configure the TCP settings.
Scanbot requires at least two ports to perform correctly

```
ip=<IP Adress>                  # IP adress of the machine running Nanonis. Defaults to local host 127.0.0.1
port_list=<P1,P2,...>           # Available ports. See Nanonis => Main Options => TCP Programming Interface.
```

## Data Storage
Scanbot can SCP data to a server by setting the following field:

```
scp_path=<user@host:path>       # ssh key must be set up for this to work
```

## Nanonis Configuration
The following optional fields relate to Nanonis configuration
```
topo_basename=<.sxm basename>   # base filename used when saving .sxm files. Defaults to whatever is in Nanonis if not provided. 
```

## Tip Crash Safety
The following fields set the parameters of the Z piezo when retracting the tip after a crash is detected.
```
safe_current=<current>              # A tunnelling current above this threshold is considered a tip crash
safe_retract_V=<Z_piezo_voltage>    # Voltage applied to the Z piezo when the tip is automatically retracted after a crash is detected
safe_retract_F=<Z_piezo_frequency>  # Frequency applied to the Z piezo when the tip is automatically retracted after a crash is detected
```