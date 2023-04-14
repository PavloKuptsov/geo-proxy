#!/bin/bash

# Copy the service file to the systemd directory
sudo cp gunicorn.service /etc/systemd/system/

# Reload the systemd daemon to pick up the new service file
sudo systemctl daemon-reload

# Start the Gunicorn service
sudo systemctl start gunicorn

# Enable the service to start on system boot
sudo systemctl enable gunicorn
