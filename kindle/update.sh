#!/bin/sh

PI_IP="192.168.1.x"
PORT="8080"
IMAGE_URL="http://${PI_IP}:${PORT}/calendar.png"
IMAGE_PATH="/tmp/calendar.png"

# Disable screensaver / sleep
lipc-set-prop com.lab126.powerd preventScreenSaver 1

while true; do
    wget -q "$IMAGE_URL" -O "${IMAGE_PATH}.tmp"
    if [ $? -eq 0 ]; then
        mv "${IMAGE_PATH}.tmp" "$IMAGE_PATH"
        eips -g "$IMAGE_PATH"
    else
        logger -t kindle-calendar "Failed to fetch image from $IMAGE_URL"
    fi
    sleep 1800
done
