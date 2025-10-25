# Govee Light Control Integration

Voice control your Govee smart lights directly from Voice LCD using local network control (no cloud/internet required).

---

## Features

✅ **Voice-activated control** - "Pi, light on", "Pi, red light", "Pi, dim"
✅ **Local network only** - No internet dependency
✅ **Fast response** - Direct UDP communication
✅ **Multiple controls** - Power, brightness, colors, temperature
✅ **Works with existing Govee devices** - H61D5, H61A1, and more

---

## Quick Start

### Prerequisites

1. **Govee device on same network as Pi**
2. **LAN Control enabled** in Govee Home app:
   - Open Govee Home app
   - Select your device
   - Settings → LAN Control → Enable

3. **govee-ai repository** at `/home/morph/Desktop/govee-ai/`
   - Already installed and configured
   - Devices already discovered (see govee-ai/devices.json)

### Test Govee Control

```bash
# Test standalone script
cd ~/Desktop/Voice_LCD/examples/custom_scripts
./govee_control.sh on
./govee_control.sh off
./govee_control.sh color red
```

### Use Voice Commands

Start Voice LCD and try:

- **"Pi, light on"** - Turn on Govee light
- **"Pi, light off"** - Turn off
- **"Pi, bright"** - Set to 100% brightness
- **"Pi, dim"** - Set to 20% brightness
- **"Pi, red light"** - Change to red color
- **"Pi, warm light"** - Warm white (3000K)

---

## Available Voice Commands

### Power Control
| Voice Command | Aliases | Action |
|---------------|---------|--------|
| "light on" | "govee on", "lights on", "turn on light" | Turn device on |
| "light off" | "govee off", "lights off", "turn off light" | Turn device off |

### Brightness Control
| Voice Command | Aliases | Brightness |
|---------------|---------|------------|
| "bright" | "full brightness", "maximum brightness" | 100% |
| "medium brightness" | "medium", "half brightness" | 50% |
| "dim" | "low brightness", "dim light" | 20% |

### Color Control
| Voice Command | Aliases | Color |
|---------------|---------|-------|
| "red light" | "make it red", "color red" | Red (255,0,0) |
| "blue light" | "make it blue", "color blue" | Blue (0,0,255) |
| "green light" | "make it green", "color green" | Green (0,255,0) |
| "white light" | "make it white", "color white" | White (255,255,255) |

### Temperature Control
| Voice Command | Aliases | Temperature |
|---------------|---------|-------------|
| "warm light" | "warm white", "cozy light" | 3000K (warm) |
| "cool light" | "cool white", "daylight" | 6500K (cool) |

---

## How It Works

### Architecture

```
Voice LCD (voice_lcd.py)
    ↓
Voice Command: "Pi, light on"
    ↓
voice_config.json → run_command action
    ↓
govee_control.sh (wrapper script)
    ↓
govee.py (CLI from govee-ai repo)
    ↓
UDP multicast commands (port 4003)
    ↓
Govee Device (local network)
```

### Components

**1. govee_control.sh**
- Location: `Voice_LCD/examples/custom_scripts/govee_control.sh`
- Purpose: Bash wrapper that simplifies govee.py CLI calls
- Features: Error handling, short output for LCD, color name mapping

**2. govee.py**
- Location: `/home/morph/Desktop/govee-ai/govee.py`
- Purpose: Complete CLI controller for Govee devices
- Features: Device discovery, power, brightness, RGB, temperature control

**3. govee_api.py**
- Location: `/home/morph/Desktop/govee-ai/govee_api.py`
- Purpose: Python API library for programmatic control
- Features: Device discovery, command sending, status queries

**4. voice_config.json**
- Location: `Voice_LCD/voice_config.json`
- Purpose: Voice command definitions
- Contains: 12 Govee-related voice commands (lines 184-270)

---

## Manual Control

### Using the Wrapper Script

```bash
cd ~/Desktop/Voice_LCD/examples/custom_scripts

# Power
./govee_control.sh on
./govee_control.sh off

# Brightness (1-100)
./govee_control.sh brightness 75

# Colors
./govee_control.sh color red
./govee_control.sh color blue
./govee_control.sh color green

# Temperature
./govee_control.sh warm    # 3000K
./govee_control.sh cool    # 6500K

# Utility
./govee_control.sh scan    # Find devices
./govee_control.sh status  # Check status
./govee_control.sh help    # Show usage
```

