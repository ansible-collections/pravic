#!/usr/bin/env bash

set -eux

export ANSIBLE_CALLBACKS_ENABLED="cloud.pravic.state"

STATE_FILE="state.json"
trap 'rm -rvf "${STATE_FILE}"' EXIT

ansible-playbook main.yml -i localhost -e state_file=STATE_FILE "$@"
