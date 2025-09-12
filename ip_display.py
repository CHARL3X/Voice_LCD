#!/usr/bin/env python3
"""
IP Display - Shows Pi's IP address and animated special characters
"""

import time
import random
import socket
import subprocess
try:
    from RPLCD.i2c import CharLCD
    HAS_LCD = True
except ImportError:
    print("LCD libraries not found. Install with: pip install RPLCD")
    HAS_LCD = False

class IPDisplay:
    def __init__(self, i2c_addr=0x3f, cols=16, rows=2):
        self.cols = cols
        self.rows = rows
        
        if HAS_LCD:
            try:
                self.lcd = CharLCD('PCF8574', i2c_addr, cols=cols, rows=rows)
                self.lcd.clear()
                self.has_display = True
                print(f"Connected to LCD at 0x{i2c_addr:02x}")
            except Exception as e:
                print(f"Failed to connect to LCD: {e}")
                self.has_display = False
        else:
            self.has_display = False
            
        self.running = True
        self.scroll_pos = 0
        self.dot_positions = [random.randint(0, cols-1) for _ in range(3)]
        
        # Create custom characters
        if self.has_display:
            self.create_custom_chars()
    
    def create_custom_chars(self):
        """Create custom LCD characters"""
        # Custom char 0: Solid dot (degree symbol alternative)
        dot_char = (
            0b00000,
            0b01110,
            0b01110,
            0b01110,
            0b00000,
            0b00000,
            0b00000,
            0b00000,
        )
        
        # Custom char 1: Double vertical bar
        double_bar = (
            0b01010,
            0b01010,
            0b01010,
            0b01010,
            0b01010,
            0b01010,
            0b01010,
            0b01010,
        )
        
        self.lcd.create_char(0, dot_char)
        self.lcd.create_char(1, double_bar)
        
    def get_ip_address(self):
        """Get Pi's IP address"""
        try:
            # Try to get wlan0 first (WiFi)
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                # Get first IP address
                ip = result.stdout.strip().split()[0]
                return ip
        except:
            pass
            
        try:
            # Fallback method
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "No Network"
    
    def display_text(self, line1="", line2=""):
        """Display text on LCD"""
        if not self.has_display:
            print(f"LCD: '{line1}' / '{line2}'")
            return
            
        # Truncate to display width
        line1 = line1[:self.cols].ljust(self.cols)
        line2 = line2[:self.cols].ljust(self.cols)
        
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(line1)
        if self.rows > 1:
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2)
    
    def run(self):
        """Main display loop"""
        print("Starting IP Display...")
        print("Press Ctrl+C to stop")
        
        try:
            while self.running:
                # Get current IP
                ip = self.get_ip_address()
                
                # Create scrolling bars with floating dots
                bar_line = chr(1) * self.cols  # Fill with custom double bars
                
                # Create line with floating dots
                dot_line = [' '] * self.cols
                for pos in self.dot_positions:
                    dot_line[pos] = chr(0)  # Custom dot character
                
                # Move dots randomly
                for i in range(len(self.dot_positions)):
                    move = random.choice([-1, 0, 1])
                    self.dot_positions[i] = (self.dot_positions[i] + move) % self.cols
                
                # Display IP and animated line
                self.display_text(ip, ''.join(dot_line))
                
                time.sleep(0.5)  # Update every half second
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            if self.has_display:
                self.lcd.clear()

def main():
    display = IPDisplay(i2c_addr=0x3f, cols=16, rows=2)
    display.run()

if __name__ == "__main__":
    main()