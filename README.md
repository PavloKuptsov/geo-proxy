# geo-proxy

## Installation
Copy server.py, requirements.txt and gui_run.sh to `~/krakensdr_doa/krakensdr_doa`
```
sudo apt install pip gunicorn
pip3 install --system -r requirements.txt
sudo iptables -A INPUT -p tcp --dport 8082 -j ACCEPT
sudo reboot
```

After the reboot, server should start and be reachable on the 8082 port. It writes logs to 
`~/krakensdr_doa/krakensdr_doa/gunicorn.log`.

In case there are problems, the server can be started manually by running
```
gunicorn -b 0.0.0.0:8082 'server:create_app()'
```
