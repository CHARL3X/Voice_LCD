#!/usr/bin/env python3
"""
Digital Zen Garden - Aesthetically pleasing LCD display
Creates calming, ambient visual patterns on a rectangular LCD
"""

import time
import random
import signal
import sys
from datetime import datetime
from typing import List, Tuple
try:
    from RPLCD.i2c import CharLCD
    HAS_LCD = True
except ImportError:
    print("LCD libraries not found. Install with: pip install RPLCD")
    HAS_LCD = False

class ZenGarden:
    def __init__(self, i2c_addr=0x3f, cols=16, rows=2):
        self.cols = cols
        self.rows = rows
        self.i2c_addr = i2c_addr
        
        if HAS_LCD:
            try:
                self.lcd = CharLCD('PCF8574', i2c_addr, cols=cols, rows=rows)
                self.lcd.clear()
                self.has_display = True
                print(f"Connected to LCD at 0x{i2c_addr:02x} ({cols}x{rows})")
            except Exception as e:
                print(f"Failed to connect to LCD: {e}")
                self.has_display = False
        else:
            self.has_display = False
            
        self.scenes = [
            self.progress_bars,
            self.spectrum_analyzer,
            self.clock_scene,
            self.smooth_scroll,
            self.bouncing_dot,
            self.level_meter
        ]
        self.current_scene = 0
        self.scene_duration = 15  # seconds per scene
        self.running = True
        
        # Set up signal handlers for clean exit
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Zen quotes for ambient display
        self.zen_quotes = [
            "Be present",
            "Breathe deeply", 
            "Find stillness",
            "Let go gently",
            "Peace within",
            "Moment by moment",
            "Simple beauty",
            "Quiet mind",
            "Flow like water",
            "Inner calm"
        ]
        
    def display_text(self, line1: str = "", line2: str = ""):
        """Display text on LCD, centering if shorter than display width"""
        if not self.has_display:
            print(f"LCD: '{line1}' / '{line2}'")
            return
            
        # Center and pad lines
        line1 = line1[:self.cols].center(self.cols)
        line2 = line2[:self.cols].center(self.cols) if self.rows > 1 else ""
        
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(line1)
        if self.rows > 1:
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2)
    
    def clear(self):
        if self.has_display:
            self.lcd.clear()
        else:
            print("LCD: [CLEAR]")
    
    def progress_bars(self):
        """Clean animated progress bars"""
        for cycle in range(3):
            # Fill bar
            for i in range(self.cols + 1):
                bar1 = '#' * i + '-' * (self.cols - i)
                bar2 = '-' * (self.cols - i) + '#' * i
                self.display_text(bar1, bar2)
                time.sleep(0.15)
            time.sleep(0.5)
    
    def spectrum_analyzer(self):
        """Fake spectrum analyzer with blocks"""
        heights = [0] * 8  # 8 frequency bands for 16 chars
        
        for frame in range(20):
            # Random frequency data
            for i in range(8):
                heights[i] = max(0, heights[i] + random.randint(-1, 2))
                if heights[i] > 2: heights[i] = 2
            
            # Build display
            line1 = ''
            line2 = ''
            for h in heights:
                if h >= 2:
                    line1 += '##'
                    line2 += '##'
                elif h >= 1:
                    line1 += '  '
                    line2 += '##'
                else:
                    line1 += '  '
                    line2 += '  '
            
            self.display_text(line1, line2)
            time.sleep(0.2)
    
    def clock_scene(self):
        """Display current time with decorative elements"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%m/%d")
        
        # Add decorative borders
        decoration = ">" + "=" * (len(time_str)) + "<"
        
        for _ in range(5):  # Show for 5 seconds
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            self.display_text(decoration, time_str)
            time.sleep(1)
    
    def smooth_scroll(self):
        """Smooth scrolling text"""
        message = "DIGITAL DISPLAY VIBES"
        padded = " " * self.cols + message + " " * self.cols
        
        for i in range(len(padded) - self.cols + 1):
            line1 = padded[i:i + self.cols]
            line2 = "=" * (i % self.cols) + "-" * (self.cols - (i % self.cols))
            self.display_text(line1, line2)
            time.sleep(0.25)
    
    def bouncing_dot(self):
        """Bouncing dot animation"""
        positions = list(range(self.cols)) + list(range(self.cols - 2, 0, -1))
        
        for cycle in range(2):
            for pos in positions:
                line1 = " " * pos + "*" + " " * (self.cols - pos - 1)
                line2 = "-" * self.cols
                self.display_text(line1, line2)
                time.sleep(0.15)
    
    def level_meter(self):
        """VU meter style display"""
        for frame in range(15):
            # Random levels for left/right channels
            left_level = random.randint(0, self.cols)
            right_level = random.randint(0, self.cols)
            
            # Build meter bars
            left_bar = "#" * left_level + "." * (self.cols - left_level)
            right_bar = "#" * right_level + "." * (self.cols - right_level)
            
            self.display_text(left_bar, right_bar)
            time.sleep(0.3)
    
    def run(self):
        """Main loop - cycles through scenes"""
        print("Starting Digital Zen Garden...")
        print("Press Ctrl+C to stop")
        
        if not self.has_display:
            print("No LCD detected - running in demo mode")
        
        try:
            while self.running:
                scene_func = self.scenes[self.current_scene]
                print(f"Playing scene: {scene_func.__name__}")
                
                scene_func()
                
                # Transition pause
                self.clear()
                time.sleep(1)
                
                # Move to next scene
                self.current_scene = (self.current_scene + 1) % len(self.scenes)
                
        except KeyboardInterrupt:
            print("\nShutting down peacefully...")
            self.clear()
        except Exception as e:
            print(f"Error: {e}")
            self.clear()
    
    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False
        self.clear()
        sys.exit(0)

def main():
    # Auto-detect display size (default to 16x2)
    garden = ZenGarden(i2c_addr=0x3f, cols=16, rows=2)
    garden.run()

if __name__ == "__main__":
    main()