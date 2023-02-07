# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
    name: aws

    short_description: Connection plugin creating AWS client

    description:
        - This plugin is used to create connection for resource based automation.

    options:
      aws_access_key_id:
        description:
          - Amazon AWS Region
        default: ''
        vars:
          - name: ansible_aws_access_key_id
        env:
          - name: AWS_CONFIG_ACCESS_KEY_ID
      aws_secret_access_key:
        description:
          - Amazon AWS Secret access token
        default: ''
        vars:
          - name: ansible_aws_secret_access_key
        env:
          - name: AWS_CONFIG_SECRET_ACCESS_KEY
      aws_session_token:
        description:
          - Amazon AWS Session token
        default: ''
        vars:
          - name: ansible_aws_session_token
        env:
          - name: AWS_CONFIG_SESSION_TOKEN
      region_name:
        description:
          - Amazon AWS Region
        default: ''
        vars:
          - name: ansible_aws_region_name
        env:
          - name: AWS_CONFIG_REGION_NAME
      profile_name:
        description:
          - The Amazon AWS Profile
        default: ''
        vars:
          - name: ansible_aws_profile_name
        env:
          - name: AWS_CONFIG_PROFILE_NAME
"""

from ansible_collections.pravic.pravic.plugins.plugin_utils.connection import CloudConnectionBase


class Connection(CloudConnectionBase):
    """Local Amazon connection plugin"""

    TRANSPORT = "cloud.pravic.aws"

    def documentation(self):
        return DOCUMENTATION

    def cloud_provider(self):
        return "aws"

    def connection_name(self):
        return self.TRANSPORT