### Using govee.py Directly

```bash
cd /home/morph/Desktop/govee-ai

# Discovery
python3 govee.py scan      # Find any Govee device
python3 govee.py discover  # Find specific device (H61D5)

# Control
python3 govee.py on
python3 govee.py off
python3 govee.py brightness 75
python3 govee.py rgb 255 0 0      # Red
python3 govee.py temp 4000        # 4000K temperature
python3 govee.py status           # Query device
```

---

## Network Requirements

### Ports
- **4001** - UDP multicast scan requests
- **4002** - UDP device discovery responses
- **4003** - UDP device control commands

### Protocol
- **UDP multicast** to `239.255.255.250`
- **JSON-formatted** commands and responses
- **No authentication** required (LAN Control must be enabled)

### Device Requirements
- Device firmware must support LAN Control
- Device and Pi must be on same subnet
- UDP ports must not be blocked by firewall

---

## Discovered Devices

Your system has 2 Govee devices already discovered:

**Device 1: H61D5**
- MAC: `15:61:D0:32:34:39:32:1C`
- IP: `192.168.1.212`
- Model: H61D5

**Device 2: H61A1**
- MAC: `92:E4:60:74:F4:35:4F:17`
- IP: `192.168.3.205`
- Model: H61A1

Device info stored in: `/home/morph/Desktop/govee-ai/devices.json`

---

## Troubleshooting

### Voice Commands Not Working

1. **Test script directly:**
   ```bash
   cd ~/Desktop/Voice_LCD/examples/custom_scripts
   ./govee_control.sh on
   ```

2. **Check if govee-ai works:**
   ```bash
   cd /home/morph/Desktop/govee-ai
   python3 govee.py scan
   ```

3. **Verify Voice LCD can call script:**
   - Check path in voice_config.json is correct
   - Ensure script is executable: `chmod +x govee_control.sh`

### Device Not Responding

1. **Verify LAN Control enabled** in Govee Home app
2. **Check device is on network:**
   ```bash
   ping 192.168.1.212  # Replace with your device IP
   ```
3. **Rescan for devices:**
   ```bash
   cd /home/morph/Desktop/govee-ai
   python3 govee.py scan
   ```
4. **Check firewall** - UDP ports 4001-4003 must be open

### Multiple Devices

Currently controls the first discovered device. To control specific device:

**Option 1: Modify govee.py default MAC**
```python
# Edit govee.py line 18
def __init__(self, device_mac: str = "YOUR:DEVICE:MAC:HERE"):
```

**Option 2: Use govee_api.py**
Create custom Python script targeting specific device by MAC.

---

## Adding More Colors

Edit `govee_control.sh` to add more color options:

```bash
case "$VALUE" in
    red)      RGB="255 0 0" ;;
    blue)     RGB="0 0 255" ;;
    # Add your colors here:
    purple)   RGB="128 0 128" ;;
    cyan)     RGB="0 255 255" ;;
    orange)   RGB="255 165 0" ;;
    # etc...
esac
```

Then add corresponding voice command to `voice_config.json`.

---

## Advanced Usage

### Python API Integration

For more complex automation, use govee_api.py directly:

```python
from govee_api import GoveeAPI

api = GoveeAPI()
devices = api.discover_devices()

if devices:
    mac = devices[0].mac
    api.turn_on(mac)
    api.set_brightness(mac, 75)
    api.set_color_rgb(mac, 255, 0, 0)
```

### Examples Available

The govee-ai repository includes example scripts:
- `examples/disco_mode.py` - Rainbow color cycling
- `examples/sunrise_simulator.py` - Gradual brightness increase
- `examples/sunset_simulator.py` - Gradual dimming
- `examples/mood_lighting.py` - Smooth color transitions

---

## Related Files

| File | Purpose |
|------|---------|
| `voice_config.json` | Voice command definitions (lines 184-270) |
| `examples/custom_scripts/govee_control.sh` | Wrapper script for CLI |
| `/home/morph/Desktop/govee-ai/govee.py` | CLI controller |
| `/home/morph/Desktop/govee-ai/govee_api.py` | Python API |
| `/home/morph/Desktop/govee-ai/devices.json` | Discovered devices cache |

---

## Credits

- **Govee LAN API** - Local network control protocol
- **govee-ai repository** - CLI and API implementation
- **Voice LCD** - Voice command integration

---

**Enjoy voice-controlled lighting! 🎤💡**
