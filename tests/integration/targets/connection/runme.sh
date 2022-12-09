#!/usr/bin/env bash

set -eux

ansible-playbook playbooks/deploy.yml -i inventory/hosts.yml "$@"
