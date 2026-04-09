#!/usr/bin/with-contenv bashio
set -e

export CAMERA_IP="$(bashio::config 'camera_ip')"
export CAMERA_PORT="$(bashio::config 'camera_port')"
export CAMERA_USERNAME="$(bashio::config 'username')"
export CAMERA_PASSWORD="$(bashio::config 'password')"
export CAMERA_CHANNEL="$(bashio::config 'channel')"
export CAMERA_SPEED="$(bashio::config 'speed')"
export CAMERA_DURATION="$(bashio::config 'duration')"

export SDK_ROOT="/app/sdk"
export LD_LIBRARY_PATH="/app/sdk:/app/sdk/HCNetSDKCom:${LD_LIBRARY_PATH:-}"

echo "Starting EZVIZ PTZ service..."
python3 /app/ptz_service.py