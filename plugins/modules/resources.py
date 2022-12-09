#!/usr/bin/python

import os
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.gravesm.eda.plugins.module_utils.aws.client import AwsClient
from ansible_collections.gravesm.eda.plugins.module_utils.k8s.client import K8sClient
from ansible_collections.gravesm.eda.plugins.module_utils.resource import run


ARG_SPEC = {
    "resources": {"type": "dict"},
    "state": {"type": "str"},
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
    module = AnsibleModule(argument_spec=ARG_SPEC)

    cloud_provider = os.environ.get('cloud_provider')
    if cloud_provider.lower() == "k8s":
        client = K8sClient(**get_client_config_args(cloud_provider.lower()))
    if cloud_provider.lower() == "aws":
        client = AwsClient(**get_client_config_args(cloud_provider.lower()))

    result = run(
        module.params.get("resources", []),
        module.params.get("current_state", {}),
        client,
        module.params["state"],
    )
    module.exit_json(changed=True, resources=result)


if __name__ == "__main__":
    main()
