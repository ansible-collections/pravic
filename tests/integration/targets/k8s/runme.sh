#!/usr/bin/env bash

set -eux

export ANSIBLE_CALLBACKS_ENABLED="pravic.pravic.state"

STATE_FILE="state.json"
trap 'rm -rvf "${STATE_FILE}"' EXIT

ansible-playbook main.yml -i inventory -e state_file=STATE_FILE "$@"
