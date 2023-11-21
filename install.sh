#!/bin/bash

install_dependencies()
{
  echo "Installing dependencies"
  apt update
  apt install python3-pip
  pip install --system -r requirements.txt
}

remove_old_service()
{
    echo "Checking for the old service"
    if [ "$(systemctl is-active gunicorn)" = "active" ]; then
      echo "Old service version found, removing"
      systemctl stop gunicorn
      systemctl disable gunicorn
      rm /etc/systemd/system/gunicorn.service
    fi
}

install_service()
{
    echo "Installing the service"
    if [ "$(systemctl is-active sunflower)" = "inactive" ]; then
      cp sunflower.service /etc/systemd/system/
      systemctl daemon-reload
      systemctl enable sunflower
      systemctl start sunflower
    fi
    if [ "$(systemctl is-active sunflower_ws_client)" = "inactive" ]; then
      cp sunflower_ws_client.service /etc/systemd/system/
      systemctl daemon-reload
      systemctl enable sunflower_ws_client
      systemctl start sunflower_ws_client
    fi
}

main()
{
  install_dependencies
  remove_old_service
  install_service
}

main "$@"