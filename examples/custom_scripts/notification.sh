#!/bin/bash
# notification.sh - Send notifications via voice commands
# Usage: ./notification.sh "Your message"

MESSAGE="$1"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Validate message
if [ -z "$MESSAGE" ]; then
    echo "No message provided"
    exit 1
fi

# Log to file (create your own notification method here)
LOG_FILE="/tmp/voice_notifications.log"
echo "[$TIMESTAMP] $MESSAGE" >> "$LOG_FILE"

# Example: Send to ntfy (uncomment if you use ntfy.sh)
# curl -d "$MESSAGE" ntfy.sh/your_topic

# Example: Send via telegram (uncomment if configured)
# telegram-send "$MESSAGE"

# Output confirmation
echo "Notification sent"
exit 0
