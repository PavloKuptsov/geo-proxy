#!/bin/bash

install_dependencies()
{
  echo "[-    ] Installing dependencies"
  apt install python3-pip
  echo "[-    ] Creating virtualenv"
  python3 -m virtualenv venv
  echo "[+    ] Virtualenv created"
  echo "[+-   ] Installing python packages"
  venv/bin/pip install -r requirements.txt
  echo "[++   ] Packages installed"
}

remove_old_service()
{
  if [ "$(systemctl is-active gunicorn)" = "active" ];
  then
    systemctl stop gunicorn
    systemctl disable gunicorn
    rm /etc/systemd/system/gunicorn.service
  fi
}

install_service()
{
  echo "[+++- ] Installing the service"
  if [ "$(systemctl is-active sunflower)" = "inactive" ];
  then
    cp sunflower.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable sunflower
    systemctl start sunflower
    echo "[++++ ] Service installed successfully"
  else
    systemctl restart sunflower
    echo "[++++ ] Service updated successfully"
  fi
}

main()
{
  if install_dependencies; then
    echo "[+++  ] Dependencies installed successfully"
  else
    echo "[!!!  ] Error during dependency installation"
    exit 1
  fi
  remove_old_service
  install_service
  echo "[+++++] Installation complete"
}

main "$@"