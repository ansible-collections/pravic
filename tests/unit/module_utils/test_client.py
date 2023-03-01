# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import json

from pathlib import Path
from unittest.mock import Mock, MagicMock
from unittest import mock

import pytest


from ansible_collections.pravic.pravic.plugins.module_utils.aws.client import (
    AwsClient,
    Discoverer,
    Resource,
    ResourceType,
)


def resources(filepath):
    current = Path(os.path.dirname(os.path.abspath(__file__)))
    with open(current / filepath) as fp:
        return json.load(fp)


RESOURCE = resources("fixtures/resource.json")
SCHEMA = resources("fixtures/schema.json")
RESPONSE_OP_UPDATE = resources("fixtures/response_op_update.json")
RESPONSE_OP_CREATE = resources("fixtures/response_op_create.json")
RESPONSE_OP_DELETE = resources("fixtures/response_op_delete.json")
RESPONSE_GET = resources("fixtures/response_get.json")


@pytest.fixture(scope="module")
def mock_resource_type():
    return ResourceType(SCHEMA)


def test_resource_type(mock_resource_type):
    assert isinstance(mock_resource_type, ResourceType)
    assert mock_resource_type.type_name == "AWS::IAM::Role"
    assert mock_resource_type.identifier == "RoleName"
    assert mock_resource_type.read_only_properties == ["Arn", "RoleId"]
    assert isinstance(mock_resource_type.make(RESOURCE), Resource)


def test_resource_type_empty_schema():
    resource_type = ResourceType({})
    assert isinstance(resource_type, ResourceType)


def test_resource(mock_resource_type):
    resource = Resource(resource=RESOURCE["Properties"], resource_type=mock_resource_type)
    assert isinstance(resource, Resource)
    assert resource.type_name == "AWS::IAM::Role"
    assert resource.identifier == "eda-test-role"
    assert resource.resource == RESOURCE
    assert resource.properties == RESOURCE["Properties"]
    assert resource.read_only_properties == ["Arn", "RoleId"]


@pytest.fixture(scope="module")
def aws_client():
    class NotFound(Exception):
        pass

    class AwsClientMock(AwsClient):
        def __init__(self):
            self.session = Mock()
            self.client = MagicMock()
            self.resources = Mock()
            self.check_mode = False

    resource = AwsClientMock()
    resource.client.exceptions.ResourceNotFoundException = NotFound
    return resource


@pytest.fixture(scope="module")
def discoverer():
    class NotFound(Exception):
        pass

    instance_discoverer = Discoverer(Mock())
    instance_discoverer.client = MagicMock()
    instance_discoverer.client.describe_type.return_value = {"Schema": json.dumps(SCHEMA)}
    instance_discoverer.client.exceptions.TypeNotFoundException = NotFound
    return instance_discoverer


def test_discoverer(discoverer, mock_resource_type):
    result = discoverer.get("AWS::IAM::Role")
    assert isinstance(result, ResourceType)
    assert result.type_name == mock_resource_type.type_name
    assert result.identifier == mock_resource_type.identifier
    assert result.read_only_properties == mock_resource_type.read_only_properties


def test_discoverer_invalid_type(discoverer):
    discoverer.client.describe_type.side_effect = discoverer.client.exceptions.TypeNotFoundException
    with pytest.raises(Exception) as e:
        discoverer.get("AWS::IMA::Role")

    assert "Invalid TypeName" in str(e.value)


def test_present_update_resource_no_diff(aws_client, mock_resource_type):
    aws_client.resources.get.return_value = mock_resource_type
    aws_client.client.get_resource.return_value = RESPONSE_GET
    result = aws_client.present(RESOURCE)
    aws_client.client.update_resource.assert_called_once()
    aws_client.client.create_resource.assert_not_called()
    assert result == RESPONSE_OP_UPDATE


@mock.patch.object(AwsClient, "_get_resource")
def test_present_create_resource(get_resource, aws_client, mock_resource_type):
    res_type = mock_resource_type.make(RESOURCE["Properties"])
    aws_client.resources.get.return_value = mock_resource_type

    get_resource.side_effect = [
        aws_client.client.exceptions.ResourceNotFoundException,
        res_type.resource_type.make(json.loads(RESPONSE_GET["ResourceDescription"]["Properties"])),
    ]

    result = aws_client.present(RESOURCE)
    aws_client.client.create_resource.assert_called_once_with(TypeName=res_type.type_name, DesiredState=json.dumps(res_type.properties))
    assert result == RESPONSE_OP_CREATE


def test_absent(aws_client, mock_resource_type):
    aws_client.resources.get.return_value = mock_resource_type
    aws_client.client.get_resource.return_value = RESPONSE_GET
    result = aws_client.absent(RESOURCE)
    aws_client.client.delete_resource.assert_called_once()
    assert result == RESPONSE_OP_DELETE


@mock.patch.object(AwsClient, "_get_resource")
def test_absent_not_found(get_resource, aws_client, mock_resource_type):
    aws_client.resources.get.return_value = mock_resource_type
    get_resource.side_effect = [aws_client.client.exceptions.ResourceNotFoundException]
    result = aws_client.absent(RESOURCE)
    assert result == {
        "Type": "AWS::IAM::Role",
        "Properties": {},
        "changed": False,
        "msg": "Skipped",
    }
