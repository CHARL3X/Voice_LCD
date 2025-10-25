#!/bin/bash
# gpio_control.sh - Control GPIO pins via voice commands
# Usage: ./gpio_control.sh <on|off> <pin_number>

ACTION=$1
PIN=$2

# Validate arguments
if [ -z "$ACTION" ] || [ -z "$PIN" ]; then
    echo "Usage: on/off PIN"
    exit 1
fi

# Check if gpio command exists
if ! command -v gpio &> /dev/null; then
    echo "gpio not installed"
    exit 1
fi

# Perform action
case "$ACTION" in
    on|ON)
        gpio -g write "$PIN" 1
        echo "GPIO $PIN: ON"
        exit 0
        ;;
    off|OFF)
        gpio -g write "$PIN" 0
        echo "GPIO $PIN: OFF"
        exit 0
        ;;
    *)
        echo "Unknown: $ACTION"
        exit 1
        ;;
esac
