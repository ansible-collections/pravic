# 1. What the UX of updates to state should be

Date: 2023-01-27

## Status

Proposed

## Context

In general, Ansible modules allow two `states: present` and `state: absent`. When `state=present`, the resource is created if it does not already exist or is updated. In the case of updating a resource, the Ansible module provides `purge_*` parameters to give the user granular control over the information they wish to update.

Let’s take a deep look at how `purge_tags` work in the amazon.aws collection for simplicity:
* When `purge_tags=true` and tags are set, existing tags are purged from the resource to match exactly what is defined by tags parameter.
* If tags parameter is not set then tags are not modified even if `purge_tags=true`.
* When `purge_tags=false` and tags are set, the resource tags are updated with what is defined by tags parameter.

A plenty of existing Ansible modules support purge_* parameters for different configurations; just to mention a few examples:
* [purge_listeners](https://github.com/ansible-collections/amazon.aws/blob/main/plugins/modules/elb_application_lb.py)
* [purge_rules](https://github.com/ansible-collections/amazon.aws/blob/main/plugins/modules/elb_application_lb.py)
* [purge_security_groups](https://github.com/ansible-collections/amazon.aws/blob/main/plugins/modules/rds_instance.py)
* [purge_iam_roles](https://github.com/ansible-collections/amazon.aws/blob/main/plugins/modules/rds_instance.py)
* [purge_policies](https://github.com/ansible-collections/amazon.aws/blob/main/plugins/modules/iam_user.py)
* …

For example, we have the following S3 bucket with some tags:

```json
    "s3_bucket_1": {
        "Properties": {
            "BucketName": "pravic-s3-bucket-1",
            "Tags": [
                {
                    "Key": "tag_1",
                    "Value": "Tag1"
                },
                {
                    "Key": "tag_2",
                    "Value": "Tag2"
                }
            ]
        },
        "Type": "AWS::S3::Bucket"
    },
```

Suppose we want to update the S3 bucket, retaining the tags already assigned:

```yaml
    resources:
        s3_bucket_1:
            Type: AWS::S3::Bucket
            Properties:
            BucketName: pravic-s3-bucket-1
            Tags:
                - Key: tag_3
                Value: Tag_3
```

Without `purge_tags` option, we would need to perform three tasks:
* Gather information about the existing S3 bucket and find out its actual tags;
* Remove the existing tags of the S3 bucket;
* Re-tag the S3 bucket with the new and old tags;

`purge_tags` option will allow you to set that configuration within only one task by setting `purge_tags=false`.

## Decision and possible consequencies

With the new resource modules and implementing only `state=present` will result quite difficult to implement a `purge_*` parameter for each possible property of each resource module.

The choice not to implement `purge_*` parameters seems to be a missing feature from the user's point of view, who will not have the ability to easily and immediately change the state of resources as desired in a single task.

One possible approach would be to support a generic purge parameter. In addition, a `state: updated` could be added, allowing the user to explicitly confirm their intention to change the state of the resource.

However, let’s take a look at the network resource modules that support different states ([see](https://docs.ansible.com/ansible/latest/network/user_guide/network_resource_modules.html)).

Relating to the previous example, `state=merged` will allow us to accomplish that in one single task. Conversely, if we want to reinitialize resource tags completely, `state=deleted` allows us to do so. `state=replaced`, on the other hand, allows us to replace a resource's existing information with new one.

In addition, `state=gathered`, will allow us to get information on a specific resource.

To conclude, the proposal is to comply with network resource modules states and implement those for project pravic when it comes to resource update.

However, `state=present` will do resource provisioning, while `state=absent` will do resource deprovisioning.
