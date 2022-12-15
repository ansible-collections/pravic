#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2022, Aubin Bikouo <@abikouo>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""

module: perf_resources_definition

short_description: Create set of resources with dependencies

author:
    - "Aubin Bikouo (@abikouo)"

description:
  - Create a set of resources to benchmark performance of the dependency resolution algorithm.

options:
  resources_type:
    description:
    - Type of resources to create
    - C(aws) will create Amazon AWS resources
    - C(kubernetes) will create Kubernetes resources
    type: str
    required: true
    choices:
    - aws
    - kubernetes
  number_resources:
    description:
    - Number of resources to create.
    type: int
    default: 10
  dependant_resources:
    description:
    - number max of resources on which each resource should depends on.
    - When not provided, this is will be randomly generated for each resource.
    type: int
"""

EXAMPLES = r"""
"""

RETURN = r"""
resources:
  description:
  - The generated object definition.
  returned: always
  type: complex
  sample:
    {
        "resource_0": {
            "kind": "Namespace",
            "apiVersion": "v1",
            "metadata": {"name": "ansible-kubernetes"},
        },
        "resource_1": {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": "test-map",
                "namespace": "resource:resource_0.metadata.name",
            }
        }
    }
"""

import random
from ansible.module_utils.basic import AnsibleModule


def argument_spec():
    return {
        "resources_type": {
            "type": "str", "choices": ["aws", "kubernetes"], "required": True,
        },
        "number_resources": {
            "type": "int", "default": 10,
        },
        "dependant_resources": {"type": "int"},
    }


def build_nodes(number, indegree_m=None):
    result = []
    for vertex in range(number):
        max_indegree = number - vertex - 1
        indegree = []
        if max_indegree > 0:
            items = range(vertex+1, number)
            selection = indegree_m or random.randint(1, number - vertex - 1)
            selection = len(items) if selection > len(items) else selection
            indegree = random.sample(items, k=selection)
        result.append((vertex, indegree))
    return result


def create_k8s_namespace(name):
    return {"kind": "Namespace", "apiVersion": "v1", "metadata": {"name": name}}


def create_k8s_configmap(name, namespace, dependencies):
    return {
        "kind": "ConfigMap",
        "apiVersion": "v1",
        "metadata": {
            "name": name,
            "namespace": f"resource:{namespace}.metadata.name"
        },
        "data": {i: f"resource:resource_{r}.metadata.name" for i, r in enumerate(dependencies)}
    }


def create_aws_ec2key(name, dependencies):
    return {
        "Type": "AWS::EC2::KeyPair",
        "Properties": {
            "KeyName": name,
            "KeyType": random.choice(("rsa", "ed25519")),
            "Tags": [
                {"Key": f"{i}", "Value": f"resource:resource_{r}.Properties.KeyName"} for i, r in enumerate(dependencies)
            ],
        }
    }


class ResourceDefinition(AnsibleModule):

    def __init__(self):

        super(ResourceDefinition, self).__init__(argument_spec=argument_spec())
        self.execute_module()

    def create_k8s_resources(self, nodes):

        result = {}
        namespace = None
        while nodes:
            node = nodes.pop(-1)
            if namespace is None:
                namespace = f"resource_{node[0]}"
                result[namespace] = create_k8s_namespace("ansible")
            else:
                name = f"configmap{node[0]}"
                result[f"resource_{node[0]}"] = create_k8s_configmap(name, namespace, node[1])

        return result

    def create_aws_resources(self, nodes):

        result = {}
        while nodes:
            node = nodes.pop(-1)
            name = f"ansible-pravic-{node[0]}"
            result[f"resource_{node[0]}"] = create_aws_ec2key(name, node[1])

        return result

    def execute_module(self):

        nodes = build_nodes(
            number=self.params.get("number_resources"),
            indegree_m=self.params.get("dependant_resources")
        )

        if self.params.get("resources_type") == "kubernetes":
            result = self.create_k8s_resources(nodes)
        if self.params.get("resources_type") == "aws":
            result = self.create_aws_resources(nodes)

        self.exit_json(resources=result)


def main():
    ResourceDefinition()


if __name__ == "__main__":
    main()
