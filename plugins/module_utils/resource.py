import concurrent.futures
import functools
import operator
import re
from graphlib import TopologicalSorter

import yaml
import time
import os


REREG = re.compile(r"resource:((\w+)\S+)")


def get_value(data, path):
    while path:
        key = path.pop(0)
        data = data[key]
    return data


def replace_reference(context, match):
    ref = match.group(1)
    return get_value(context, ref.split("."))


def resolve_refs(node, context):
    if isinstance(node, dict):
        resolved = {}
        for k, v in node.items():
            resolved[k] = resolve_refs(v, context)
        return resolved
    elif isinstance(node, list):
        return [resolve_refs(i, context) for i in node]
    else:
        replacer = functools.partial(replace_reference, context)
        return REREG.sub(replacer, node)


def resolve_dependencies(sorter, desired_state, state):
    for name, resource in desired_state.items():
        if state == "present":
            sorter.add(
                name, *map(operator.itemgetter(1), REREG.findall(yaml.dump(resource)))
            )
        elif state == "absent":
            sorter.add(name)
            for item in map(operator.itemgetter(1), REREG.findall(yaml.dump(resource))):
                sorter.add(item, name)

    sorter.prepare()


def run(desired_state, current_state, client, state):

    output = {}

    start = time.time()
    sorter = TopologicalSorter()
    resolve_dependencies(sorter, desired_state, state)
    end = time.time()

    if os.environ.get("PRAVIC_TIME_DEPENDENCY_RESOLUTION", "").lower() in ("true", "yes", "1"):
        output.update(
            {"duration": {"dependency_resolution": (end - start) * 1000}}
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        while sorter:
            futures = {}
            for name in sorter.get_ready():
                if state == "present":
                    node = resolve_refs(desired_state[name], current_state)
                    futures[executor.submit(client.present, node)] = name
                elif state == "absent":
                    if name not in current_state:
                        sorter.done(name)
                        continue
                    node = resolve_refs(desired_state[name], current_state)
                    futures[executor.submit(client.absent, node)] = name
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                name = futures[future]
                if result:
                    current_state[name] = result
                else:
                    try:
                        del current_state[name]
                    except KeyError:
                        pass
                sorter.done(name)
    output["resources"] = current_state
    return output
