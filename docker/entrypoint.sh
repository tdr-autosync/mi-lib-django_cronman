#!/bin/bash

set -e

# Configure environment

source /etc/profile.d/venv.sh

exec $@
