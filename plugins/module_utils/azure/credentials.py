import os
import inspect
import traceback

from os.path import expanduser

from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.six.moves import configparser
import ansible.module_utils.six.moves.urllib.parse as urlparse

from ansible_collections.pravic.pravic.plugins.module_utils.exception import CloudException


AZURE_CREDENTIAL_ENV_MAPPING = dict(
    profile="AZURE_PROFILE",
    subscription_id="AZURE_SUBSCRIPTION_ID",
    client_id="AZURE_CLIENT_ID",
    secret="AZURE_SECRET",
    tenant="AZURE_TENANT",
    ad_user="AZURE_AD_USER",
    password="AZURE_PASSWORD",
    cloud_environment="AZURE_CLOUD_ENVIRONMENT",
    cert_validation_mode="AZURE_CERT_VALIDATION_MODE",
    adfs_authority_url="AZURE_ADFS_AUTHORITY_URL",
    x509_certificate_path="AZURE_X509_CERTIFICATE_PATH",
    thumbprint="AZURE_THUMBPRINT",
)

HAS_AZURE = True
HAS_AZURE_EXC = None
HAS_AZURE_CLI_CORE = True

HAS_MSRESTAZURE = True
HAS_MSRESTAZURE_EXC = None

try:
    from msrestazure.azure_active_directory import AADTokenCredentials
    from msrestazure.azure_active_directory import MSIAuthentication
    from azure.cli.core.auth.adal_authentication import MSIAuthenticationWrapper
    from msrestazure import azure_cloud
    from azure.common.credentials import ServicePrincipalCredentials, UserPassCredentials
    from azure.mgmt.resource.subscriptions import SubscriptionClient
    from adal.authentication_context import AuthenticationContext
    from azure.identity._credentials import client_secret, user_password, certificate

except ImportError as exc:
    Authentication = object
    HAS_AZURE_EXC = traceback.format_exc()
    HAS_AZURE = False

try:
    from azure.cli.core.util import CLIError
    from azure.common.credentials import get_cli_profile
    from azure.common.cloud import get_cli_active_cloud
except ImportError:
    HAS_AZURE_CLI_CORE = False
    CLIError = Exception


