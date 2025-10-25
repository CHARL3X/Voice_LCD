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

try:
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    import smbus2
    HAS_OLED = True
except ImportError:
    HAS_OLED = False

class OLEDVoiceDisplay:
    """OLED display optimized for voice transcription on tiny 128x32 screen"""
    
    def __init__(self):
        self.device = None
        self.width = 128
        self.height = 32
        self.current_text = ""
        self.scroll_position = 0
        self.scroll_timer = 0
        self.status_message = "Voice: Ready"
        
    def initialize(self, i2c_port=1, oled_addresses=None):
        """Initialize OLED device for voice display"""
        if oled_addresses is None:
            oled_addresses = [0x3D, 0x3C]  # Default addresses

        try:
            # Try configured OLED addresses
            for addr in oled_addresses:
                try:
                    serial = i2c(port=i2c_port, address=addr)
                    self.device = ssd1306(serial, width=self.width, height=self.height)
                    self.clear()
                    self.show_status("Voice: Ready")
                    return True
                except Exception as e:
                    continue
            return False
        except Exception as e:
            return False
    
    def clear(self):
        """Clear the OLED display"""
        if self.device:
            self.device.clear()
    
    def show_status(self, status):
        """Show status message"""
        self.status_message = status
        if self.device:
            with canvas(self.device) as draw:
                # Status line at top
                draw.text((0, 0), self.status_message[:21], fill="white")
                # Divider line
                draw.line((0, 10, self.width-1, 10), fill="white")
    
    def show_transcription(self, text):
        """Show transcribed text with smart wrapping and scrolling"""
        if not self.device:
            return
            
        self.current_text = text
        wrapped_lines = self.wrap_text(text, 21)  # ~21 chars per line on 128px width
        
        with canvas(self.device) as draw:
            # Status line
            draw.text((0, 0), self.status_message[:21], fill="white")
            draw.line((0, 10, self.width-1, 10), fill="white")
            
            # Text area (lines 2-4, starting at y=12)
            y_start = 12
            line_height = 8
            max_visible_lines = 2  # Can fit ~2.5 lines, use 2 for readability
            
            if len(wrapped_lines) <= max_visible_lines:
                # Text fits without scrolling
                for i, line in enumerate(wrapped_lines):
                    if i < max_visible_lines:
                        draw.text((2, y_start + i * line_height), line, fill="white")
            else:
                # Need scrolling - show scrolling indicator
                draw.text((self.width-10, y_start), ">>", fill="white")
                
                # Show subset of lines based on scroll position
                start_line = self.scroll_position // 20  # Scroll every 20 frames (1 second at 20fps)
                for i in range(max_visible_lines):
                    line_idx = start_line + i
                    if line_idx < len(wrapped_lines):
                        draw.text((2, y_start + i * line_height), wrapped_lines[line_idx], fill="white")
                
                # Auto-scroll through lines
                self.scroll_timer += 1
                if self.scroll_timer >= 40:  # 2 seconds per line
                    self.scroll_position += 20
                    if self.scroll_position >= len(wrapped_lines) * 20:
                        self.scroll_position = 0
                    self.scroll_timer = 0
    
    def show_command_result(self, result_text):
        """Show command execution result"""
        self.show_status("Voice: Result")
        if not self.device:
            return
            
        wrapped_lines = self.wrap_text(result_text, 21)
        
        with canvas(self.device) as draw:
            # Status
            draw.text((0, 0), "Voice: Result", fill="white")
            draw.line((0, 10, self.width-1, 10), fill="white")
            
            # Result text
            y_start = 12
            line_height = 8
            
            for i, line in enumerate(wrapped_lines[:2]):  # Show first 2 lines
                draw.text((2, y_start + i * line_height), line, fill="white")
    
    def wrap_text(self, text, chars_per_line):
        """Wrap text to fit display width with word boundaries"""
        if not text:
            return []
            
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Check if adding word would exceed line length
            test_line = current_line + (" " if current_line else "") + word
            
            if len(test_line) <= chars_per_line:
                current_line = test_line
            else:
                # Start new line
                if current_line:
                    lines.append(current_line)
                current_line = word
                
                # Handle very long words
                while len(current_line) > chars_per_line:
                    lines.append(current_line[:chars_per_line])
                    current_line = current_line[chars_per_line:]
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def cleanup(self):
        """Cleanup OLED resources"""
        if self.device:
            self.clear()


