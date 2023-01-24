#!/usr/bin/env bash

set -eux

export ANSIBLE_CALLBACKS_ENABLED="cloud.pravic.state"
export ANSIBLE_COLLECTIONS_PATH=/Users/alinabuzachis/dev/collections

STATE_FILE="state.json"
trap 'rm -rvf "${STATE_FILE}"' EXIT

ansible-playbook main.yml -i localhost -e state_file=STATE_FILE "$@"
