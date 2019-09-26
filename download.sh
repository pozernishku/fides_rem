#!/usr/bin/env bash

# dont forget to check x permissions

# CentOS
sudo head -n 5005 ../wet.path.app.10k | tail -n +5001 | xargs -n 1 -P 16 sudo wget -q

# run: sudo nohup ./download.sh &


# MacOS - removed sudo from everywhere
# head -n 5005 ../wet.path.app.10k | tail -n +5001 | xargs -n 1 -P 4 wget -q

# run: nohup ./download.sh &