#!/usr/bin/env bash

set -eux

ansible-playbook playbooks/playbook.yml "$@"
