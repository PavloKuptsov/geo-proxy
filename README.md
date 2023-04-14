# geo-proxy

## Installation
Copy geo-proxy directory to `/home/krakenrf`
```
sudo apt install python3-pip gunicorn
sudo pip install --system -r requirements.txt
sudo iptables -A INPUT -p tcp --dport 8082 -j ACCEPT
gunicorn -b 0.0.0.0:8082 'server:create_app()'
```

<!---After the reboot, server should start and be reachable on the 8082 port. It writes logs to 
`~/krakensdr_doa/krakensdr_doa/gunicorn.log`.

In case there are problems, the server can be started manually by running
```
gunicorn -b 0.0.0.0:8082 'server:create_app()'
```--->