class VoiceLCDv2:
    def __init__(self, config_path="voice_config.json"):
        self.config_path = config_path
        self.logger = None  # Initialize logger first
        self.loggers = {}   # Component loggers
        self.load_config()
        
        # Setup enhanced logging system
        self.setup_logging()

        # Validate configuration
        self.validate_config()

        # Display setup (LCD with OLED fallback)
        self.setup_display()
        
        # Speech setup
        self.setup_speech()
        
        # Command history
        self.command_history = []
        
        # Ring buffer initialization
        self.init_ring_buffer()

        self.log("Voice LCD v2 initialized")

    def resolve_path(self, path):
        """
        Resolve path relative to config file directory.
        Supports both relative and absolute paths.
        """
        if not path:
            return path

        # Already absolute path
        if os.path.isabs(path):
            return path

        # Resolve relative to config file directory
        config_dir = os.path.dirname(os.path.abspath(self.config_path))
        resolved = os.path.normpath(os.path.join(config_dir, path))
        return resolved

    def validate_config(self):
        """Validate configuration and warn about missing or invalid settings"""
        warnings = []

        # Check required sections
        required_sections = ["hardware", "display", "voice", "commands"]
        for section in required_sections:
            if section not in self.config:
                warnings.append(f"Missing required config section: '{section}'")

        # Check voice config
        if "voice" in self.config:
            voice = self.config["voice"]
            if "model_path" not in voice:
                warnings.append("Missing 'voice.model_path' - speech recognition will fail")
            elif voice["model_path"]:
                model_path = self.resolve_path(voice["model_path"])
                if not os.path.exists(model_path):
                    warnings.append(f"Speech model not found: {model_path}")

            if "wake_words" not in voice or not voice["wake_words"]:
                warnings.append("No wake words configured - voice commands won't trigger")

        # Check hardware config
        if "hardware" in self.config:
            hw = self.config["hardware"]
            required_hw = ["lcd_i2c_address", "lcd_cols", "lcd_rows"]
            for key in required_hw:
                if key not in hw:
                    warnings.append(f"Missing hardware config: '{key}'")

        # Check commands
        if "commands" in self.config:
            if not self.config["commands"]:
                warnings.append("No commands configured - nothing will respond to voice")

        # Log warnings
        if warnings:
            self.log("=== Configuration Warnings ===")
            for warning in warnings:
                self.log(f"  ⚠ {warning}")
            self.log("==============================")
        else:
            self.log("Configuration validated successfully")

        return len(warnings) == 0

    def setup_logging(self):
        """Setup enhanced logging system with rotation"""
        # Check for new logging config, fall back to legacy
        logging_config = self.config.get("logging")
        if not logging_config:
            # Legacy logging support
            legacy = self.config.get("advanced", {})
            if legacy.get("enable_logging", False):
                log_file = self.resolve_path(legacy.get("log_file", "voice_lcd.log"))
                logging.basicConfig(filename=log_file, level=logging.INFO,
                                  format='%(asctime)s - %(levelname)s - %(message)s')
                self.logger = logging.getLogger(__name__)
            return
        
        if not logging_config.get("enabled", False):
            return
        
        # Setup main rotating logger
        main_config = logging_config["main_log"]
        log_file = self.resolve_path(main_config["file"])
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
    
    def setup_display(self):
        """Initialize display - LCD with OLED fallback"""
        self.display_mode = None
        self.lcd = None
        self.oled_display = None
        self.oled_service_stopped = False
        
        # Try LCD first
        if self.setup_lcd():
            self.display_mode = "LCD"
            self.has_display = True
            self.log_hardware("Using LCD display mode")
        # Fallback to OLED
        elif self.setup_oled_fallback():
            self.display_mode = "OLED"
            self.has_display = True
            self.log_hardware("Using OLED fallback mode")
        else:
            self.display_mode = "NONE"
            self.has_display = False
            self.log_hardware("No display available - console only")
    
    def setup_lcd(self):
        """Try to initialize LCD display"""
        if not HAS_LCD:
            self.log_hardware("LCD libraries not available")
            return False

        hw = self.config["hardware"]
        max_retries = 3
        backpack_type = hw.get("i2c_backpack_type", "PCF8574")

        for attempt in range(max_retries):
            try:
                addr = int(hw["lcd_i2c_address"], 16)
                self.lcd = CharLCD(backpack_type, addr,
                                 cols=hw["lcd_cols"], rows=hw["lcd_rows"])
                self.lcd.clear()
                self.log_hardware(f"LCD connected at {hw['lcd_i2c_address']} using {backpack_type} (attempt {attempt + 1})")
                return True
            except Exception as e:
                self.log_hardware(f"LCD setup attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)

        self.log_hardware("LCD hardware not detected after all attempts")
        return False
    
    def setup_oled_fallback(self):
        """Initialize OLED fallback display"""
        if not HAS_OLED:
            self.log_hardware("OLED libraries not available")
            return False

        try:
            # Stop oled.service if running
            if self.stop_oled_service():
                self.oled_service_stopped = True
                time.sleep(2)  # Give service time to stop

            # Get hardware config
            hw = self.config.get("hardware", {})
            i2c_port = hw.get("i2c_port", 1)
            oled_addresses = hw.get("oled_addresses", [0x3D, 0x3C])

            # Initialize OLED voice display
            self.oled_display = OLEDVoiceDisplay()
            if self.oled_display.initialize(i2c_port=i2c_port, oled_addresses=oled_addresses):
                self.log_hardware(f"OLED voice display initialized on port {i2c_port}")
                return True
            else:
                self.log_hardware("OLED voice display initialization failed")
                # Restart oled.service if we stopped it
                if self.oled_service_stopped:
                    self.start_oled_service()
                    self.oled_service_stopped = False
                return False

        except Exception as e:
            self.log_hardware(f"OLED fallback setup failed: {e}")
            # Restart oled.service if we stopped it
            if self.oled_service_stopped:
                self.start_oled_service()
                self.oled_service_stopped = False
            return False
    
    def stop_oled_service(self):
        """Stop oled.service to free up OLED for voice display"""
        try:
            hw = self.config.get("hardware", {})
            service_name = hw.get("oled_service_name", "oled.service")

            result = subprocess.run(['sudo', 'systemctl', 'stop', service_name],
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_hardware(f"{service_name} stopped successfully")
                return True
            else:
                self.log_hardware(f"Failed to stop {service_name}: {result.stderr}")
                return False
        except Exception as e:
            self.log_hardware(f"Error stopping OLED service: {e}")
            return False

    def start_oled_service(self):
        """Restart oled.service"""
        try:
            hw = self.config.get("hardware", {})
            service_name = hw.get("oled_service_name", "oled.service")

            result = subprocess.run(['sudo', 'systemctl', 'start', service_name],
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_hardware(f"{service_name} restarted successfully")
                return True
            else:
                self.log_hardware(f"Failed to restart {service_name}: {result.stderr}")
                return False
        except Exception as e:
            self.log_hardware(f"Error restarting OLED service: {e}")
            return False
    
    def cleanup_display(self):
        """Cleanup display resources and restore services"""
        if self.oled_display:
            self.oled_display.cleanup()
        
        if self.oled_service_stopped:
            self.log_hardware("Restoring oled.service...")
            self.start_oled_service()
            self.oled_service_stopped = False
    
    def setup_speech(self):
        """Initialize speech recognition"""
        if not HAS_VOSK:
            self.has_speech = False
            self.log_hardware("Vosk not available")
            return

        voice_config = self.config["voice"]
        model_path = self.resolve_path(voice_config["model_path"])

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
        except (struct.error, ValueError, ZeroDivisionError) as e:
            self.log_transcription(f"Warning: Audio RMS calculation failed: {e}")
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
        """Display text on LCD or OLED"""
        if not self.has_display:
            print(f"Display: '{line1}' | '{line2}'")
            return
            
        if self.display_mode == "LCD":
            cols = self.config["hardware"]["lcd_cols"]
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(line1[:cols].ljust(cols))
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2[:cols].ljust(cols))
        elif self.display_mode == "OLED":
            # Format for OLED display
            combined_text = f"{line1} {line2}".strip()
            if combined_text:
                self.oled_display.show_command_result(combined_text)
            else:
                self.oled_display.show_status("Voice: Ready")
    
    def scroll_text(self, text, line=2, duration=None, cycles=None):
        """Scroll text on specified line"""
        if not text:
            return
            
        if self.display_mode == "OLED":
            # OLED uses built-in smart scrolling
            if line == 1:
                self.oled_display.show_command_result(text)
            else:
                self.oled_display.show_transcription(text)
            
            # Hold display for duration
            if duration:
                time.sleep(duration)
            else:
                time.sleep(self.config["display"].get("heard_text_cycles", 2) * 2)
            return
        
        # LCD scrolling behavior
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
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split()[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, IndexError) as e:
            self.log_command(f"Warning: Could not get IP address: {e}")
        except Exception as e:
            self.log_command(f"Unexpected error getting IP: {e}")
        return "No Network"
    
    def get_log_info(self):
        """Get information about current log files"""
        try:
            log_config = self.config.get("logging", {})
            if not log_config.get("enabled", False):
                return "Logging disabled"

            log_file = self.resolve_path(log_config.get("main_log", {}).get("file", "voice_lcd.log"))
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
            
            # Memory info (if available on Linux)
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
            except (FileNotFoundError, IndexError, ValueError) as e:
                self.log("Memory info not available (non-Linux system or permission issue)")
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
                timeout = command_config.get("timeout", None)  # Optional timeout in seconds
                show_errors = command_config.get("show_errors", True)

                self.log_command(f"Running command: {cmd[:50]}...")

                # Run command with optional timeout
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                # Check if command succeeded
                if result.returncode == 0:
                    output = result.stdout.strip()[:50]  # Limit output length
                    self.log_command(f"Command succeeded: {output[:30]}")
                else:
                    # Command failed - show stderr if enabled
                    if show_errors and result.stderr:
                        output = result.stderr.strip()[:50]
                        self.log_command(f"Command failed (exit {result.returncode}): {output[:30]}")
                    else:
                        output = result.stdout.strip()[:50] or f"Error (exit {result.returncode})"
                        self.log_command(f"Command failed with exit code {result.returncode}")

                # Format display output
                fmt = command_config.get("display_format", ["Output:", "{output}"])
                line1 = fmt[0] if len(fmt) > 0 else "Output:"
                line2 = fmt[1].replace("{output}", output) if len(fmt) > 1 else output

                # Display result
                if len(line2) <= self.config["hardware"]["lcd_cols"]:
                    self.display_text(line1, line2)
                    time.sleep(self.config["display"]["command_result_time"])
                else:
                    self.display_text(line1, "")
                    time.sleep(0.5)
                    self.scroll_text(line2, line=2, cycles=2)

            except subprocess.TimeoutExpired:
                error_msg = f"Timeout ({timeout}s)"
                self.log_command(f"Command timed out after {timeout} seconds")
                self.display_text("Command Error:", error_msg)
                time.sleep(3)
            except FileNotFoundError as e:
                error_msg = "Script not found"
                self.log_command(f"Command not found: {cmd}")
                self.display_text("Command Error:", error_msg)
                time.sleep(3)
            except Exception as e:
                error_msg = str(e)[:16]
                self.log_command(f"Command exception: {e}")
                self.display_text("Command Error:", error_msg)
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
        
        # Show processing status for OLED
        if self.display_mode == "OLED":
            self.oled_display.show_status("Voice: Processing")
        
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
            if self.display_mode == "OLED":
                self.oled_display.show_status(f"Voice: {command_name}")
                time.sleep(0.5)
            action = command_config["action"]
            self.execute_action(action, command_config, text)
        else:
            # No command found
            error_msgs = self.config["messages"].get("error_responses", 
                                                   ["Command not recognized"])
            error_msg = random.choice(error_msgs)
            if self.display_mode == "OLED":
                self.oled_display.show_status("Voice: Unknown")
                time.sleep(0.5)
            self.scroll_text(error_msg, line=1, duration=3)
        
        # Return to ready state for OLED
        if self.display_mode == "OLED":
            time.sleep(0.5)
            self.oled_display.show_status("Voice: Ready")
    
    def listen(self):
        """Main listening loop"""
        if not self.has_speech:
            self.log("Speech recognition not available - check model path")
            return
        
        # Display startup message
        startup = self.config["display"]["startup_message"]
        if self.display_mode == "OLED":
            # Special OLED startup
            self.oled_display.show_status("Voice: Starting")
            time.sleep(1)
            self.oled_display.show_status(f"Mode: OLED ({self.oled_display.width}x{self.oled_display.height})")
            time.sleep(1)
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
                            if self.display_mode == "OLED":
                                # OLED shows transcription with status
                                self.oled_display.show_status("Voice: Heard")
                                time.sleep(0.2)
                                self.oled_display.show_transcription(text)
                                time.sleep(self.config["display"]["short_text_display_time"])
                            else:
                                # LCD behavior
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
                if self.display_mode == "LCD":
                    self.lcd.clear()
                elif self.display_mode == "OLED":
                    self.oled_display.show_status("Voice: Shutdown")
                    time.sleep(1)
            self.cleanup_display()
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