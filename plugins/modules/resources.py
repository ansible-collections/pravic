#!/usr/bin/python


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cloud.pravic.plugins.module_utils.client import AwsClient
from ansible_collections.cloud.pravic.plugins.module_utils.resource import run


ARG_SPEC = {
    "resources": {"type": "dict"},
    "state": {"type": "str"},
    "current_state": {"type": "dict"},
    "connection": {"type": "dict"},
}


def main():
    module = AnsibleModule(argument_spec=ARG_SPEC)
    client = AwsClient(**module.params.get("connection") or {})
    result = run(
        module.params.get("resources", []),
        module.params.get("current_state", {}),
        client,
        module.params["state"],
    )
    module.exit_json(changed=True, resources=result)


if __name__ == "__main__":
    main()
