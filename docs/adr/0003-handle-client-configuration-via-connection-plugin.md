# Why are we using a connection plugin to handle client configuration ?

Date: 2023-02-07

## Status

Proposed

## Context

The Pravic project aims to manage resources on multiple cloud provider using the ``resource`` module.
In order to create/delete/update theses resources, user need to provide YAML definition of the resources along with credentials to create cloud client configuration, so that the module can know if theses resources will be created on Kubernetes cluster, AWS or any other provider.

Theses credentials can be provided as parameters of the ``resource`` module, this means for each provider on which we are going to deploy resources in we need a dedicated tasks with the corresponding parameters, this has the drawback to increase the complexity of the playbook and this can of playbook is not really reusable as this need to be adapted for each cloud provider on which we need to deploy resources.

## Decision

We propose to handle client configuration using connection plugins. Each supported cloud provider will have its dedicated connection plugin, adding support for a new cloud provider does not require update of the ``resource`` module parameters. Users can create reusable playbooks, running with different inventory configuration which will deal with the client configuration.

## Consequences

Implementation of connection plugin means that we cannot use Ansible native connection plugin (e.g. ssh, etc) so this means for instance if the user intend to execute ``resource`` module from a distant machine where credentials or required librairies are installed, this wont be possible using the connection plugin, user need to install Ansible on this machine and use pravic collection on it.