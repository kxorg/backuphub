#!/bin/bash

cd /home/dv/backuphub/app
pytest --nomigrations -v "$@"