#!/bin/bash

set -e

# Configure environment

source /etc/profile.d/venv.sh
source /etc/profile.d/psql.sh

exec $@
