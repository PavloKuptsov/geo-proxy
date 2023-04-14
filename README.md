# geo-proxy

## Installation
```
cd /home/krakenrf
git clone https://github.com/PavloKuptsov/geo-proxy.git
chmod -R 770 geo-proxy/
cd geo-proxy
./install.sh
```

The server should start and be reachable on the 8082 port. The root, http://localhost:8082 should return
`{"message": "ping"}`
