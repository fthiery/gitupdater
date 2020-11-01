# gitupdaterd

Daemon which updates git folders periodically

## Configuration

Create ~/.config/gitupdater and/or drop config files into ~/.config/gitupdater.d (see the example config.cfg.example file).

## Installation

```
mkdir -p ~/.config/systemd/user
cp systemd/* ~/.config/systemd/user
systemctl --user daemon-reload
sudo ln -sf `pwd`/gitupdater.py /usr/local/bin
systemctl --user enable gitupdater.timer
systemctl --user start gitupdater.timer
```

## Requirements

* python3
* git
* libnotify
* python-gobject
