#!/usr/bin/env python3
"""
Voice LCD v2 - Configurable voice-activated display system
Config: voice_config.json
"""
import sys
import os
import json
import time
import random
import subprocess
import socket
import re
import logging
from datetime import datetime

sys.path.insert(0, '/home/morph/Desktop/LCD/venv/lib/python3.11/site-packages')

try:
    import vosk
    import pyaudio
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False

try:
    from RPLCD.i2c import CharLCD
    HAS_LCD = True
except ImportError:
    HAS_LCD = False

class VoiceLCDv2:
    def __init__(self, config_path="voice_config.json"):
        self.config_path = config_path
        self.logger = None  # Initialize logger first
        self.load_config()
        
        # Setup logging
        if self.config.get("advanced", {}).get("enable_logging", False):
            log_file = self.config["advanced"].get("log_file", "voice_lcd.log")
            logging.basicConfig(filename=log_file, level=logging.INFO,
                              format='%(asctime)s - %(levelname)s - %(message)s')
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = None
        
        # LCD setup
        self.setup_lcd()
        
        # Speech setup
        self.setup_speech()
        
        # Command history
        self.command_history = []
        
        self.log("Voice LCD v2 initialized")
    
    def log(self, message):
        """Log message if logging enabled"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        if self.logger:
            self.logger.info(message)
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            self.log(f"Config loaded from {self.config_path}")
        except Exception as e:
            self.log(f"Error loading config: {e}")
            self.config = self.default_config()
    
    def default_config(self):
        """Fallback config if file missing"""
        return {
            "hardware": {"lcd_i2c_address": "0x3f", "lcd_cols": 16, "lcd_rows": 2},
            "display": {"scroll_speed": 0.15, "short_text_display_time": 3.0},
            "voice": {"wake_words": ["pi", "pie"], "show_all_transcriptions": True},
            "commands": {}, "messages": {"jokes": ["No jokes configured!"]},
            "advanced": {"enable_logging": False}
        }
    
    def setup_lcd(self):
        """Initialize LCD display"""
        hw = self.config["hardware"]
        if HAS_LCD:
            try:
                addr = int(hw["lcd_i2c_address"], 16)
                self.lcd = CharLCD('PCF8574', addr, 
                                 cols=hw["lcd_cols"], rows=hw["lcd_rows"])
                self.lcd.clear()
                self.has_display = True
                self.log(f"LCD connected at {hw['lcd_i2c_address']}")
            except Exception as e:
                self.log(f"LCD setup failed: {e}")
                self.has_display = False
        else:
            self.has_display = False
            self.log("LCD libraries not available")
    
    def setup_speech(self):
        """Initialize speech recognition"""
        if not HAS_VOSK:
            self.has_speech = False
            self.log("Vosk not available")
            return
        
        voice_config = self.config["voice"]
        model_path = voice_config["model_path"]
        
        if not os.path.exists(model_path):
            self.has_speech = False
            self.log(f"Speech model not found at {model_path}")
            return
        
        try:
            self.log("Loading speech model... (30+ seconds)")
            self.model = vosk.Model(model_path)
            
            hw = self.config["hardware"]
            self.rec = vosk.KaldiRecognizer(self.model, hw["audio_sample_rate"])
            self.has_speech = True
            self.log("Speech recognition ready!")
        except Exception as e:
            self.log(f"Speech setup failed: {e}")
            self.has_speech = False
    
    def display_text(self, line1="", line2=""):
        """Display text on LCD"""
        cols = self.config["hardware"]["lcd_cols"]
        
        if self.has_display:
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(line1[:cols].ljust(cols))
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2[:cols].ljust(cols))
        else:
            print(f"LCD: '{line1}' | '{line2}'")
    
    def scroll_text(self, text, line=2, duration=None, cycles=None):
        """Scroll text on specified line"""
        if not text:
            return
            
        cols = self.config["hardware"]["lcd_cols"]
        speed = self.config["display"]["scroll_speed"]
        cycles = cycles or self.config["display"].get("heard_text_cycles", 2)
        
        padded = " " * cols + text + " " * cols
        
        if duration:
            # Time-based scrolling
            start_time = time.time()
            while time.time() - start_time < duration:
                for i in range(len(padded) - cols + 1):
                    if time.time() - start_time >= duration:
                        break
                    if line == 1:
                        self.display_text(padded[i:i+cols], "")
                    else:
                        self.display_text("", padded[i:i+cols])
                    time.sleep(speed)
        else:
            # Cycle-based scrolling
            for cycle in range(cycles):
                for i in range(len(padded) - cols + 1):
                    if line == 1:
                        self.display_text(padded[i:i+cols], "")
                    else:
                        self.display_text("Heard:", padded[i:i+cols])
                    time.sleep(speed)
            
            # Show static view briefly
            if line == 2:
                self.display_text("Heard:", text[:cols])
                time.sleep(1)
    
    def substitute_variables(self, text):
        """Replace variables in text with actual values"""
        # Random numbers
        text = re.sub(r'\{random_(\d+)_(\d+)\}', 
                     lambda m: str(random.randint(int(m.group(1)), int(m.group(2)))), text)
        
        # IP address
        if '{ip}' in text:
            text = text.replace('{ip}', self.get_ip())
        
        # Current time/date
        if '{time}' in text:
            text = text.replace('{time}', datetime.now().strftime("%H:%M:%S"))
        if '{date}' in text:
            text = text.replace('{date}', datetime.now().strftime("%m/%d/%y"))
        
        return text
    
    def get_ip(self):
        """Get Pi's IP address"""
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split()[0]
        except:
            pass
        return "No Network"
    
    def execute_action(self, action_type, command_config, command_text=""):
        """Execute different types of actions"""
        if action_type == "show_ip":
            ip = self.get_ip()
            fmt = command_config.get("display_format", ["IP Address:", "{ip}"])
            self.display_text(fmt[0], self.substitute_variables(fmt[1]))
            time.sleep(self.config["display"]["command_result_time"])
        
        elif action_type == "show_time":
            now = datetime.now()
            time_fmt = command_config.get("time_format", "%H:%M:%S")
            date_fmt = command_config.get("date_format", "%m/%d/%y")
            self.display_text(now.strftime(time_fmt), now.strftime(date_fmt))
            time.sleep(self.config["display"]["command_result_time"])
        
        elif action_type == "tell_joke":
            jokes = self.config["messages"]["jokes"]
            joke = random.choice(jokes)
            duration = command_config.get("scroll_duration", 8)
            self.scroll_text(joke, line=1, duration=duration)
        
        elif action_type == "custom_message":
            message = self.substitute_variables(command_config["message"])
            duration = command_config.get("scroll_duration", 5)
            if len(message) <= self.config["hardware"]["lcd_cols"]:
                self.display_text(message, "")
                time.sleep(duration)
            else:
                self.scroll_text(message, line=1, duration=duration)
        
        elif action_type == "run_command":
            try:
                cmd = command_config["command"]
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                output = result.stdout.strip()[:50]  # Limit output length
                
                fmt = command_config.get("display_format", ["Output:", "{output}"])
                line1 = fmt[0] if len(fmt) > 0 else "Output:"
                line2 = fmt[1].replace("{output}", output) if len(fmt) > 1 else output
                
                if len(line2) <= self.config["hardware"]["lcd_cols"]:
                    self.display_text(line1, line2)
                    time.sleep(self.config["display"]["command_result_time"])
                else:
                    self.display_text(line1, "")
                    time.sleep(0.5)
                    self.scroll_text(line2, line=2, cycles=2)
                    
            except Exception as e:
                self.display_text("Command Error:", str(e)[:16])
                time.sleep(3)
        
        elif action_type == "clear_display":
            if self.has_display:
                self.lcd.clear()
            time.sleep(1)
    
    def find_matching_command(self, text):
        """Find command that matches the spoken text"""
        text_lower = text.lower()
        
        for command_name, command_config in self.config["commands"].items():
            # Check main command name
            if command_name in text_lower:
                return command_name, command_config
            
            # Check aliases
            aliases = command_config.get("aliases", [])
            for alias in aliases:
                if alias.lower() in text_lower:
                    return command_name, command_config
        
        return None, None
    
    def handle_command(self, text):
        """Process recognized speech"""
        text = text.strip()
        self.log(f"Processing: '{text}'")
        
        # Add to history
        if self.config["advanced"].get("enable_command_history", False):
            self.command_history.append((datetime.now(), text))
            max_history = self.config["advanced"].get("max_command_history", 50)
            if len(self.command_history) > max_history:
                self.command_history.pop(0)
        
        # Find matching command
        command_name, command_config = self.find_matching_command(text)
        
        if command_config:
            self.log(f"Executing command: {command_name}")
            action = command_config["action"]
            self.execute_action(action, command_config, text)
        else:
            # No command found
            error_msgs = self.config["messages"].get("error_responses", 
                                                   ["Command not recognized"])
            error_msg = random.choice(error_msgs)
            self.scroll_text(error_msg, line=1, duration=3)
    
    def listen(self):
        """Main listening loop"""
        if not self.has_speech:
            self.log("Speech recognition not available - check model path")
            return
        
        # Display startup message
        startup = self.config["display"]["startup_message"]
        self.display_text(startup[0], startup[1])
        
        # Audio setup
        hw = self.config["hardware"] 
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, channels=1, 
                          rate=hw["audio_sample_rate"], input=True,
                          frames_per_buffer=hw["audio_chunk_size"])
        
        wake_words = self.config["voice"]["wake_words"]
        show_all = self.config["voice"]["show_all_transcriptions"]
        
        self.log(f"Listening for wake words: {', '.join(wake_words)}")
        
        try:
            while True:
                data = stream.read(hw["audio_chunk_size"], exception_on_overflow=False)
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        if show_all:
                            # Show what was heard
                            cols = self.config["hardware"]["lcd_cols"]
                            if len(text) <= cols:
                                self.display_text("Heard:", text)
                                time.sleep(self.config["display"]["short_text_display_time"])
                            else:
                                self.display_text("Heard:", "")
                                time.sleep(0.5)
                                self.scroll_text(text, line=2)
                        
                        # Check for wake words
                        text_lower = text.lower()
                        wake_detected = any(wake_word in text_lower for wake_word in wake_words)
                        
                        if wake_detected:
                            self.handle_command(text)
                        
                        # Return to ready state (don't overwrite transcriptions)
                        # Only clear if no recent transcription
                        time.sleep(0.5)
                        
        except KeyboardInterrupt:
            self.log("Stopped by user")
        finally:
            stream.stop_stream()
            stream.close() 
            audio.terminate()
            if self.has_display:
                self.lcd.clear()
            self.log("Shutdown complete")

def main():
    try:
        vlcd = VoiceLCDv2()
        vlcd.listen()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()