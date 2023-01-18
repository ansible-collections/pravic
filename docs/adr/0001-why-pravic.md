# 1. Why Project Pravic

Date: 2023-01-17

## Status

Proposed

## Context

Most cloud automation today works with REST APIs in some form. The extent to which they adhere to a pure definition of REST can vary, but they are all generally based around managing resources through some declarative HTTP API. This is a fundamentally different mode of operation than running commands or executing code on a server somewhere in order to change its state.

Historically, it has been necessary for content developers to leverage Cloud SDKs to manually create individual plugins for cloud resources and services, which imposes a high opportunity cost for automating against clouds as well as a burden on users to select and utilize modules for individual services and resources.  Recent cloud collections (vmware.vmware_rest and amazon.cloud) have been able to take advantage of REST resource schemas to more rapidly generate plugins, but this has also exposed limitations in the traditional Ansible task-driven model when automating against resource-based remote targets.

Ansible's domain model is based on tasks, not resources. Conversely, a REST API is based on resources, not tasks. We are forcing both developers and users to try and jam resources into tasks. The resulting lack of a strong domain model for resources leads to a number of serious deficiencies for cloud automation content:

* An inability to declare explicit dependencies between resources. Dependencies are currently just a byproduct of the ordered task-based execution model of Ansible and registered output. To be fully useful, for example, resources defined in a role should be accessible outside the role in some sort of namespaced construct. A more robust and explicit means of declaring dependencies is needed.
* An inability to intelligently create a set of resources in parallel. If dependencies between resources were more explicitly declared, we would more easily be able to concurrently create resources, potentially leading to significant performance gains.
* An inability to easily understand the desired end state of your infrastructure. A task-based execution model means a resource may be defined in one task and then modified later by another, requiring sequential reading of the entire playbook to know what your end state will be.
* An inability to easily tear down your infrastructure. By forcing resources into tasks, we also force users to bake the resource state into the playbook. Decoupling the state from the resource definition opens up the possibility of using the same content to both provision and deprovision your infrastructure. Given that ephemerality is one of the selling points of cloud infrastructure, deprovisioning should require almost no extra effort from Ansible.

### Hosts

With a web API, the state that we're managing lives on the other end of an HTTP connection. It doesn't really matter where we run our playbook. The notion of local and remote host is largely meaningless in this context and adds a maintenance burden on developers and a cognitive burden on users. This functionality provides little benefit to REST-based collections.

### Task Execution
The Ansible model where each task is executed in a separate Python process is an expensive constraint that prevents the easy reuse of connections. When a collection does all its work over HTTP, the benefits of connection reuse can be significant. Turbo Mode was designed to address this, but it is not a viable long-term solution. The maintenance burden is high. It requires extra work by plugin developers and playbook authors, and this is not something either of these personas should have to think about. It should be provided as base functionality by Ansible.

## Decision

We propose to extend the language and capabilities of Ansible to be able to declare and manage non-host-based resources and the relationships between these resources where a REST schema exists for those resources.  Building on the work done in our REST-based generated collections, we would create a schema or language by which plugin developers can define resources and dependencies for the platform to manage.  The platform could then be enabled to execute automation against HTTP and REST-based targets in a manner that better reflects the nature of these types of remote systems.

This work would additionally allow us to better enable machine-driven content creation and discovery and reduce the time to market and maintenance burden for new content.

### Resource Declaration

A resource definition should be the authoritative view of the state or status of a resource.  The definition provides a configuration as code view of the desired state of the resource.  This differs from Ansible's existing task-based approach to cloud automation by abstracting the individual steps necessary to achieve the desired state, which can involve many modules and tasks which must be executed in a strict order for many cloud services today.
```yaml
---
resources:
  instance_01:
    - name: instance_01
      Type: AWS::EC2::Instance
      Properties:
        AvailabilityZone: us-east-1
        ImageId: String
        InstanceType: m1.medium
        KeyName: example_key
        SecurityGroupIds:
          - String
        SubnetId: resource:group_01.Properties.GroupId
        Tags:
          - Bar: Baz
  elasticache_01:
    - name: cache_01
      Type: AWS::ElastiCache::CacheCluster
      Properties:
        CacheNodeType: cache.m1.medium
        ClusterName: cache_01
        Engine: redis
        Tags:
          - test: tag
        VpcSecurityGroupIds:
          - resource:group_01.Properties.GroupName
  group_01:
    - name: group_01
      Type: AWS::EC2::SecurityGroup
      Properties:
        GroupDescription: some_group
        GroupName: group_01
        SecurityGroupEgress:
          - {{ Egress }}
        SecurityGroupIngress:
          - {{ Ingress }}
        Tags:
          - Foo: Bar
        VpcId: resource:vpc_01.Properties.VpcId
  vpc_1:
    - name: vpc_01
      Type: AWS::EC2::VPC
      Properties:
        CidrBlock: 10.0.0.0/16
```
Generally we want to take advantage of the provider's schema as much as possible, such as the above example which is based directly on AWS' Cloud Control / CloudFormation resource schemas.  However to integrate this with Ansible it will be necessary to put some structure in place around top-level key words and the format in which resources may be accessed and referenced to ensure a consistent user experience across different Ansible components.

### Dependency Resolution

Cloud resources commonly depend on other resources to exist or be in a specific state before they can be created.  This often causes frustration for Ansible users as they must maintain a high degree of awareness of these relationships and ensure that tasks have the appropriate checks for resource readiness and availability.

Where a vendor provides a reference schema for their resources, such as in the case of the AWS Cloud Control API, we can programmatically identify these dependencies and make decisions about the order of resource actions.

In the above example, the VPC must be created before any other resources and the security group must be created before the instance and the elastic cache.  We could identify this both through the resource references in the resource definition and by analyzing the AWS schemas for these resources.

### Asynchronous Execution

Cloud deployments are often made up of a large number of resources.  Some resources will depend on each other, and others will not.  Common automation scenarios frequently experience long execution times as tasks are executed one at a time, and with each task needing to duplicate API authentication and connection management.  The async keyword and careful construction of roles and playbooks can help, provided the content creator can maintain a high degree of contextual awareness about which tasks can happen in what order.

With a declared set of resources and knowledge of the dependencies between resources, we should be able to programmatically split resource changes into a series of actions which must happen synchronously and those which can happen asynchronously, saving a significant amount of execution time.  We can also execute these activities in a shared connection or connection pool to reduce the overhead of spawning a new Python process and API connection for each task.

In the above example, the VPC and security group must be synchronously created first, but the instance and cache could be created at the same time without blocking each other.  Additional resources added to the definition could potentially be created with further asynchronousity. 

Improvements to Ansible's ability to execute tasks asynchronously can also be used with existing automation and collections, without requiring users to adopt Resource Based

## Consequences

Implementation of Project Pravic will be a significant undertaking impacting multiple components of the Ansible ecosystem.  Further, Ansible users will need to learn a new syntax to take advantage of the new features.  Implementation will ensure that use of the new features is completely optional for the user so as not to burden our users unnecessarily. 