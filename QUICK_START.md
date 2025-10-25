# Voice LCD Quick Start Guide

**Simple Voice Transcriber with Display & Custom Script Execution**

---

## What This Does

1. **Transcribes your speech** in real-time using offline voice recognition
2. **Displays transcribed text** on LCD or OLED screen
3. **Executes voice commands** to run any script on your Raspberry Pi
4. **Easy configuration** - just edit JSON to add new commands

---

## Basic Usage

### Start the Voice LCD

```bash
cd ~/Desktop/Voice_LCD
source venv/bin/activate
./voice_lcd.py
```

### Say Commands

1. Say the wake word: **"Pi"** or **"Pie"**
2. Follow with your command: **"time"**, **"weather"**, **"ip"**, etc.
3. Watch the transcription appear on your display!

**Example:** *"Pi, what's the time?"*

---

## Adding Your Own Voice Commands (3 Easy Steps)

### Step 1: Open Config File

```bash
nano voice_config.json
```

### Step 2: Add Your Command

Add this to the `"commands"` section:

```json
"my command": {
  "action": "run_command",
  "aliases": ["alternative phrase", "another way to say it"],
  "command": "/path/to/your/script.sh",
  "display_format": ["Script Result:", "{output}"],
  "timeout": 10
}
```

### Step 3: Save and Restart

- Save the file (Ctrl+O, Enter, Ctrl+X in nano)
- Restart voice_lcd.py
- Try saying: **"Pi, my command"**

---

## Example: Add a "Take Photo" Command

```json
"take photo": {
  "action": "run_command",
  "aliases": ["camera", "picture", "snap"],
  "command": "raspistill -o /home/morph/photos/photo_$(date +%s).jpg && echo 'Photo saved!'",
  "display_format": ["Camera:", "{output}"],
  "timeout": 5
}
```

Now say: **"Pi, take photo"** or **"Pi, camera"**

---

## Running Custom Scripts

### Create Your Script

```bash
#!/bin/bash
# /home/morph/my_scripts/hello.sh

echo "Hello from my script!"
date +"%H:%M:%S"
```

Make it executable:

```bash
chmod +x /home/morph/my_scripts/hello.sh
```

### Add Voice Command

```json
"run hello": {
  "action": "run_command",
  "command": "/home/morph/my_scripts/hello.sh",
  "display_format": ["Script says:", "{output}"]
}
```

---

## Command Action Types

### 1. `run_command` - Run Any Script or Shell Command

```json
"backup files": {
  "action": "run_command",
  "command": "/home/morph/backup.sh",
  "timeout": 30,
  "show_errors": true
}
```

**Options:**
- `timeout`: Max seconds to wait (optional)
- `show_errors`: Show error messages if command fails (default: true)
- `display_format`: Two-line format for LCD

### 2. `custom_message` - Display Text with Variables

```json
"show info": {
  "action": "custom_message",
  "message": "Time: {time}, Date: {date}, IP: {ip}",
  "scroll_duration": 5
}
```

**Available Variables:**
- `{ip}` - Your IP address
- `{time}` - Current time (HH:MM:SS)
- `{date}` - Current date (MM/DD/YY)
- `{random_1_100}` - Random number 1-100
- `{output}` - Output from run_command

### 3. Built-in Actions

```json
"clear screen": {
  "action": "clear_display"
},

"show time": {
  "action": "show_time",
  "time_format": "%H:%M:%S",
  "date_format": "%m/%d/%y"
},

"show ip": {
  "action": "show_ip",
  "display_format": ["IP Address:", "{ip}"]
}
```

---

## Common Use Cases

### Control GPIO Pins (LEDs, Relays)

```json
"lights on": {
  "action": "run_command",
  "command": "gpio -g write 17 1 && echo 'ON'",
  "display_format": ["GPIO 17:", "{output}"]
}
```

### Read Sensor Data

```json
"check sensor": {
  "action": "run_command",
  "command": "python3 /home/morph/read_temp_sensor.py",
  "display_format": ["Temperature:", "{output}"]
}
```

### System Automation

```json
"shutdown": {
  "action": "run_command",
  "command": "echo 'Shutting down in 10s' && sleep 10 && sudo shutdown -h now",
  "display_format": ["Shutting down", "in 10 seconds..."]
}
```

### Run Python Scripts

```json
"analyze data": {
  "action": "run_command",
  "command": "python3 /home/morph/analyze.py --quick",
  "timeout": 30,
  "display_format": ["Analysis:", "{output}"]
}
```

---

## Troubleshooting

### Voice Recognition Not Working

**Check model path:**
```bash
ls -l models/vosk-model-small-en-us-0.15
```

If missing, the config might have wrong path. Edit `voice_config.json`:
```json
"model_path": "./models/vosk-model-small-en-us-0.15"
```

### Display Not Working

**Check I2C connection:**
```bash
i2cdetect -y 1
```

You should see your LCD address (usually 0x3f or 0x27).

**Update config if different address:**
```json
"hardware": {
  "lcd_i2c_address": "0x27",  // Change to your address
  "i2c_port": 1
}
```

### Script Not Running

1. **Make script executable:**
   ```bash
   chmod +x /path/to/your/script.sh
   ```

2. **Use full absolute paths** in commands

3. **Test script manually first:**
   ```bash
   /path/to/your/script.sh
   ```

4. **Check timeout** - increase if script takes longer

### Commands Not Recognized

1. **Check wake word** - say "Pi" or "Pie" clearly first
2. **Add aliases** for different phrasings:
   ```json
   "aliases": ["alternative", "another way", "different phrase"]
   ```
3. **Enable transcription view** to see what's heard:
   ```json
   "show_all_transcriptions": true
   ```

---

## Configuration Tips

### Use Relative Paths

```json
"model_path": "./models/vosk-model-small-en-us-0.15",
"log_file": "./voice_lcd.log"
```

### Multiple Wake Words

```json
"wake_words": ["pi", "pie", "computer", "hey pi"]
```

### Adjust for Your Mic

```json
"audio_sample_rate": 16000,  // Try 16000 or 22050
"audio_chunk_size": 2048     // Try 2048 or 4096
```

---

## Example Configs

See the `examples/` directory:

- **simple_config.json** - Basic setup
- **smart_home_config.json** - Home automation examples
- **script_commands_template.json** - Comprehensive script running guide

Copy an example to get started:

```bash
cp examples/simple_config.json voice_config.json
```

---

## Next Steps

1. **Test built-in commands**: Try "Pi time", "Pi weather", "Pi ip"
2. **Add your first custom command**: Follow the 3-step guide above
3. **Write your first script**: Start simple, then expand
4. **Customize wake words**: Pick words that work for you
5. **Share your configs**: Submit cool commands to the community!

---

## Need Help?

- Check `CLAUDE.md` for full project documentation
- See `OLED_FALLBACK_README.md` for OLED-specific info
- Review `voice_config.json` comments for all options
- Read `examples/script_commands_template.json` for advanced scripting

**Happy voice commanding! 🎤**
