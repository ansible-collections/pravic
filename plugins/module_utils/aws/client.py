import functools
import json

import boto3.session
import botocore


class JsonPatch(list):
    def __str__(self):
        return json.dumps(self)


def op(operation, path, value):
    path = "/{0}".format(path.lstrip("/"))
    return {"op": operation, "path": path, "value": value}


class Resource:
    def __init__(self, resource, resource_type):
        self.resource_type = resource_type
        self._resource = resource

    @property
    def type_name(self):
        return self.resource_type.type_name

    @property
    def identifier(self):
        return self._resource.get(self.resource_type.identifier)

    @property
    def resource(self):
        return {
            "Type": self.type_name,
            "Properties": self.properties,
        }

    @property
    def properties(self):
        return self._resource

    @property
    def read_only_properties(self):
        return self.resource_type.read_only_properties


class ResourceType:
    def __init__(self, schema):
        self._schema = schema

    @property
    def type_name(self):
        return self._schema["typeName"]

    @property
    def identifier(self):
        return self._property_name(self._schema["primaryIdentifier"][0])

    @property
    def read_only_properties(self):
        return [p.split("/")[-1] for p in self._schema["readOnlyProperties"]]

    def make(self, resource):
        return Resource(resource, self)

    def _property_name(self, path):
        return path.split("/")[-1]


class Discoverer:
    def __init__(self, session):
        self.client = session.client("cloudformation")

    @functools.cache
    def get(self, type_name):
        result = self.client.describe_type(Type="RESOURCE", TypeName=type_name)
        return ResourceType(json.loads(result["Schema"]))


class AwsClient:
    def __init__(self, **kwargs):
        self.session = boto3.session.Session(**kwargs)
        self.resources = Discoverer(self.session)
        self.client = self.session.client("cloudcontrol")

    def present(self, resource):
        r_type = self.resources.get(resource["Type"])
        desired = r_type.make(resource["Properties"])
        try:
            existing = self._get_resource(desired)
            result = self._update(existing, desired)
        except self.client.exceptions.ResourceNotFoundException:
            result = self._create(desired)
        return result.resource

    def absent(self, resource):
        r_type = self.resources.get(resource["Type"])
        desired = r_type.make(resource["Properties"])
        try:
            existing = self._get_resource(desired)
            result = self._delete(existing)
        except self.client.exceptions.ResourceNotFoundException:
            result = Resource({}, r_type)
        return result.resource

    def _get_resource(self, resource):
        result = self.client.get_resource(
            TypeName=resource.type_name, Identifier=resource.identifier
        )
        return resource.resource_type.make(
            json.loads(result["ResourceDescription"]["Properties"])
        )

    def _create(self, resource):
        result = self.client.create_resource(
            TypeName=resource.type_name, DesiredState=json.dumps(resource.properties)
        )
        try:
            self._wait(result["ProgressEvent"]["RequestToken"])
        except botocore.exceptions.WaiterError as e:
            raise Exception(e.last_response["ProgressEvent"]["StatusMessage"])
        return self._get_resource(resource)

    def _update(self, existing, desired):
        patch = JsonPatch()
        filtered = {k: v for k,v in desired.properties.items() if k not in desired.read_only_properties}
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

    def _delete(self, resource):
        result = self.client.delete_resource(
            TypeName=resource.type_name, Identifier=resource.identifier
        )
        self._wait(result["ProgressEvent"]["RequestToken"])
        return resource

    def _wait(self, token):
        self.client.get_waiter("resource_request_success").wait(
            RequestToken=token,
            WaiterConfig={
                "Delay": 10,
                "MaxAttempts": 6,
            },
        )