class AzureCredentials(object):
    _cloud_environment = None
    _adfs_authority_url = None

    def __init__(
        self,
        auth_source=None,
        profile=None,
        subscription_id=None,
        client_id=None,
        secret=None,
        tenant=None,
        ad_user=None,
        password=None,
        cloud_environment="AzureCloud",
        cert_validation_mode="validate",
        api_profile="latest",
        adfs_authority_url=None,
        is_ad_resource=False,
        x509_certificate_path=None,
        thumbprint=None,
    ):
        self.is_ad_resource = is_ad_resource

        # authenticate
        self.credentials = self._get_credentials(
            auth_source=auth_source,
            profile=profile,
            subscription_id=subscription_id,
            client_id=client_id,
            secret=secret,
            tenant=tenant,
            ad_user=ad_user,
            password=password,
            cloud_environment=cloud_environment,
            cert_validation_mode=cert_validation_mode,
            api_profile=api_profile,
            adfs_authority_url=adfs_authority_url,
            x509_certificate_path=x509_certificate_path,
            thumbprint=thumbprint,
        )

        if not self.credentials:
            if HAS_AZURE_CLI_CORE:
                self.fail(
                    "Failed to get credentials. Either pass as parameters, set environment variables, "
                    "define a profile in ~/.azure/credentials, or log in with Azure CLI (`az login`)."
                )
            else:
                self.fail(
                    "Failed to get credentials. Either pass as parameters, set environment variables, "
                    "define a profile in ~/.azure/credentials, or install Azure CLI and log in (`az login`)."
                )

        # cert validation mode precedence: module-arg, credential profile, env, "validate"
        self._cert_validation_mode = cert_validation_mode or self.credentials.get("cert_validation_mode") or self._get_env("cert_validation_mode") or "validate"

        if self._cert_validation_mode not in ["validate", "ignore"]:
            self.fail("invalid cert_validation_mode: {0}".format(self._cert_validation_mode))

        # if cloud_environment specified, look up/build Cloud object
        raw_cloud_env = self.credentials.get("cloud_environment")
        if self.credentials.get("credentials") is not None and raw_cloud_env is not None:
            self._cloud_environment = raw_cloud_env
        elif not raw_cloud_env:
            self._cloud_environment = azure_cloud.AZURE_PUBLIC_CLOUD  # SDK default
        else:
            # try to look up "well-known" values via the name attribute on azure_cloud members
            all_clouds = [x[1] for x in inspect.getmembers(azure_cloud) if isinstance(x[1], azure_cloud.Cloud)]
            matched_clouds = [x for x in all_clouds if x.name == raw_cloud_env]
            if len(matched_clouds) == 1:
                self._cloud_environment = matched_clouds[0]
            elif len(matched_clouds) > 1:
                self.fail("Azure SDK failure: more than one cloud matched for cloud_environment name '{0}'".format(raw_cloud_env))
            else:
                if not urlparse.urlparse(raw_cloud_env).scheme:
                    self.fail("cloud_environment must be an endpoint discovery URL or one of {0}".format([x.name for x in all_clouds]))
                try:
                    self._cloud_environment = azure_cloud.get_cloud_from_metadata_endpoint(raw_cloud_env)
                except Exception as e:
                    self.fail("cloud_environment {0} could not be resolved: {1}".format(raw_cloud_env, e.message), exception=traceback.format_exc())

        if self.credentials.get("subscription_id", None) is None and self.credentials.get("credentials") is None:
            self.fail("Credentials did not include a subscription_id value.")
        self.subscription_id = self.credentials["subscription_id"]

        # get authentication authority
        # for adfs, user could pass in authority or not.
        # for others, use default authority from cloud environment
        if self.credentials.get("adfs_authority_url") is None:
            self._adfs_authority_url = self._cloud_environment.endpoints.active_directory
        else:
            self._adfs_authority_url = self.credentials.get("adfs_authority_url")

        if self.credentials.get("auth_source") == "msi":
            # MSI Credentials
            self.azure_credentials = self.credentials["credentials"]
            self.azure_credential_track2 = self.credentials["credential"]
        elif self.credentials.get("credentials") is not None:
            # AzureCLI credentials
            self.azure_credentials = self.credentials["credentials"]
            self.azure_credential_track2 = self.credentials["credentials"]
        elif self.credentials.get("client_id") is not None and self.credentials.get("secret") is not None and self.credentials.get("tenant") is not None:
            graph_resource = self._cloud_environment.endpoints.active_directory_graph_resource_id
            rm_resource = self._cloud_environment.endpoints.resource_manager
            self.azure_credentials = ServicePrincipalCredentials(
                client_id=self.credentials["client_id"],
                secret=self.credentials["secret"],
                tenant=self.credentials["tenant"],
                cloud_environment=self._cloud_environment,
                resource=graph_resource if self.is_ad_resource else rm_resource,
                verify=self._cert_validation_mode == "validate",
            )
            self.azure_credential_track2 = client_secret.ClientSecretCredential(
                client_id=self.credentials["client_id"], client_secret=self.credentials["secret"], tenant_id=self.credentials["tenant"]
            )

        elif (
            self.credentials.get("client_id") is not None
            and self.credentials.get("tenant") is not None
            and self.credentials.get("thumbprint") is not None
            and self.credentials.get("x509_certificate_path") is not None
        ):
            self.azure_credentials = self.acquire_token_with_client_certificate(
                self._adfs_authority_url,
                self._cloud_environment.endpoints.active_directory_resource_id,
                self.credentials["x509_certificate_path"],
                self.credentials["thumbprint"],
                self.credentials["client_id"],
                self.credentials["tenant"],
            )

            self.azure_credential_track2 = certificate.CertificateCredential(
                tenant_id=self.credentials["tenant"], client_id=self.credentials["client_id"], certificate_path=self.credentials["x509_certificate_path"]
            )

        elif self.credentials.get("ad_user") is not None and self.credentials.get("password") is not None:
            tenant = self.credentials.get("tenant")
            if not tenant:
                tenant = "common"  # SDK default

            self.azure_credentials = UserPassCredentials(
                self.credentials["ad_user"],
                self.credentials["password"],
                tenant=tenant,
                cloud_environment=self._cloud_environment,
                verify=self._cert_validation_mode == "validate",
            )

            client_id = self.credentials.get("client_id", "04b07795-8ddb-461a-bbee-02f9e1bf7b46")

            self.azure_credential_track2 = user_password.UsernamePasswordCredential(
                username=self.credentials["ad_user"],
                password=self.credentials["password"],
                tenant_id=self.credentials.get("tenant", "organizations"),
                client_id=client_id,
            )

        elif (
            self.credentials.get("ad_user") is not None
            and self.credentials.get("password") is not None
            and self.credentials.get("client_id") is not None
            and self.credentials.get("tenant") is not None
        ):
            self.azure_credentials = self.acquire_token_with_username_password(
                self._adfs_authority_url,
                self._cloud_environment.endpoints.active_directory_resource_id,
                self.credentials["ad_user"],
                self.credentials["password"],
                self.credentials["client_id"],
                self.credentials["tenant"],
            )

        else:
            self.fail(
                "Failed to authenticate with provided credentials. Some attributes were missing. "
                "Credentials must include client_id, secret and tenant or ad_user and password, or "
                "ad_user, password, client_id, tenant and adfs_authority_url(optional) for ADFS authentication, or "
                "be logged in using AzureCLI."
            )

    @staticmethod
    def fail(msg):
        raise CloudException(msg)

    def _get_env(self, module_key, default=None):
        "Read envvar matching module parameter"
        return os.environ.get(AZURE_CREDENTIAL_ENV_MAPPING[module_key], default)

    def _get_profile(self, profile="default"):
        path = expanduser("~/.azure/credentials")
        try:
            config = configparser.ConfigParser()
            config.read(path)
        except Exception as exc:
            self.fail("Failed to access {0}. Check that the file exists and you have read " "access. {1}".format(path, str(exc)))
        credentials = dict()
        for key in AZURE_CREDENTIAL_ENV_MAPPING:
            try:
                credentials[key] = config.get(profile, key, raw=True)
            except Exception:
                pass

        if credentials.get("subscription_id"):
            return credentials

        return None

    def _get_msi_credentials(self, subscription_id=None, client_id=None, _cloud_environment=None, **kwargs):
        # Get object `cloud_environment` from string `_cloud_environment`
        cloud_environment = None
        if not _cloud_environment:
            cloud_environment = azure_cloud.AZURE_PUBLIC_CLOUD
        else:
            # try to look up "well-known" values via the name attribute on azure_cloud members
            all_clouds = [x[1] for x in inspect.getmembers(azure_cloud) if isinstance(x[1], azure_cloud.Cloud)]
            matched_clouds = [x for x in all_clouds if x.name == _cloud_environment]
            if len(matched_clouds) == 1:
                cloud_environment = matched_clouds[0]
            elif len(matched_clouds) > 1:
                self.fail("Azure SDK failure: more than one cloud matched for cloud_environment name '{0}'".format(_cloud_environment))
            else:
                if not urlparse.urlparse(_cloud_environment).scheme:
                    self.fail("cloud_environment must be an endpoint discovery URL or one of {0}".format([x.name for x in all_clouds]))
                try:
                    cloud_environment = azure_cloud.get_cloud_from_metadata_endpoint(_cloud_environment)
                except Exception as exc:
                    self.fail("cloud_environment {0} could not be resolved: {1}".format(_cloud_environment, str(exc)), exception=traceback.format_exc())

        credentials = MSIAuthentication(client_id=client_id, cloud_environment=cloud_environment)
        credential = MSIAuthenticationWrapper(client_id=client_id, cloud_environment=cloud_environment)
        subscription_id = subscription_id or self._get_env("subscription_id")
        if not subscription_id:
            try:
                # use the first subscription of the MSI
                subscription_client = SubscriptionClient(credentials)
                subscription = next(subscription_client.subscriptions.list())
                subscription_id = str(subscription.subscription_id)
            except Exception as exc:
                self.fail(
                    "Failed to get MSI token: {0}. " "Please check whether your machine enabled MSI or grant access to any subscription.".format(str(exc))
                )
        return {
            "credentials": credentials,
            "credential": credential,
            "subscription_id": subscription_id,
            "cloud_environment": cloud_environment,
            "auth_source": "msi",
        }

    def _get_azure_cli_credentials(self, subscription_id=None, resource=None):
        if self.is_ad_resource:
            resource = "https://graph.windows.net/"
        subscription_id = subscription_id or self._get_env("subscription_id")
        try:
            profile = get_cli_profile()
        except Exception as exc:
            self.fail("Failed to load CLI profile {0}.".format(str(exc)))

        credentials, subscription_id, tenant = profile.get_login_credentials(subscription_id=subscription_id, resource=resource)
        cloud_environment = get_cli_active_cloud()

        cli_credentials = {"credentials": credentials, "subscription_id": subscription_id, "cloud_environment": cloud_environment}
        return cli_credentials

    def _get_env_credentials(self):
        env_credentials = dict()
        for attribute, env_variable in AZURE_CREDENTIAL_ENV_MAPPING.items():
            env_credentials[attribute] = os.environ.get(env_variable, None)

        if env_credentials["profile"]:
            credentials = self._get_profile(env_credentials["profile"])
            return credentials

        if env_credentials.get("subscription_id") is not None:
            return env_credentials

        return None

    def _get_credentials(self, auth_source=None, **params):
        # Get authentication credentials.

        arg_credentials = dict()
        for attribute, env_variable in AZURE_CREDENTIAL_ENV_MAPPING.items():
            arg_credentials[attribute] = params.get(attribute, None)

        if auth_source == "msi":
            return self._get_msi_credentials(
                subscription_id=params.get("subscription_id"), client_id=params.get("client_id"), _cloud_environment=params.get("cloud_environment")
            )

        if auth_source == "cli":
            if not HAS_AZURE_CLI_CORE:
                self.fail(msg=missing_required_lib("azure-cli", reason="for `cli` auth_source"))
            try:
                cli_credentials = self._get_azure_cli_credentials(subscription_id=params.get("subscription_id"))
                return cli_credentials
            except CLIError as err:
                self.fail("Azure CLI profile cannot be loaded - {0}".format(err))

        if auth_source == "env":
            env_credentials = self._get_env_credentials()
            return env_credentials

        if auth_source == "credential_file":
            profile = params.get("profile") or "default"
            default_credentials = self._get_profile(profile)
            return default_credentials

        # auto, precedence: module parameters -> environment variables -> default profile in ~/.azure/credentials -> azure cli
        # try module params
        if arg_credentials["profile"] is not None:
            credentials = self._get_profile(arg_credentials["profile"])
            return credentials

        if arg_credentials["client_id"] or arg_credentials["ad_user"]:
            return arg_credentials

        # try environment
        env_credentials = self._get_env_credentials()
        if env_credentials:
            return env_credentials

        # try default profile from ~./azure/credentials
        default_credentials = self._get_profile()
        if default_credentials:
            return default_credentials

        if HAS_AZURE_CLI_CORE:
            cli_credentials = self._get_azure_cli_credentials(subscription_id=params.get("subscription_id"))
            return cli_credentials

        return None

    def acquire_token_with_username_password(self, authority, resource, username, password, client_id, tenant):
        authority_uri = authority

        if tenant is not None:
            authority_uri = authority + "/" + tenant

        context = AuthenticationContext(authority_uri)
        token_response = context.acquire_token_with_username_password(resource, username, password, client_id)

        return AADTokenCredentials(token_response)

    def acquire_token_with_client_certificate(self, authority, resource, x509_certificate_path, thumbprint, client_id, tenant):
        authority_uri = authority

        if tenant is not None:
            authority_uri = authority + "/" + tenant

        context = AuthenticationContext(authority_uri)
        x509_certificate = None
        with open(x509_certificate_path, "rb") as pem_file:
            x509_certificate = pem_file.read()
        token_response = context.acquire_token_with_client_certificate(resource, client_id, x509_certificate, thumbprint)

        return AADTokenCredentials(token_response)
