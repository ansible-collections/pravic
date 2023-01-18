# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import functools
import json
from typing import Any, Dict, List
import traceback

BOTO3_IMP_ERR = None
try:
    import boto3.session
    import botocore
    HAS_BOTO3 = True
except ImportError:
    BOTO3_IMP_ERR = traceback.format_exc()
    HAS_BOTO3 = False

from ansible.module_utils.basic import missing_required_lib
from ansible_collections.cloud.pravic.plugins.module_utils.resource import CloudClient


class JsonPatch(list):
    def __str__(self):
        return json.dumps(self)


def op(operation: str, path: str, value: str) -> Dict:
    path = "/{0}".format(path.lstrip("/"))
    return {"op": operation, "path": path, "value": value}


class Resource:
    def __init__(self, resource: Dict, resource_type: 'ResourceType') -> None:
        self.resource_type = resource_type
        self._resource = resource

    @property
    def type_name(self) -> str:
        return self.resource_type.type_name

    @property
    def identifier(self) -> str:
        return self._resource[self.resource_type.identifier]

    @property
    def resource(self) -> Dict:
        return {
            "Type": self.type_name,
            "Properties": self.properties,
        }

    @property
    def properties(self) -> Dict:
        return self._resource

    @property
    def read_only_properties(self) -> List[str]:
        return self.resource_type.read_only_properties


class ResourceType:
    def __init__(self, schema: Dict) -> None:
        self._schema = schema

    @property
    def type_name(self) -> str:
        return self._schema["typeName"]

    @property
    def identifier(self) -> str:
        return self._property_name(self._schema["primaryIdentifier"][0])

    @property
    def read_only_properties(self) -> List[str]:
        return [p.split("/")[-1] for p in self._schema["readOnlyProperties"]]

    def make(self, resource: Dict) -> Resource:
        return Resource(resource, self)

    def _property_name(self, path: str) -> str:
        return path.split("/")[-1]


class Discoverer:
    def __init__(self, session: Any) -> None:
        self.client = session.client("cloudformation")

    @functools.cache  # pylint: disable=method-cache-max-size-none
    def get(self, type_name: str) -> ResourceType:
        try:
            result = self.client.describe_type(Type="RESOURCE", TypeName=type_name)
        except self.client.exceptions.TypeNotFoundException as e:
            raise Exception(e, "Invalid TypeName")
        return ResourceType(json.loads(result["Schema"]))


class AwsBotocoreError(Exception):
    def __init__(self, exc, msg):
        self.exc = exc
        self.msg = msg
        super().__init__(self)


class AwsClient(CloudClient):
    def __init__(self, **kwargs: Any) -> None:

        if not HAS_BOTO3:
            raise AwsBotocoreError(
                msg=missing_required_lib('boto3 and botocore'),
                exc=BOTO3_IMP_ERR
            )

        self.session = boto3.session.Session(**kwargs)
        self.resources = Discoverer(self.session)
        self.client = self.session.client("cloudcontrol")

    def present(self, resource: Dict) -> Dict:
        r_type = self.resources.get(resource["Type"])
        desired = r_type.make(resource["Properties"])
        try:
            existing = self._get_resource(desired)
            result = self._update(existing, desired)
        except self.client.exceptions.ResourceNotFoundException:
            result = self._create(desired)
        return result.resource

    def absent(self, resource: Dict) -> Dict:
        r_type = self.resources.get(resource["Type"])
        desired = r_type.make(resource["Properties"])
        try:
            existing = self._get_resource(desired)
            result = self._delete(existing)
        except self.client.exceptions.ResourceNotFoundException:
            result = Resource({}, r_type)
        return result.resource

    def _get_resource(self, resource: Resource) -> Resource:
        result = self.client.get_resource(
            TypeName=resource.type_name, Identifier=resource.identifier
        )
        return resource.resource_type.make(
            json.loads(result["ResourceDescription"]["Properties"])
        )

    def _create(self, resource: Resource) -> Resource:
        result = self.client.create_resource(
            TypeName=resource.type_name, DesiredState=json.dumps(resource.properties)
        )
        try:
            self._wait(result["ProgressEvent"]["RequestToken"])
        except botocore.exceptions.WaiterError as e:
            raise Exception(e.last_response["ProgressEvent"]["StatusMessage"])
        return self._get_resource(resource)

    def _update(self, existing: Resource, desired: Resource) -> Resource:
        patch = JsonPatch()
        filtered = {k: v for k, v in desired.properties.items() if k not in desired.read_only_properties}
        for k, v in filtered.items():
            if k not in existing.properties:
                patch.append(op("add", k, v))
            elif v != existing.properties.get(k):
                patch.append(op("replace", k, v))
        if patch:
            result = self.client.update_resource(
                TypeName=existing.type_name,
                Identifier=existing.identifier,
                PatchDocument=str(patch),
            )
            self._wait(result["ProgressEvent"]["RequestToken"])
        return self._get_resource(desired)

    def _delete(self, resource: Resource) -> Resource:
        result = self.client.delete_resource(
            TypeName=resource.type_name, Identifier=resource.identifier
        )
        self._wait(result["ProgressEvent"]["RequestToken"])
        return resource

    def _wait(self, token: str) -> None:
        self.client.get_waiter("resource_request_success").wait(
            RequestToken=token,
            WaiterConfig={
                "Delay": 10,
                "MaxAttempts": 6,
            },
        )
