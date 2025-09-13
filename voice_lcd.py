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
import logging.handlers
import shutil
import struct
import array
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
        self.loggers = {}   # Component loggers
        self.load_config()
        
        # Setup enhanced logging system
        self.setup_logging()
        
        # LCD setup
        self.setup_lcd()
        
        # Speech setup
        self.setup_speech()
        
        # Command history
        self.command_history = []
        
        # Ring buffer initialization
        self.init_ring_buffer()
        
        self.log("Voice LCD v2 initialized")
    
    def setup_logging(self):
        """Setup enhanced logging system with rotation"""
        # Check for new logging config, fall back to legacy
        logging_config = self.config.get("logging")
        if not logging_config:
            # Legacy logging support
            legacy = self.config.get("advanced", {})
            if legacy.get("enable_logging", False):
                log_file = legacy.get("log_file", "voice_lcd.log")
                logging.basicConfig(filename=log_file, level=logging.INFO,
                                  format='%(asctime)s - %(levelname)s - %(message)s')
                self.logger = logging.getLogger(__name__)
            return
        
        if not logging_config.get("enabled", False):
            return
        
        # Setup main rotating logger
        main_config = logging_config["main_log"]
        log_file = main_config["file"]
        max_bytes = main_config.get("max_file_size_mb", 10) * 1024 * 1024
        backup_count = main_config.get("backup_count", 5)
        log_format = main_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Main rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        handler.setFormatter(logging.Formatter(log_format))
        
        # Setup main logger
        self.logger = logging.getLogger("voice_lcd_main")
        self.logger.setLevel(getattr(logging, main_config.get("level", "INFO")))
        self.logger.addHandler(handler)
        
        # Setup component loggers
        component_config = logging_config.get("component_logs", {})
        for component, config in component_config.items():
            if config.get("enabled", True):
                logger = logging.getLogger(f"voice_lcd_{component}")
                logger.setLevel(getattr(logging, config.get("level", "INFO")))
                if config.get("include_in_main", True):
                    logger.addHandler(handler)
                self.loggers[component] = logger
    
    def log(self, message, component="system"):
        """Enhanced logging with component support"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        if self.logger:
            if component in self.loggers:
                self.loggers[component].info(message)
            else:
                self.logger.info(message)
    
    def log_transcription(self, message):
        """Log transcription-specific messages"""
        self.log(message, "transcription")
    
    def log_hardware(self, message):
        """Log hardware-specific messages"""
        self.log(message, "hardware")
    
    def log_command(self, message):
        """Log command execution messages"""
        self.log(message, "commands")
    
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
                self.log_hardware(f"LCD connected at {hw['lcd_i2c_address']}")
            except Exception as e:
                self.log_hardware(f"LCD setup failed: {e}")
                self.has_display = False
        else:
            self.has_display = False
            self.log_hardware("LCD libraries not available")
    
    def setup_speech(self):
        """Initialize speech recognition"""
        if not HAS_VOSK:
            self.has_speech = False
            self.log_hardware("Vosk not available")
            return
        
        voice_config = self.config["voice"]
        model_path = voice_config["model_path"]
        
        if not os.path.exists(model_path):
            self.has_speech = False
            self.log_hardware(f"Speech model not found at {model_path}")
            return
        
        try:
            self.log_hardware("Loading speech model... (30+ seconds)")
            self.model = vosk.Model(model_path)
            
            hw = self.config["hardware"]
            self.rec = vosk.KaldiRecognizer(self.model, hw["audio_sample_rate"])
            self.has_speech = True
            self.log_hardware("Speech recognition ready!")
        except Exception as e:
            self.log_hardware(f"Speech setup failed: {e}")
            self.has_speech = False
    
    def init_ring_buffer(self):
        """Initialize ring buffer state variables"""
        ring_config = self.config.get("voice", {}).get("ring_buffer", {})
        
        self.ring_buffer_enabled = ring_config.get("enabled", False)
        self.silence_threshold = ring_config.get("silence_threshold", 0.01)
        self.silence_duration = ring_config.get("silence_duration", 3.0)
        self.max_reset_interval = ring_config.get("max_reset_interval", 30.0)
        self.text_buffer_size = ring_config.get("text_buffer_size", 50)
        
        # State tracking
        self.silence_start_time = None
        self.last_reset_time = time.time()
        self.consecutive_silence_chunks = 0
        self.recent_transcriptions = []
        
        if self.ring_buffer_enabled:
            self.log("Ring buffer enabled - audio processing delays will be minimized")
        else:
            self.log("Ring buffer disabled - using standard processing")
    
    def calculate_audio_rms(self, audio_data):
        """Calculate RMS (Root Mean Square) of audio data to detect silence"""
        try:
            # Convert bytes to array of 16-bit integers
            audio_array = array.array('h', audio_data)
            
            # Calculate RMS
            sum_squares = sum(sample * sample for sample in audio_array)
            rms = (sum_squares / len(audio_array)) ** 0.5
            
            # Normalize to 0-1 range (assuming 16-bit audio)
            return rms / 32768.0
        except:
            return 0.0
    
    def should_reset_recognizer(self, audio_rms):
        """Determine if recognizer should be reset based on silence detection"""
        if not self.ring_buffer_enabled:
            return False
        
        current_time = time.time()
        is_silence = audio_rms < self.silence_threshold
        
        if is_silence:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
            
            silence_duration = current_time - self.silence_start_time
            if silence_duration >= self.silence_duration:
                return True
        else:
            # Reset silence tracking when sound is detected
            self.silence_start_time = None
        
        # Force reset if max interval exceeded
        time_since_reset = current_time - self.last_reset_time
        if time_since_reset >= self.max_reset_interval:
            return True
        
        return False
    
    def reset_speech_recognizer(self):
        """Reset the Vosk recognizer to clear audio buffer"""
        if self.has_speech:
            try:
                self.rec.Reset()
                self.last_reset_time = time.time()
                self.silence_start_time = None
                self.log_transcription("Speech recognizer reset - audio buffer cleared")
                return True
            except Exception as e:
                self.log_transcription(f"Failed to reset recognizer: {e}")
                return False
        return False
    
    def get_ring_buffer_stats(self):
        """Get ring buffer performance statistics"""
        if not self.ring_buffer_enabled:
            return {"status": "disabled"}
        
        current_time = time.time()
        time_since_reset = current_time - self.last_reset_time
        
        stats = {
            "status": "enabled",
            "time_since_last_reset": round(time_since_reset, 1),
            "recent_transcriptions_count": len(self.recent_transcriptions),
            "silence_threshold": self.silence_threshold,
            "silence_duration_target": self.silence_duration,
            "max_reset_interval": self.max_reset_interval,
            "is_currently_silent": self.silence_start_time is not None
        }
        
        if self.silence_start_time:
            stats["current_silence_duration"] = round(current_time - self.silence_start_time, 1)
        
        return stats
    
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
    
    def get_log_info(self):
        """Get information about current log files"""
        try:
            log_config = self.config.get("logging", {})
            if not log_config.get("enabled", False):
                return "Logging disabled"
            
            log_file = log_config.get("main_log", {}).get("file", "voice_lcd.log")
            if os.path.exists(log_file):
                size = os.path.getsize(log_file) / (1024 * 1024)  # MB
                return f"Log: {size:.1f}MB"
            return "No log file found"
        except Exception as e:
            return f"Error: {str(e)[:20]}"
    
    def clean_logs(self):
        """Force log rotation and cleanup"""
        try:
            if self.logger and hasattr(self.logger, 'handlers'):
                for handler in self.logger.handlers:
                    if hasattr(handler, 'doRollover'):
                        handler.doRollover()
                        return "Logs rotated"
            return "No rotation needed"
        except Exception as e:
            return f"Error: {str(e)[:20]}"
    
    def get_system_health(self):
        """Get system health information"""
        try:
            # Disk usage
            disk = shutil.disk_usage("/")
            used_percent = (disk.used / disk.total) * 100
            free_gb = disk.free / (1024**3)
            
            # Memory info (if available)
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1]) // 1024
                mem_free = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1]) // 1024
                mem_used = mem_total - mem_free
                mem_percent = (mem_used / mem_total) * 100
                
                return {
                    "disk_used_percent": used_percent,
                    "disk_free_gb": free_gb,
                    "memory_used_percent": mem_percent,
                    "memory_used_mb": mem_used
                }
            except:
                return {
                    "disk_used_percent": used_percent,
                    "disk_free_gb": free_gb
                }
        except Exception as e:
            return {"error": str(e)[:30]}
    
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
        
        elif action_type == "show_log_info":
            log_info = self.get_log_info()
            fmt = command_config.get("display_format", ["Log Status:", "{info}"])
            self.display_text(fmt[0], log_info)
            time.sleep(self.config["display"]["command_result_time"])
            # Also print detailed info to console
            if self.logger:
                print(f"Log file details: {log_info}")
        
        elif action_type == "clean_logs":
            fmt = command_config.get("display_format", ["Cleaning logs", "Please wait..."])
            self.display_text(fmt[0], fmt[1])
            result = self.clean_logs()
            time.sleep(1)
            self.display_text("Log Cleanup:", result)
            time.sleep(self.config["display"]["command_result_time"])
        
        elif action_type == "system_health":
            fmt = command_config.get("display_format", ["System Status:", "See details below"])
            self.display_text(fmt[0], "Checking...")
            health = self.get_system_health()
            
            if "error" in health:
                self.display_text("System Error:", health["error"])
            else:
                # Show disk usage on LCD
                disk_line = f"Disk: {health['disk_used_percent']:.0f}% used"
                free_line = f"Free: {health['disk_free_gb']:.1f}GB"
                self.display_text(disk_line, free_line)
                
                # Print detailed info to console
                print(f"=== System Health ===")
                print(f"Disk Usage: {health['disk_used_percent']:.1f}% used")
                print(f"Free Space: {health['disk_free_gb']:.2f} GB")
                if "memory_used_percent" in health:
                    print(f"Memory Usage: {health['memory_used_percent']:.1f}%")
                    print(f"Memory Used: {health['memory_used_mb']} MB")
                
                # Ring buffer stats
                ring_stats = self.get_ring_buffer_stats()
                print(f"\n=== Ring Buffer Status ===")
                if ring_stats["status"] == "enabled":
                    print(f"Status: Enabled - Preventing audio delays")
                    print(f"Time since last reset: {ring_stats['time_since_last_reset']}s")
                    print(f"Recent transcriptions: {ring_stats['recent_transcriptions_count']}")
                    if ring_stats["is_currently_silent"]:
                        print(f"Currently silent for: {ring_stats.get('current_silence_duration', 0)}s")
                else:
                    print(f"Status: Disabled - Using standard processing")
                
                # Check thresholds and warn
                log_config = self.config.get("logging", {})
                threshold = log_config.get("maintenance", {}).get("disk_space_warning_threshold_percent", 90)
                if health["disk_used_percent"] > threshold:
                    print(f"WARNING: Disk usage above {threshold}%!")
            
            time.sleep(self.config["display"]["command_result_time"])
        
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
        self.log_command(f"Processing: '{text}'")
        
        # Add to history
        if self.config["advanced"].get("enable_command_history", False):
            self.command_history.append((datetime.now(), text))
            max_history = self.config["advanced"].get("max_command_history", 50)
            if len(self.command_history) > max_history:
                self.command_history.pop(0)
        
        # Find matching command
        command_name, command_config = self.find_matching_command(text)
        
        if command_config:
            self.log_command(f"Executing command: {command_name}")
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
                
                # Ring buffer: Calculate audio level and check for reset
                if self.ring_buffer_enabled:
                    audio_rms = self.calculate_audio_rms(data)
                    if self.should_reset_recognizer(audio_rms):
                        self.reset_speech_recognizer()
                
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        # Ring buffer: Add to recent transcriptions buffer
                        if self.ring_buffer_enabled:
                            self.recent_transcriptions.append({
                                'text': text,
                                'timestamp': time.time()
                            })
                            # Trim buffer to max size
                            if len(self.recent_transcriptions) > self.text_buffer_size:
                                self.recent_transcriptions.pop(0)
                        
                        # Log transcription if enabled
                        if self.config.get("logging", {}).get("component_logs", {}).get("transcription", {}).get("enabled", True):
                            self.log_transcription(f"Transcribed: '{text}'")
                        
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