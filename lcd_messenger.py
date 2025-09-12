#!/usr/bin/env python3
"""
LCD Messenger - CLI tool for displaying scrolling messages on LCD
"""

import time
import sys
import argparse
import signal
from typing import Optional

try:
    from RPLCD.i2c import CharLCD
    HAS_LCD = True
except ImportError:
    print("LCD libraries not found. Install with: pip install RPLCD")
    HAS_LCD = False

class LCDMessenger:
    def __init__(self, i2c_addr=0x3f, cols=16, rows=2):
        self.cols = cols
        self.rows = rows
        self.running = True
        
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
        
        # Set up signal handlers for clean exit
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def display_text(self, line1="", line2=""):
        """Display text on LCD"""
        if not self.has_display:
            print(f"LCD: '{line1}' | '{line2}'")
            return
            
        # Truncate to display width
        line1 = line1[:self.cols].ljust(self.cols)
        line2 = line2[:self.cols].ljust(self.cols)
        
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(line1)
        if self.rows > 1:
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2)
    
    def scroll_message(self, message, speed=0.3, line=1):
        """Scroll a message horizontally across the specified line"""
        if not message:
            return
        
        # Pad message with spaces for smooth scrolling
        padded_message = " " * self.cols + message + " " * self.cols
        
        print(f"Scrolling message on line {line}: '{message}'")
        print("Press Ctrl+C to stop")
        
        try:
            while self.running:
                for i in range(len(padded_message) - self.cols + 1):
                    if not self.running:
                        break
                        
                    display_text = padded_message[i:i + self.cols]
                    
                    if line == 1:
                        self.display_text(display_text, "")
                    else:
                        self.display_text("", display_text)
                    
                    time.sleep(speed)
                
                # Brief pause before repeating
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.cleanup()
    
    def scroll_two_lines(self, line1_msg, line2_msg, speed=0.3):
        """Scroll messages on both lines simultaneously"""
        if not line1_msg and not line2_msg:
            return
        
        # Pad both messages
        padded_line1 = " " * self.cols + (line1_msg or "") + " " * self.cols
        padded_line2 = " " * self.cols + (line2_msg or "") + " " * self.cols
        
        # Make them the same length for synchronized scrolling
        max_len = max(len(padded_line1), len(padded_line2))
        padded_line1 = padded_line1.ljust(max_len)
        padded_line2 = padded_line2.ljust(max_len)
        
        print(f"Scrolling two-line message:")
        print(f"  Line 1: '{line1_msg}'")
        print(f"  Line 2: '{line2_msg}'")
        print("Press Ctrl+C to stop")
        
        try:
            while self.running:
                for i in range(max_len - self.cols + 1):
                    if not self.running:
                        break
                        
                    display_line1 = padded_line1[i:i + self.cols]
                    display_line2 = padded_line2[i:i + self.cols]
                    
                    self.display_text(display_line1, display_line2)
                    time.sleep(speed)
                
                # Brief pause before repeating
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.cleanup()
    
    def static_display(self, line1="", line2=""):
        """Display static text until interrupted"""
        print(f"Displaying static text:")
        if line1:
            print(f"  Line 1: '{line1}'")
        if line2:
            print(f"  Line 2: '{line2}'")
        print("Press Ctrl+C to stop")
        
        try:
            self.display_text(line1, line2)
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()
    
    def interactive_mode(self):
        """Interactive mode for typing messages"""
        print("Interactive LCD Messenger")
        print("Commands:")
        print("  Type a message to scroll it on line 1")
        print("  Use 'line1|line2' format for two-line messages")
        print("  'static message' for non-scrolling display")
        print("  'clear' to clear the display")
        print("  'quit' or Ctrl+C to exit")
        print()
        
        try:
            while self.running:
                user_input = input("Message: ").strip()
                
                if not user_input or user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'clear':
                    if self.has_display:
                        self.lcd.clear()
                    else:
                        print("LCD: [CLEARED]")
                    continue
                elif user_input.lower().startswith('static '):
                    static_msg = user_input[7:]  # Remove 'static ' prefix
                    if '|' in static_msg:
                        line1, line2 = static_msg.split('|', 1)
                        self.display_text(line1.strip(), line2.strip())
                    else:
                        self.display_text(static_msg, "")
                    print("Static message displayed. Type another command...")
                elif '|' in user_input:
                    # Two-line message
                    line1, line2 = user_input.split('|', 1)
                    self.scroll_two_lines(line1.strip(), line2.strip(), speed=0.3)
                else:
                    # Single line scroll
                    self.scroll_message(user_input, speed=0.3, line=1)
                    
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up and clear display"""
        self.running = False
        if self.has_display:
            self.lcd.clear()
        print("\nDisplay cleared. Goodbye!")
    
    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        self.cleanup()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='LCD Messenger - Display scrolling messages on LCD')
    parser.add_argument('-m', '--message', help='Message to display')
    parser.add_argument('-2', '--line2', help='Second line message')
    parser.add_argument('-s', '--static', action='store_true', help='Display static (non-scrolling) text')
    parser.add_argument('--speed', type=float, default=0.3, help='Scroll speed in seconds (default: 0.3)')
    parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--addr', type=lambda x: int(x, 16), default=0x3f, help='I2C address (hex, default: 0x3f)')
    
    args = parser.parse_args()
    
    # Create messenger instance
    messenger = LCDMessenger(i2c_addr=args.addr)
    
    try:
        if args.interactive:
            # Interactive mode
            messenger.interactive_mode()
        elif args.message:
            # Command line message
            if args.static:
                # Static display
                messenger.static_display(args.message, args.line2 or "")
            elif args.line2:
                # Two-line scrolling
                messenger.scroll_two_lines(args.message, args.line2, args.speed)
            else:
                # Single line scrolling
                messenger.scroll_message(args.message, args.speed, line=1)
        else:
            # No message provided, enter interactive mode
            messenger.interactive_mode()
            
    except Exception as e:
        print(f"Error: {e}")
        messenger.cleanup()

if __name__ == "__main__":
    main()