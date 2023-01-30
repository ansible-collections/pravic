#!/usr/bin/env bash

set -eux

export ANSIBLE_CALLBACKS_ENABLED="pravic.pravic.state"

STATE_FILE="state.json"
trap 'rm -rvf "${STATE_FILE}"' EXIT

ansible-playbook playbooks/check_mode.yml  -i localhost -e state_file=STATE_FILE "$@"

ansible-playbook playbooks/resource_dependency.yml -i localhost -e state_file=STATE_FILE "$@"
