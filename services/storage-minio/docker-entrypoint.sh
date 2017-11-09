#!/bin/sh

set -e

python3 -u /srv/minio/minio_controller.py &
# sleep 2
/minio server /data
