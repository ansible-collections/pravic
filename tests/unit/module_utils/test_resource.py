# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, patch, call
import pytest
from typing import Dict

from ansible_collections.pravic.pravic.plugins.module_utils.resource import (
    get_value,
    replace_reference,
    REREG,
    resolve_refs,
    CloudClient,
    ResourceExceptionError,
)

PATCH_BASE_PATH = "ansible_collections.pravic.pravic.plugins.module_utils.resource."


@pytest.mark.parametrize(
    "data,path,expected",
    [
        ({"a": "value_a"}, ["a"], "value_a"),
        ({"parent_a": {"child_1": "value_a_1", "child_2": "value_a_2"}}, ["parent_a", "child_1"], "value_a_1"),
        ({"parent_a": {"child_1": "value_a_1", "child_2": "value_a_2"}}, ["parent_a", "child_1", "another_child"], None),
    ],
)
def test_get_value(data, path, expected):
    if expected:
        assert expected == get_value(data, path)
    else:
        with pytest.raises(TypeError):
            get_value(data, path)


@pytest.mark.parametrize("data", ["a.b.c", "a.b"])
@patch(PATCH_BASE_PATH + "get_value")
def test_replace_reference(m_get_value, data):
    match = REREG.match(f"resource:{data}")
    context = MagicMock()
    value = MagicMock()
    m_get_value.return_value = value
    assert replace_reference(context, match) == value
    assert m_get_value.called_once_with(call(context, data.split(".")))


@pytest.mark.parametrize(
    "node,expected",
    [
        ({"a": "resource:s1.a"}, {"a": "s1_value_a"}),
        ({"a": "resource:s1.a", "b": "resource:s2.b"}, {"a": "s1_value_a", "b": "s2_value_b"}),
        ({"c": ["resource:s1.a", "resource:s2.b"]}, {"c": ["s1_value_a", "s2_value_b"]}),
        ({"a": "resource:s1.c"}, None),
    ],
)
@patch(PATCH_BASE_PATH + "replace_reference")
def test_resolve_refs(m_replace_reference, node, expected):
    context = {
        "s1": {"a": "s1_value_a", "b": "s1_value_b"},
        "s2": {"a": "s2_value_a", "b": "s2_value_b"},
    }

    def replace_ref(ctxt, match):
        tmp = ctxt
        for k in match.group(1).split("."):
            tmp = tmp[k]
        return tmp

    m_replace_reference.side_effect = replace_ref
    check_mode = False

    if expected is None:
        with pytest.raises(KeyError):
            resolve_refs(node, context, check_mode=check_mode)
    else:
        result = resolve_refs(node=node, context=context, check_mode=check_mode)
        print(f"Result: {result} - Expected: {expected}")
        assert result == expected


@patch(PATCH_BASE_PATH + "replace_reference")
def test_resolve_refs_with_check_mode(m_replace_reference):
    context = {}

    m_replace_reference.side_effect = KeyError("missing key from dictionnary")
    check_mode = True

    node = {"a": "resource:s1.a"}
    result = resolve_refs(node=node, context=context, check_mode=check_mode)
    assert result == node


@pytest.fixture()
def cloudclient():
    class TestCloudClient(CloudClient):
        def present(self, resource: Dict) -> Dict:
            pass

        def absent(self, resource: Dict) -> Dict:
            pass

    client = TestCloudClient()
    client.has_pyyaml = MagicMock()
    client.has_pyyaml.return_value = True

    return client


@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize(
    "desired_state,expected",
    [
        ({"r1": {"name": "resource:r2.r1_name"}, "r2": {"r1_name": "value1", "name": "value2"}}, ["r2", "r1"]),
        ({"r1": {"name": "resource:r2.r1_name"}, "r2": {"r1_name": "value1", "name": "resource:r3.r2_name"}, "r3": {"r2_name": "value2"}}, ["r3", "r2", "r1"]),
    ],
)
def test_cloudclient_sort_resources(cloudclient, state, desired_state, expected):
    sorter = cloudclient.sort_resources(desired_state, state)
    result = []
    while sorter:
        for name in sorter.get_ready():
            result.append(name)
            sorter.done(name)
    if state == "absent":
        expected.reverse()
    assert expected == result


@pytest.mark.parametrize("state", ["present", "absent"])
def test_cloudclient_sort_resources_with_circle(cloudclient, state):
    desired_state = {"r1": {"name": "resource:r2.r1_name", "alias": "resource1"}, "r2": {"r1_name": "resource:r1.alias", "name": "value2"}}

    with pytest.raises(ResourceExceptionError):
        cloudclient.sort_resources(desired_state, state)


@pytest.mark.parametrize("state", ["present"])
def test_cloudclient_run_present(cloudclient, state):
    desired_state = {"child": {"ref": "resource:parent.id"}, "parent": {}}

    cloudclient.present = MagicMock()
    cloudclient.present.side_effect = [
        {"changed": True, "id": "id1"},
        {"changed": True, "id": "id2"},
    ]

    cloudclient.absent = MagicMock()
    cloudclient.absent.side_effect = [
        {"changed": True},
        {"changed": False},
    ]

    current_state = {}
    check_mode = False
    result = cloudclient.run(desired_state, current_state, state, check_mode)

    if state == "present":
        assert result == {
            "changed": True,
            "parent": {"changed": True, "id": "id1"},
            "child": {"changed": True, "id": "id2"},
        }
        cloudclient.present.assert_has_calls(
            [
                call({}),
                call({"ref": "id1"}),
            ]
        )
    elif state == "absent":
        assert result == {"changed": True, "child": {"changed": True}, "parent": {"changed": False}}
        cloudclient.present.assert_has_calls(
            [
                call({"ref": "resource:parent.id"}),
                call({}),
            ]
        )


def test_cloudclient_run_present_with_checkmode(cloudclient):
    desired_state = {"child": {"ref": "resource:parent.id"}, "parent": {}}

    cloudclient.present = MagicMock()
    cloudclient.present.side_effect = lambda src: {"changed": True, **src}

    current_state = {}
    state = "present"
    check_mode = True
    result = cloudclient.run(desired_state, current_state, state, check_mode)

    assert result == {
        "changed": True,
        "parent": {"changed": True},
        "child": {"changed": True, "ref": "resource:parent.id"},
    }

    cloudclient.present.assert_has_calls(
        [
            call({}),
            call({"ref": "resource:parent.id"}),
        ]
    )
