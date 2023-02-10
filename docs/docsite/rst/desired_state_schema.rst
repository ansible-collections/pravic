.. _ansible_collections.cloud.pravic.docsite.desired_state:

YAML specification for defining desired resource state
======================================================

The users who intend to use the `pravic.pravic Collection <https://github.com/ansible-collections/pravic>`_ to provision/deprovision Cloud resources will need to use this YAML specification for defining desired resource state:

```yaml
  ResourceGroups:
  description: Array of resource groups.
  type: array
  items:
    type: object
    properties:
      ResourceGroupName:
        description: The unique identifier for a group of resources. ResourceGroupName should not include any spaces.
        type: string
      Resources:
        description: Dictionary of resources belonging to ResourceGroupName.
        type: object
        patternProperties:
          name:
            description: The locally unique identifier for a resource. It is a hash map with the name as the key."
            type: object
            properties:
              resource:
                description: Resource specific properties according to the provider.
                type: object
```

This desired resource state definition is provider-agnostic and will allow users to define one or more ResourceGroupName where each can contain one or more Resources.
The dependencies between resources will also need to be specified as:
`ResourceGroupName.ResourceName.Properties.<some property>.`

Example of Desired Resource State
=================================

For the sake of simplicity, an example resource definition for AWS provider might look something like this:

```yaml
  ---
  ResourceGroups:
  - ResourceGroupName: cloud_1
    Resources:
    bucket_02:
      Type: AWS::S3::Bucket
      Properties:
        BucketName: ansible-declared-state-02
    bucket_03:
      Type: AWS::S3::Bucket
      Properties:
        BucketName: ansible-declared-state-03
  - ResourceGroupName: cloud_2
    Resources:
    bucket_04:
      Type: AWS::S3::Bucket
      Properties:
        BucketName: ansible-declared-state-04
```

The example above shows how we take advantage of the AWS' Cloud Control / CloudFormation's resource schema for each resource you define. However, in order to give more structure to the desired resource state schema, several top-levels keys such as `ResourceGroups`, `ResourceGroupName` and `Resources` have also been included.
