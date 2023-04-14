#!/bin/bash

sudo apt install python3-pip gunicorn
sudo pip install --system -r requirements.txt
sudo cp gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
