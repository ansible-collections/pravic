import concurrent.futures
import functools
import operator
import re
from graphlib import TopologicalSorter
import traceback
from abc import ABCMeta, abstractmethod
from typing import Dict, Any

PYYAML_IMP_ERR = None
try:
    import yaml

    HAS_PYYAML = True
except ImportError:
    PYYAML_IMP_ERR = traceback.format_exc()
    HAS_PYYAML = False

from ansible.module_utils.basic import missing_required_lib


REREG = re.compile(r"resource:((\w+)\S+)")


def get_value(data, path):
    while path:
        key = path.pop(0)
        data = data[key]
    return data


def replace_reference(context, match):
    ref = match.group(1)
    return get_value(context, ref.split("."))


def resolve_refs(node, context, check_mode):
    if isinstance(node, dict):
        resolved = {}
        for k, v in node.items():
            resolved[k] = resolve_refs(v, context, check_mode)
        return resolved
    elif isinstance(node, list):
        return [resolve_refs(i, context, check_mode) for i in node]
    elif isinstance(node, (str, bytes, bytearray)):
        replacer = functools.partial(replace_reference, context)
        try:
            return REREG.sub(replacer, node)
        except KeyError:
            if check_mode:
                return node
            raise
    return node


class ResourceExceptionError(Exception):
    def __init__(self, exc, msg):
        self.exc = exc
        self.msg = msg
        super().__init__(self)


class CloudClient(metaclass=ABCMeta):
    def __init__(self, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def present(self, resource: Dict) -> Dict:
        pass

    @abstractmethod
    def absent(self, resource: Dict) -> Dict:
        pass

    def run(self, desired_state, current_state, state, check_mode):

        if not HAS_PYYAML:
            raise ResourceExceptionError(
                msg=missing_required_lib("PyYAML"), exc=PYYAML_IMP_ERR
            )

        sorter = TopologicalSorter()
        for name, resource in desired_state.items():
            if state == "present":
                sorter.add(
                    name,
                    *map(operator.itemgetter(1), REREG.findall(yaml.dump(resource)))
                )
            elif state == "absent":
                sorter.add(name)
                for item in map(
                    operator.itemgetter(1), REREG.findall(yaml.dump(resource))
                ):
                    sorter.add(item, name)

        sorter.prepare()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            current_state["changed"] = False
            while sorter:
                futures = {}
                for name in sorter.get_ready():
                    if state == "present":
                        node = resolve_refs(
                            desired_state[name], current_state, check_mode
                        )
                        futures[executor.submit(self.present, node)] = name
                    elif state == "absent":
                        if name not in current_state:
                            sorter.done(name)
                            continue
                        node = resolve_refs(
                            desired_state[name], current_state, check_mode
                        )
                        futures[executor.submit(self.absent, node)] = name
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    name = futures[future]
                    if result:
                        current_state[name] = result
                        current_state["changed"] |= result["changed"]
                    else:
                        try:
                            del current_state[name]
                        except KeyError:
                            pass
                    sorter.done(name)
        return current_state
