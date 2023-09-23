# geo-proxy

## Installation
```
cd /home/krakenrf
git clone https://github.com/PavloKuptsov/geo-proxy.git
chmod -R 770 geo-proxy/
cd geo-proxy
sudo ./install.sh
```

The server should start and be reachable on the 8082 port. The root, http://localhost:8082 should return
`{"message": "ping"}`

## Use in docker and docker compose

1. Install [Docker](https://docs.docker.com/engine/install/)
1. Install [Docker Compose V2 Plugin](https://docs.docker.com/compose/cli-command/#installing-compose-v2)

**Note:** Please note that you need install docker compose plugin v2, not docker compose V1 python library.

### Prepare host

You need prepare host to run DOA not in privileged mode. For this make such changes:

 - Skip load kernel module:

```
echo 'blacklist dvb_usb_rtl28xxu' > /etc/modprobe.d/blacklist-dvb_usb_rtl28xxu.conf
```

 - Setup required sysctl:

```
echo 'kernel.sched_rt_runtime_us=-1' > /etc/sysctl.d/doa.conf
```

 - Install and setup required sysfs:

```
apt install sysfsutils
echo 'module/usbcore/parameters/usbfs_memory_mb=0' > /etc/sysfs.d/doa.conf
```

> **NOTE:** This changes require reboot the host.

### Run instances

Copy file `compose.yaml` to some folder. Then you can run from this folder:

```
docker compose up -d geo-proxy doa
```
