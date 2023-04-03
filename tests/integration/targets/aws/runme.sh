#!/usr/bin/env bash

set -eux

export ANSIBLE_CALLBACKS_ENABLED="pravic.pravic.state"

STATE_FILE_1="state_1.json"
STATE_FILE_2="state_2.json"
trap 'rm -rvf "${STATE_FILE_1}" "${STATE_FILE_2}"' EXIT

ansible-playbook playbooks/check_mode.yml  -i localhost -e state_file=STATE_FILE_1 "$@"

ansible-playbook playbooks/resource_dependency.yml -i localhost -e state_file=STATE_FILE_2 "$@"
