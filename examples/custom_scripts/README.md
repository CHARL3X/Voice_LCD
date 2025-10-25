# Custom Voice Command Scripts

Example scripts you can use with voice commands.

## Usage

1. Copy a script to your preferred location
2. Make it executable: `chmod +x script.sh`
3. Add a voice command in `voice_config.json` pointing to the script
4. Test manually first: `./script.sh`

## Scripts Included

### hello_world.sh
Simple example that outputs a greeting. Great for testing.

**Voice command:**
```json
"hello world": {
  "action": "run_command",
  "command": "/path/to/hello_world.sh",
  "display_format": ["Script says:", "{output}"]
}
```

### gpio_control.sh
Control a GPIO pin (LED, relay, etc.). Modify GPIO_PIN variable for your setup.

**Voice commands:**
```json
"lights on": {
  "action": "run_command",
  "command": "/path/to/gpio_control.sh on 17",
  "display_format": ["GPIO 17:", "ON"]
},
"lights off": {
  "action": "run_command",
  "command": "/path/to/gpio_control.sh off 17",
  "display_format": ["GPIO 17:", "OFF"]
}
```

### notification.sh
Send a notification (can be extended to use ntfy, telegram, email, etc.)

**Voice command:**
```json
"send alert": {
  "action": "run_command",
  "command": "/path/to/notification.sh 'Voice command received'",
  "display_format": ["Alert:", "Sent"]
}
```

## Creating Your Own Scripts

### Script Guidelines

1. **Keep output short** - LCD displays are limited (16-50 chars)
2. **Use echo for output** - This shows on the display
3. **Handle errors** - Exit with error messages
4. **Make it executable** - `chmod +x your_script.sh`
5. **Test standalone** - Run without voice first

### Template

```bash
#!/bin/bash
# your_script.sh - Description

# Your logic here
if [ condition ]; then
    echo "Success message"
    exit 0
else
    echo "Error message"
    exit 1
fi
```

## Advanced Examples

### Python Script Template

```python
#!/usr/bin/env python3
# sensor_reader.py

import sys

try:
    # Your code here
    temperature = read_sensor()
    print(f"{temperature}°C")  # This shows on display
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
```

### Script with Arguments

```bash
#!/bin/bash
# control.sh <action> <device>

ACTION=$1
DEVICE=$2

case "$ACTION" in
    on)
        echo "Turning on $DEVICE"
        # Your on logic
        ;;
    off)
        echo "Turning off $DEVICE"
        # Your off logic
        ;;
    *)
        echo "Unknown: $ACTION"
        exit 1
        ;;
esac
```

## Tips

- **Test output length**: `./script.sh | wc -c` (should be < 50)
- **Handle spaces**: Use quotes in commands: `"/path/with spaces/script.sh"`
- **Environment**: Scripts run in voice_lcd's environment, not login shell
- **Permissions**: Scripts may need sudo for certain operations
- **Logging**: Add logging to debug: `echo "Debug" >> /tmp/script.log`
