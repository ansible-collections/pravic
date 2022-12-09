import kubernetes


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

class K8sClient:
    def __init__(self, **kwargs):
        self.client = get_api_client(**kwargs)

    def present(self, definition):
        api_version = definition.get("apiVersion")
        kind = definition.get("kind")
        name = definition["metadata"].get("name")
        namespace = definition["metadata"].get("namespace")
        resource = self._get_resource(api_version, kind)
        try:
            instance = resource.get(name=name, namespace=namespace)
            resource.patch(definition, name=name, namespace=namespace)
        except kubernetes.dynamic.exceptions.NotFoundError:
            instance = resource.create(definition, name=name, namespace=namespace)
        return instance.to_dict()

    def absent(self, definition):
        api_version = definition.get("apiVersion")
        kind = definition.get("kind")
        name = definition["metadata"].get("name")
        namespace = definition["metadata"].get("namespace")
        resource = self._get_resource(api_version, kind)
        try:
            resource.delete(name=name, namespace=namespace)
        except kubernetes.dynamic.exceptions.NotFoundError:
            pass
        return {}

    def _get_resource(self, api_version, kind, prefix="api"):
        return self.client.resources.get(
            prefix=prefix, api_version=api_version, kind=kind
        )