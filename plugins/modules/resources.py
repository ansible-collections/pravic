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
  connection:
    description:
      - parameters used to create cloud client.
    type: dict
  client:
    description:
      - cloud client.
    choices:
      - azure
      - aws
    type: str
    required: true

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
          KeyName: test-pravic
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


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.pravic.pravic.plugins.module_utils.exception import CloudException, module_fail_from_exception
from ansible_collections.pravic.pravic.plugins.module_utils.aws.client import AwsClient
from ansible_collections.pravic.pravic.plugins.module_utils.azure.client import AzureClient


ARG_SPEC = {
    "resources": {"type": "dict", "required": True},
    "state": {"type": "str", "choices": ["present", "absent"], "default": "present"},
    "current_state": {"type": "dict"},
    "connection": {"type": "dict"},
    "client": {"type": "str", "choices": ["aws", "azure"], "required": True},
}

CLIENT_MAPPING = {
    "aws": AwsClient,
    "azure": AzureClient,
}


def main():
    module = AnsibleModule(argument_spec=ARG_SPEC, supports_check_mode=True)
    try:
        client_obj = CLIENT_MAPPING.get(module.params.get("client"))
        client = client_obj(check_mode=module.check_mode, **module.params.get("connection") or {})
        result = client.run(
            module.params.get("resources", []),
            module.params.get("current_state", {}),
            module.params["state"],
            module.check_mode,
        )
        module.exit_json(changed=result["changed"], resources=result)
    except CloudException as e:
        module_fail_from_exception(module, e)


if __name__ == "__main__":
    main()
