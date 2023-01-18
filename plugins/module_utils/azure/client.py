import json
from typing import Any, Dict, Tuple
import copy
import uuid

from ansible_collections.pravic.pravic.plugins.module_utils.azure.credentials import AzureCredentials

try:
    from msrestazure.tools import resource_id
    from msrestazure.azure_configuration import AzureConfiguration
    from msrest.service_client import ServiceClient
    from msrestazure.azure_exceptions import CloudError
    from msrest.pipeline import ClientRawResponse
    from msrest.polling import LROPoller
    from msrestazure.polling.arm_polling import ARMPolling

except ImportError:
    pass

from ansible_collections.pravic.pravic.plugins.module_utils.resource import CloudClient
from ansible.module_utils.common.dict_transformations import dict_merge


class AzureRestClient(object):

    def __init__(self, **kwargs):

        is_track2 = kwargs.pop("is_track2", None)
        user_agent = kwargs.pop("user_agent", None)
        self.azure_credentials = AzureCredentials(**kwargs)

        self.base_url = self.azure_credentials._cloud_environment.endpoints.resource_manager

        # https://github.com/Azure/msrestazure-for-python/pull/169
        # China's base_url doesn't end in a trailing slash, though others do,
        # and we need a trailing slash when generating credential_scopes below.
        if not self.base_url.endswith("/"):
            self.base_url += "/"

        self.subscription_id = self.azure_credentials.subscription_id
        if is_track2:
            self.credentials = self.azure_credentials.azure_credential_track2
        else:
            self.credentials = self.azure_credentials.azure_credentials

        self._config = None
        self.user_agent = user_agent or 'Ansible/Pravic'

        self._client = ServiceClient(self.credentials, self.configuration)
        self.models = None

    @property
    def configuration(self):
        if not self._config:
            self._config = AzureConfiguration(self.base_url)
            self._config.add_user_agent(self.user_agent)
        return self._config

    def query(self, url, method, query_parameters, header_parameters, body, expected_status_codes, polling_timeout, polling_interval):
        # Construct and send request
        operation_config = {}

        request = None

        if header_parameters is None:
            header_parameters = {}

        header_parameters['x-ms-client-request-id'] = str(uuid.uuid1())

        if method == 'GET':
            request = self._client.get(url, query_parameters)
        elif method == 'PUT':
            request = self._client.put(url, query_parameters)
        elif method == 'POST':
            request = self._client.post(url, query_parameters)
        elif method == 'HEAD':
            request = self._client.head(url, query_parameters)
        elif method == 'PATCH':
            request = self._client.patch(url, query_parameters)
        elif method == 'DELETE':
            request = self._client.delete(url, query_parameters)
        elif method == 'MERGE':
            request = self._client.merge(url, query_parameters)

        response = self._client.send(request, header_parameters, body, **operation_config)

        if response.status_code not in expected_status_codes:
            exp = CloudError(response)
            exp.request_id = response.headers.get('x-ms-request-id')
            raise exp
        elif response.status_code == 202 and polling_timeout > 0:
            def get_long_running_output(response):
                return response
            poller = LROPoller(self._client,
                               ClientRawResponse(None, response),
                               get_long_running_output,
                               ARMPolling(polling_interval, **operation_config))
            response = self.get_poller_result(poller, polling_timeout)

        return response

    def get_poller_result(self, poller, timeout):
        poller.wait(timeout=timeout)
        return poller.result()


class AzureClient(CloudClient):
    def __init__(self, check_mode=False, **kwargs: Any) -> None:
        self.mgmt_client = AzureRestClient(**kwargs)
        self.check_mode = check_mode

    def _get_resource_url(self, resource: Dict) -> str:
        params = {}
        params['subscription'] = resource.get("subscriptionId") or self.mgmt_client.subscription_id
        params['resource_group'] = resource.get("resourceGroupName")

        params['namespace'] = resource.get("provider")
        params['type'] = resource.get("type")
        params['name'] = resource.get("name")

        for i, item in enumerate(resource.get("subresource", [])):
            str_i = str(i + 1)
            params[f'child_namespace_{str_i}'] = item.get("namespace")
            params[f'child_type_{str_i}'] = item.get("type")
            params[f'child_name_{str_i}'] = item.get("name")

        return resource_id(**params)

    def _get_api_version(self, resource_url: str) -> str:

        try:
            # extract provider and resource type
            if "/providers/" in resource_url:
                provider = resource_url.split("/providers/")[1].split("/")[0]
                resourceType = resource_url.split(provider + "/")[1].split("/")[0]
                url = "/subscriptions/" + self.mgmt_client.subscription_id + "/providers/" + provider
                api_versions = json.loads(self.mgmt_client.query(url, "GET", {'api-version': '2015-01-01'}, None, None, [200], 0, 0).text)
                for rt in api_versions['resourceTypes']:
                    if rt['resourceType'].lower() == resourceType.lower():
                        api_version = rt['apiVersions'][0]
                        break
            else:
                # if there's no provider in API version, assume Microsoft.Resources
                api_version = '2018-05-01'
            if not api_version:
                self.fail("Couldn't find api version for {0}/{1}".format(provider, resourceType))
        except Exception as exc:
            self.fail("Failed to obtain API version: {0}".format(str(exc)))

        return api_version

    def _get_existing_resource(self, resource: str) -> Tuple[str, str, Dict]:

        existing = {}
        url = self._get_resource_url(resource)
        api_version = resource.get("api-version")
        if not api_version:
            api_version = self._get_api_version(url)

        qry_params = {"api-version": api_version}
        response = self.mgmt_client.query(url, "GET", qry_params, None, None, [200, 404], 0, 0)

        if response.status_code != 404:
            existing = json.loads(response.text)

        return (api_version, url, existing)

    def _query_resource(self,
                        method: Dict,
                        api_version: str,
                        resource_url: str,
                        body: str,
                        status_code: list[int] = None,
                        polling_timeout: int = 0,
                        polling_interval: int = 60) -> Dict:

        qry = {"api-version": api_version}
        headers = {"Content-Type": "application/json; charset=utf-8"}

        if status_code is None:
            status_code = []

        return self.mgmt_client.query(resource_url,
                                      method,
                                      qry,
                                      headers,
                                      body,
                                      status_code,
                                      polling_timeout,
                                      polling_interval)

    def present(self, resource: Dict) -> Dict:
        api_version, resource_url, existing = self._get_existing_resource(resource)
        body = resource.get("parameters", {})
        changed = not existing or (dict_merge(existing, body) != existing)
        if changed and not self.check_mode:
            response = self._query_resource("PUT", api_version, resource_url, body, status_code=[201])
            try:
                existing = json.loads(response.text)
            except Exception:
                existing = response.text
        return {"changed": True, **existing}

    def absent(self, resource: Dict) -> Dict:
        api_version, resource_url, existing = self._get_existing_resource(resource)
        changed = bool(existing)
        if changed and not self.check_mode:
            self._query_resource("DELETE", api_version, resource_url, {}, status_code=[204])
        return {"changed": True, **existing}
