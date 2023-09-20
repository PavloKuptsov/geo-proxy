#!/bin/bash

cd ~
sudo apt install apt-transport-https
curl -fsSL https://swupdate.openvpn.net/repos/openvpn-repo-pkg-key.pub | sudo gpg --dearmor > openvpn-repo-pkg-keyring.gpg
sudo cp openvpn-repo-pkg-keyring.gpg  /etc/apt/trusted.gpg.d/openvpn-repo-pkg-keyring.gpg
curl -fsSL https://swupdate.openvpn.net/community/openvpn3/repos/openvpn3-bullseye.list > openvpn3.list
sudo cp openvpn3.list  /etc/apt/sources.list.d/openvpn3.list
sudo apt update
sudo apt install openvpn3
read -n 1 -s -r -p "Press any key to open an editor an insert the contents of the OVPN config file..."
nano client.ovpn
read -n 1 -s -r -p "Press any key to continue setup..."
openvpn3 config-import --persistent --config client.ovpn --name client
openvpn3 config-acl --config client --grant root --transfer-owner-session true --show
sudo systemctl start openvpn3-session@client
sudo systemctl enable openvpn3-session@client
