# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi LCD display system with three main applications:
- **Digital Zen Garden** - Ambient visual patterns for meditation/decoration
- **Voice-Controlled LCD** - Configurable voice commands for system interaction
- **Utility Scripts** - IP display and messaging tools

## Hardware Requirements

- Raspberry Pi (any model with I2C support)
- I2C LCD display (16x2 or 20x4) with PCF8574 backpack
- I2C connections: SDA, SCL, VCC, GND
- USB microphone (for voice features)
- Default LCD I2C address: `0x3f`

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Enable I2C on Raspberry Pi
sudo raspi-config  # Interface Options > I2C > Enable

# Test I2C connection
i2cdetect -y 1

# Check audio devices
arecord -l
```

### Running Applications
```bash
# Digital Zen Garden (ambient display)
python3 zen_garden.py

# Voice LCD with default config
python3 voice_lcd.py

# Voice LCD with custom config
python3 voice_lcd.py examples/simple_config.json

# IP Display utility
python3 ip_display.py

# LCD Messenger CLI
python3 lcd_messenger.py "Your message here"
```

## Architecture

### Core Applications

1. **zen_garden.py** - Self-contained ambient display with 6 animated scenes
2. **voice_lcd.py** - Voice-activated LCD system with JSON configuration
3. **ip_display.py** - Network IP address display with animations
4. **lcd_messenger.py** - CLI tool for scrolling messages

### Configuration System

Voice LCD uses `voice_config.json` for complete customization:
- **Hardware settings**: I2C address, LCD dimensions, audio parameters
- **Display settings**: Scroll speed, timing, messages
- **Voice recognition**: Wake words, model path, transcription options
- **Commands**: Action types, aliases, custom messages
- **Advanced**: Logging, config reloading, command history

### Voice Command Architecture

Commands are processed through an extensible action system:
- `show_ip` - Display network IP address
- `show_time` - Current time/date display
- `tell_joke` - Random jokes with scrolling
- `custom_message` - User-defined text with variable substitution
- `run_command` - Execute shell commands and display output
- `clear_display` - Clear the LCD screen

### Variable Substitution System

Support for dynamic content in messages:
- `{ip}` - Current IP address
- `{time}` - Current time (HH:MM:SS)
- `{date}` - Current date (MM/DD/YY)
- `{random_X_Y}` - Random number between X and Y
- `{output}` - Shell command output

## Configuration Files

- `voice_config.json` - Main voice LCD configuration
- `examples/simple_config.json` - Basic setup example
- `examples/smart_home_config.json` - Advanced home automation setup
- `requirements.txt` - Python dependencies
- `models/` - Vosk speech recognition models

## Development Patterns

### LCD Display Classes
All display classes follow a common pattern:
- I2C initialization with graceful fallback
- Hardware detection and error handling
- Text centering and display utilities
- Signal handlers for clean shutdown

### Configuration Loading
Voice LCD uses JSON-based configuration with:
- Nested structure for different setting categories
- Default values with override capability
- Runtime config validation
- Support for config file reloading

### Error Handling
- Graceful degradation when hardware unavailable
- Console output fallback when LCD not connected
- Comprehensive logging system (configurable)
- User-friendly error messages

## Speech Recognition

Uses Vosk offline speech recognition:
- Model path: `/home/morph/Desktop/LCD/models/vosk-model-small-en-us-0.15`
- Wake word detection with configurable phrases
- Command timeout and retry logic
- Transcription debugging support

## Testing Hardware

```bash
# Test LCD connection
python3 -c "from RPLCD.i2c import CharLCD; lcd = CharLCD('PCF8574', 0x3f); lcd.write_string('Test')"

# Test microphone
arecord -d 5 test.wav && aplay test.wav

# Check I2C devices
i2cdetect -y 1
```

## Adding New Voice Commands

1. Add command definition to `voice_config.json`:
```json
"new_command": {
  "action": "custom_message",
  "aliases": ["alternative phrase"],
  "message": "Response text with {variables}",
  "scroll_duration": 5
}
```

2. For new action types, extend `execute_action()` method in `voice_lcd.py`

## File Organization

- Root level: Main application scripts
- `examples/` - Configuration examples and templates
- `models/` - Speech recognition model files
- `venv/` - Python virtual environment (generated)
- Logs written to `voice_lcd.log` when enabled