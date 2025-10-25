#!/bin/bash
# govee_control.sh - Control Govee lights on local network via voice commands
# Usage: ./govee_control.sh <action> [value]
# Actions: on, off, brightness <1-100>, color <name>, scan

ACTION=$1
VALUE=$2

# Path to govee-ai repository
GOVEE_API_PATH="/home/morph/Desktop/govee-ai"
GOVEE_SCRIPT="$GOVEE_API_PATH/govee.py"

# Check if govee-ai exists
if [ ! -f "$GOVEE_SCRIPT" ]; then
    echo "ERROR: govee-ai not found"
    exit 1
fi

# Execute command based on action
case "$ACTION" in
    on)
        cd "$GOVEE_API_PATH" && python3 govee.py on 2>&1 | tail -1
        if [ $? -eq 0 ]; then
            echo "Light ON"
        else
            echo "Failed to turn on"
            exit 1
        fi
        ;;

    off)
        cd "$GOVEE_API_PATH" && python3 govee.py off 2>&1 | tail -1
        if [ $? -eq 0 ]; then
            echo "Light OFF"
        else
            echo "Failed to turn off"
            exit 1
        fi
        ;;

    brightness|bright)
        if [ -z "$VALUE" ]; then
            echo "Need brightness 1-100"
            exit 1
        fi
        cd "$GOVEE_API_PATH" && python3 govee.py brightness "$VALUE" 2>&1 | tail -1
        if [ $? -eq 0 ]; then
            echo "Brightness $VALUE%"
        else
            echo "Brightness failed"
            exit 1
        fi
        ;;

    color)
        if [ -z "$VALUE" ]; then
            echo "Need color name"
            exit 1
        fi

        # Convert color names to RGB values
        case "$VALUE" in
            red)      RGB="255 0 0" ;;
            green)    RGB="0 255 0" ;;
            blue)     RGB="0 0 255" ;;
            white)    RGB="255 255 255" ;;
            yellow)   RGB="255 255 0" ;;
            purple)   RGB="128 0 128" ;;
            cyan)     RGB="0 255 255" ;;
            magenta)  RGB="255 0 255" ;;
            orange)   RGB="255 165 0" ;;
            pink)     RGB="255 192 203" ;;
            *)
                echo "Unknown color: $VALUE"
                exit 1
                ;;
        esac

        cd "$GOVEE_API_PATH" && python3 govee.py rgb $RGB 2>&1 | tail -1
        if [ $? -eq 0 ]; then
            echo "Color: $VALUE"
        else
            echo "Color failed"
            exit 1
        fi
        ;;

    warm)
        # Set to warm white (3000K)
        cd "$GOVEE_API_PATH" && python3 govee.py temp 3000 2>&1 | tail -1
        if [ $? -eq 0 ]; then
            echo "Warm white"
        else
            echo "Temp failed"
            exit 1
        fi
        ;;

    cool)
        # Set to cool white (6500K)
        cd "$GOVEE_API_PATH" && python3 govee.py temp 6500 2>&1 | tail -1
        if [ $? -eq 0 ]; then
            echo "Cool white"
        else
            echo "Temp failed"
            exit 1
        fi
        ;;

    scan)
        cd "$GOVEE_API_PATH" && python3 govee.py scan 2>&1
        ;;

    status)
        cd "$GOVEE_API_PATH" && python3 govee.py status 2>&1
        ;;

    help|--help|-h)
        echo "Govee Light Control"
        echo "Usage: $0 <action> [value]"
        echo ""
        echo "Actions:"
        echo "  on              Turn light on"
        echo "  off             Turn light off"
        echo "  brightness N    Set brightness (1-100)"
        echo "  color NAME      Set color (red, blue, green, white, etc)"
        echo "  warm            Set warm white (3000K)"
        echo "  cool            Set cool white (6500K)"
        echo "  scan            Scan for Govee devices"
        echo "  status          Show device status"
        echo ""
        echo "Examples:"
        echo "  $0 on"
        echo "  $0 brightness 75"
        echo "  $0 color red"
        ;;

    *)
        echo "Usage: on|off|brightness|color|warm|cool|scan|status"
        echo "Run '$0 help' for details"
        exit 1
        ;;
esac

exit 0
