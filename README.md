# Digital Zen Garden 🌸

An aesthetically pleasing ambient display for rectangular LCD screens. Creates calming, slowly-evolving visual patterns perfect for meditation or ambient decoration.

## Features

- **6 Different Scenes:**
  - 🌊 Animated waves
  - 🌧️ Falling rain effect  
  - 🕒 Decorative clock display
  - 🧘 Zen quotes with fade transitions
  - 💻 Matrix-style character rain
  - 🫁 Breathing meditation guide

- **Auto-cycling** between scenes every 15 seconds
- **Gentle transitions** for a calming experience
- **I2C LCD compatible** (tested with PCF8574 backpack)

## Hardware Requirements

- Raspberry Pi (any model with I2C)
- I2C LCD display (16x2 or 20x4)
- Proper I2C connections (SDA, SCL, VCC, GND)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Enable I2C** on your Pi:
   ```bash
   sudo raspi-config
   # Navigate to Interface Options > I2C > Enable
   ```

3. **Run the garden:**
   ```bash
   python3 zen_garden.py
   ```

## Detected Hardware

- LCD found at I2C address: `0x3f`
- Display type: 16x2 characters

Press `Ctrl+C` to stop the display peacefully.

---
*Find peace in the digital zen garden* ✨