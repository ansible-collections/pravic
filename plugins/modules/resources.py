#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (C), 2022 Red Hat | Ansible
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
module: resources

short_description: create/delete/update cloud resource using yaml definition

description:
  - This module is used to create, update or delete cloud resources

author:
- Mike Graves (@gravesm)

options:
  resources:
    description:
      - Resources to create, delete or update.
    type: dict
    required: true
  state:
    description:
      - Use C(present) to create or update resources.
      - Use C(absent) to delete resources.
    type: str
    choices:
      - present
      - absent
    default: present
  current_state:
    description:
      - current resources state.
    type: dict

requirements:
  - "python >= 3.9"
"""

EXAMPLES = r"""
# create Amazon IAM Role
- name: Create Amazon IAM Role
  pravic.pravic.resources:
    state: present
    resources:
        role_1:
          Type: AWS::IAM::Role
          Properties:
            RoleName: sample-test-role
            Description: event-driven test role
            AssumeRolePolicyDocument:
            Version: 2012-10-17
            Statement:
            - Action:
              - sts:AssumeRole
              Effect: Allow
              Principal:
              Service: s3.amazonaws.com
# Delete Amazon EC2 key pair
- name: Delete Amazon EC2 key pair
  pravic.pravic.resources:
    state: absent
    resources:
      key_1:
        Type: AWS::EC2::KeyPair
        Properties:
          KeyName: aubin-pravic
          KeyType: rsa

"""

RETURN = r"""
resources:
  description: The resources created, updated or deleted.
  returned: success
  type: list
  elements: dict
  sample: []
"""

import os
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.pravic.pravic.plugins.module_utils.aws.client import AwsClient
from ansible_collections.pravic.pravic.plugins.module_utils.k8s.client import K8sClient


ARG_SPEC = {
    "resources": {"type": "dict", "required": True},
    "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
    "current_state": {"type": "dict"},
}


def get_client_config_args(code):
    start = code.upper() + "_CLIENT_"
    args = {}
    for key in os.environ:
        if key.startswith(start):
            args[key.replace(start, '', 1).lower()] = os.environ.get(key)
    return args


def main():
    module = AnsibleModule(argument_spec=ARG_SPEC, supports_check_mode=True)

    cloud_provider = os.environ.get('cloud_provider')
    if cloud_provider.lower() == "k8s":
        client = K8sClient(
            **get_client_config_args(cloud_provider.lower())
        )
    if cloud_provider.lower() == "aws":
        client = AwsClient(
            **get_client_config_args(cloud_provider.lower())
        )

    result = client.run(
        module.params.get("resources", []),
        module.params.get("current_state", {}),
        module.params["state"],
    )
    module.exit_json(changed=result["changed"], resources=result)


if __name__ == "__main__":
    main()
