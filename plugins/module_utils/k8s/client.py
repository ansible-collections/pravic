# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Dict
import traceback

K8S_IMP_ERR = None
try:
    import kubernetes
    HAS_K8S_CLIENT = True
except ImportError:
    K8S_IMP_ERR = traceback.format_exc()
    HAS_K8S_CLIENT = False

from ansible.module_utils.basic import missing_required_lib
from ansible_collections.pravic.pravic.plugins.module_utils.resource import CloudClient


AUTH_ARGS = (
    "kubeconfig",
    "context",
    "host",
    "api_key",
    "username",
    "password",
    "validate_certs",
    "ca_cert",
    "client_cert",
    "client_key",
)


def get_api_client(**kwargs):

    auth = {}
    for key in AUTH_ARGS:
        if kwargs.get(key):
            auth[key] = kwargs.get(key)

    def auth_set(*names):
        return all(auth.get(name) for name in names)

    def _load_config():
        kubeconfig = auth.get("kubeconfig")
        optional_arg = {
            "context": auth.get("context"),
        }
        kubernetes.config.load_kube_config(config_file=kubeconfig, **optional_arg)

    if auth_set("host"):
        # Removing trailing slashes if any from hostname
        auth["host"] = auth.get("host").rstrip("/")

    configuration = None
    if auth_set("username", "password", "host") or auth_set("api_key", "host"):
        # We have enough in the parameters to authenticate, no need to load incluster or kubeconfig
        args = {key: auth.get(key) for key in ("username", "password", "host")}
        # api_key will be set later in this function
        configuration = kubernetes.client.Configuration(**args)
    elif auth_set("kubeconfig") or auth_set("context"):
        _load_config()
    else:
        # First try to do incluster config, then kubeconfig
        try:
            kubernetes.config.load_incluster_config()
        except kubernetes.config.ConfigException:
            _load_config()

    # Override any values in the default configuration with Ansible parameters
    # As of kubernetes-client v12.0.0, get_default_copy() is required here
    if not configuration:
        try:
            configuration = kubernetes.client.Configuration().get_default_copy()
        except AttributeError:
            configuration = kubernetes.client.Configuration()

    if auth.get('api_key'):
        setattr(
            configuration, key, {"authorization": "Bearer {0}".format(auth.get('api_key'))}
        )

    return kubernetes.dynamic.DynamicClient(
        kubernetes.client.ApiClient(configuration)
    )


class K8sException(Exception):
    def __init__(self, exc, msg):
        self.exc = exc
        self.msg = msg
        super().__init__(self.msg)


class K8sClient(CloudClient):
    def __init__(self, **kwargs: Dict) -> None:

        if not HAS_K8S_CLIENT:
            raise K8sException(
                msg=missing_required_lib("kubernetes"), exc=K8S_IMP_ERR
            )

        super(K8sClient, self).__init__(**kwargs)

        self.client = get_api_client(**kwargs)

    def _get_existing(self, api_version: str, kind: str, name: str, namespace: str):
        resource = self.client.resources.get(
            prefix="api", api_version=api_version, kind=kind
        )
        try:
            existing = resource.get(name=name, namespace=namespace).to_dict()
        except kubernetes.dynamic.exceptions.NotFoundError:
            existing = {}
        return resource, existing

    def present(self, resource: Dict) -> Dict:
        api_version = resource.get("apiVersion")
        kind = resource.get("kind")
        name = resource["metadata"].get("name")
        namespace = resource["metadata"].get("namespace")

        resource_api, existing = self._get_existing(api_version, kind, name, namespace)
        if existing:
            if self.check_mode:
                return {"changed": True, **existing}
            instance = resource_api.patch(resource, name=name, namespace=namespace).to_dict()
            return {"changed": True, **instance}
        else:
            instance = resource_api.create(resource, name=name, namespace=namespace).to_dict()
            return {"changed": True, **instance}

    def absent(self, resource: Dict) -> Dict:
        api_version = resource.get("apiVersion")
        kind = resource.get("kind")
        name = resource["metadata"].get("name")
        namespace = resource["metadata"].get("namespace")

        resource_api, existing = self._get_existing(api_version, kind, name, namespace)
        if existing:
            if not self.check_mode:
                resource_api.delete(name=name, namespace=namespace)
            return {"changed": True, **existing}
        else:
            return {"changed": False, **resource}
