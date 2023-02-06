.. _ansible_collections.cloud.pravic.docsite.stored_state:

Specification format for storing resource state
===============================================

Storing resource state allows users to have a detailed view about the resources they have provisioned earlier.
By storing resource state, a user would be able to reference their defined resources and declare a state of `absent` and expect Ansible to resolve the relationships between resources and determine the order of operations rather than requiring the user to write a properly ordered playbook.
This resource state specification is provider-agnostic and allows some resource group metadata to be stored in a `State` dictionary.

The format for storing resource state should be something like:

```yaml

    [{
        "ResourceGroupName":{
            "description":"The unique identifier for a group of resources.",
            "type":"string"
        },
        "State": {
          "description":"Dictionary of metadata for ResourceGroupName.",
          "type":"object",
          "properties": {
              "Created": {
                  "description":"Date and time in RFC3339 format that the ResourceGroup was created.",
                  "type":"date"
              },
              "Modified": {
                  "description":"Date and time in RFC3339 format that the ResourceGroup was last modified.",
                  "type":"date"
              },
              "ResourceGroup": {
                  "description":"The unique identifier for a group of resources.",
                  "type":"string"
              },
              <anything else we think makes sense>
          }
        },
        "Resources":{
            "description":"Dictionary of resources belonging to ResourceGroupName.",
            "type":"object",
            "properties": {
                "ResourceName":{
                    "description":"ResourceName is the unique identifier for a resource.",
                    "type":"object",
                    "properties": {
                      "Resource":{
                          "description":"Resource specific information.",
                          "type":"object"
                      }
                  }
              }
            }
        }
    }]

```

Example of Storing Resource State
=================================

For the sake of simplicity, an example of storing resource state definition for AWS provider might look something like this:

```yaml
    [{
        "ResourceGroupName": "cloud_1",
        "State": {
            "Created": "Mon, 05 Dec 2022 15:56:44 GMT",
            "Modified": "Mon, 05 Dec 2022 15:56:44 GMT",
            "ResourceGroup": "cloud_1",
            <anything else we think makes sense here>
          },
        "Resources":{
          "bucket_02": {
            "Type": "AWS::S3::Bucket",
            "Properties":{
                "BucketName": "ansible-declared-state-02",
                "RegionalDomainName": "ansible-declared-state-02.s3.us-east-1.amazonaws.com",
                "DomainName": "ansible-declared-state-02.s3.amazonaws.com",
                "WebsiteURL": "http://ansible-declared-state-02.s3-website-us-east-1.amazonaws.com",
                "DualStackDomainName": "ansible-declared-state-02.s3.dualstack.us-east-1.amazonaws.com",
                "Arn": "arn:aws:s3:::ansible-declared-state-02"
            }
          },
          {
          "bucket_03": {
            "Type": "AWS::S3::Bucket",
            "Properties":{
                "BucketName": "ansible-declared-state-03",
                "RegionalDomainName": "ansible-declared-state-03.s3.us-east-1.amazonaws.com",
                "DomainName": "ansible-declared-state-03.s3.amazonaws.com",
                "WebsiteURL": "http://ansible-declared-state-03.s3-website-us-east-1.amazonaws.com",
                "DualStackDomainName": "ansible-declared-state-03.s3.dualstack.us-east-1.amazonaws.com",
                "Arn": "arn:aws:s3:::ansible-declared-state-03"
            }
          }
          }
          }
        },
        {
          "ResourceGroupName": "cloud_2",
          "State": {
              "Created": "Mon, 05 Dec 2022 15:56:44 GMT",
              "Modified": "Mon, 05 Dec 2022 15:56:44 GMT",
              "ResourceGroup": "cloud_2",
              <anything else we think makes sense here>
          },
          "Resources":{
                  ...
              }
          }
    }]

```
