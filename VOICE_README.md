# Voice LCD v2 - Configurable Voice Control 🎤

Ultra-configurable voice-activated LCD display system for Raspberry Pi!

## Quick Start

```bash
# Run with default config
python voice_lcd_v2.py

# Use custom config
python voice_lcd_v2.py simple_config.json
```

## Features

✅ **Fully configurable** - Everything in JSON config  
✅ **Custom commands** - Add your own voice commands  
✅ **Multiple action types** - Display text, run shell commands, tell jokes  
✅ **Command aliases** - Multiple ways to trigger the same action  
✅ **Variable substitution** - Dynamic content like `{ip}`, `{time}`, `{random_1_100}`  
✅ **Smart scrolling** - Long text scrolls beautifully  
✅ **Extensible** - Easy to add new command types  

## Default Voice Commands

- **"Pi show IP"** - Display network IP address
- **"Pi tell joke"** - Random tech joke with scrolling
- **"Pi show time"** - Current time and date
- **"Pi weather"** - Current weather (needs internet)
- **"Pi CPU temp"** - System temperature 
- **"Pi uptime"** - How long system has been running
- **"Pi clear"** - Clear the display
- **"Pi hello"** - Friendly greeting

## Configuration

Edit `voice_config.json` to customize everything:

### Add Custom Commands
```json
"my command": {
  "action": "custom_message",
  "aliases": ["alternative phrase", "another way"],
  "message": "Hello {time}! Random: {random_1_10}",
  "scroll_duration": 5
}
```

### Action Types Available
- `show_ip` - Display IP address
- `show_time` - Display current time/date  
- `tell_joke` - Random joke from config
- `custom_message` - Display custom text with variables
- `run_command` - Execute shell command and show output
- `clear_display` - Clear the screen

### Variables You Can Use
- `{ip}` - Current IP address
- `{time}` - Current time (HH:MM:SS)
- `{date}` - Current date (MM/DD/YY)  
- `{random_X_Y}` - Random number between X and Y
- `{output}` - Output from shell commands

### Example Configs
- `examples/simple_config.json` - Basic setup
- `examples/smart_home_config.json` - Home automation theme

## Advanced Features

### Custom Wake Words
```json
"voice": {
  "wake_words": ["computer", "jarvis", "friday", "pi"]
}
```

### Shell Commands
```json
"disk space": {
  "action": "run_command",
  "command": "df -h / | awk 'NR==2{print $4\" free\"}'",
  "display_format": ["Free Space:", "{output}"]
}
```

### Multiple Aliases
```json
"shutdown": {
  "action": "run_command",
  "aliases": ["power off", "turn off", "shut down", "goodbye"],
  "command": "sudo shutdown -h +1"
}
```

## Troubleshooting

**Speech not working?**
- Check model path in config: `voice.model_path`
- Verify USB microphone is connected: `arecord -l`

**LCD not displaying?**
- Check I2C address in config: `hardware.lcd_i2c_address`
- Test with: `i2cdetect -y 1`

**Commands not recognized?**
- Enable `show_all_transcriptions: true` to see what it hears
- Add more aliases for your commands
- Speak clearly and wait for processing

## Adding New Features

Want to add a new action type? Edit the `execute_action()` method in `voice_lcd_v2.py`!

Example - add a "flash LED" action:
```python
elif action_type == "flash_led":
    # Your LED code here
    self.display_text("LED flashing!", "")
```

Then use it in config:
```json
"flash": {
  "action": "flash_led",
  "aliases": ["blink", "light up"]
}
```

## Tips

- **Speak clearly** - Pi Zero 2W processing takes 2-4 seconds
- **Use aliases** - Add multiple ways to say the same command  
- **Test transcription** - Enable `show_all_transcriptions` to debug
- **Keep it simple** - Shorter phrases work better than long sentences
- **Be patient** - Speech recognition is impressive but not instant!

---

**Have fun with your voice-controlled LCD!** 🚀