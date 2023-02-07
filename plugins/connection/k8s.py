# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
    name: k8s

    short_description: Connection plugin creating kubernetes client

    description:
        - This plugin is used to create connection for resource based automation.

    requirements:
      - kubernetes-client

    options:
      kubeconfig:
        description:
          - Path to a kubernetes config file. Defaults to I(~/.kube/config)
          - The configuration can be provided as dictionary. Added in version 2.4.0.
        default: ''
        vars:
          - name: ansible_k8s_kubeconfig
          - name: ansible_k8s_config
        env:
          - name: K8S_AUTH_KUBECONFIG
      context:
        description:
          - The name of a context found in the K8s config file.
        default: ''
        vars:
          - name: ansible_k8s_context
        env:
          - name: K8S_AUTH_CONTEXT
      host:
        description:
          - URL for accessing the API.
        default: ''
        vars:
          - name: ansible_k8s_host
          - name: ansible_k8s_server
        env:
          - name: K8S_AUTH_HOST
          - name: K8S_AUTH_SERVER
      username:
        description:
          - Provide a username for authenticating with the API.
        default: ''
        vars:
          - name: ansible_k8s_username
          - name: ansible_k8s_user
        env:
          - name: K8S_AUTH_USERNAME
      password:
        description:
          - Provide a password for authenticating with the API.
          - Please be aware that this passes information directly on the command line and it could expose sensitive data.
            We recommend using the file based authentication options instead.
        default: ''
        vars:
          - name: ansible_k8s_password
        env:
          - name: K8S_AUTH_PASSWORD
      api_key:
        description:
          - API authentication bearer token.
          - Please be aware that this passes information directly on the command line and it could expose sensitive data.
            We recommend using the file based authentication options instead.
        vars:
          - name: ansible_k8s_token
          - name: ansible_k8s_api_key
        env:
          - name: K8S_AUTH_TOKEN
          - name: K8S_AUTH_API_KEY
      client_cert:
        description:
          - Path to a certificate used to authenticate with the API.
        default: ''
        vars:
          - name: ansible_k8s_cert_file
          - name: ansible_k8s_client_cert
        env:
          - name: K8S_AUTH_CERT_FILE
        aliases: [ k8s_cert_file ]
      client_key:
        description:
          - Path to a key file used to authenticate with the API.
        default: ''
        vars:
          - name: ansible_k8s_key_file
          - name: ansible_k8s_client_key
        env:
          - name: K8S_AUTH_KEY_FILE
        aliases: [ k8s_key_file ]
      ca_cert:
        description:
          - Path to a CA certificate used to authenticate with the API.
        default: ''
        vars:
          - name: ansible_k8s_ssl_ca_cert
          - name: ansible_k8s_ca_cert
        env:
          - name: K8S_AUTH_SSL_CA_CERT
        aliases: [ k8s_ssl_ca_cert ]
      validate_certs:
        description:
          - Whether or not to verify the API server's SSL certificate. Defaults to I(true).
        default: ''
        vars:
          - name: ansible_k8s_verify_ssl
          - name: ansible_k8s_validate_certs
        env:
          - name: K8S_AUTH_VERIFY_SSL
        aliases: [ k8s_verify_ssl ]
"""

from ansible_collections.pravic.pravic.plugins.plugin_utils.connection import CloudConnectionBase


class Connection(CloudConnectionBase):
    """Local kubernetes connection plugin"""

    TRANSPORT = "cloud.pravic.k8s"

    def documentation(self):
        return DOCUMENTATION

    def cloud_provider(self):
        return "k8s"

    def connection_name(self):
        return self.TRANSPORT
