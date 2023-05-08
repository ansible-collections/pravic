# Pravic Collection for Ansible
<!-- Add CI and code coverage badges here. Samples included below. -->
[![CI](https://github.com/ansible-collections/REPONAMEHERE/workflows/CI/badge.svg?event=push)](https://github.com/ansible-collections/pravic/actions) [![Codecov](https://img.shields.io/codecov/c/github/ansible-collections/pravic)](https://codecov.io/gh/ansible-collections/pravic)

<!-- Describe the collection and why a user would want to use it. What does the collection do? -->
This is an experimental project intended to explore how Ansible could be used to manage cloud-based resources in a more declarative way.

## Code of Conduct

We follow the [Ansible Code of Conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html) in all our interactions within this project.

If you encounter abusive behavior, please refer to the [policy violations](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html#policy-violations) section of the Code for information on how to raise a complaint.

## Communication

<!--List available communication channels. In addition to channels specific to your collection, we also recommend to use the following ones.-->

We announce releases and important changes through Ansible's [The Bullhorn newsletter](https://github.com/ansible/community/wiki/News#the-bullhorn). Be sure you are [subscribed](https://eepurl.com/gZmiEP).

Join us in the `#ansible` (general use questions and support), `#ansible-community` (community and collection development questions), and other [IRC channels](https://docs.ansible.com/ansible/devel/community/communication.html#irc-channels).

We take part in the global quarterly [Ansible Contributor Summit](https://github.com/ansible/community/wiki/Contributor-Summit) virtually or in-person. Track [The Bullhorn newsletter](https://eepurl.com/gZmiEP) and join us.

For more information about communication, refer to the [Ansible Communication guide](https://docs.ansible.com/ansible/devel/community/communication.html).

## Contributing to this collection

<!--Describe how the community can contribute to your collection. At a minimum, fill up and include the CONTRIBUTING.md file containing how and where users can create issues to report problems or request features for this collection. List contribution requirements, including preferred workflows and necessary testing, so you can benefit from community PRs. If you are following general Ansible contributor guidelines, you can link to - [Ansible Community Guide](https://docs.ansible.com/ansible/devel/community/index.html). List the current maintainers (contributors with write or higher access to the repository). The following can be included:-->

The content of this collection is made by people like you, a community of individuals collaborating on making the world better through developing automation software.

We are actively accepting new contributors.

Any kind of contribution is very welcome.

You don't know how to start? Refer to our [contribution guide](CONTRIBUTING.md)!

We use the following guidelines:

* [CONTRIBUTING.md](CONTRIBUTING.md)
* [REVIEW_CHECKLIST.md](REVIEW_CHECKLIST.md)
* [Ansible Community Guide](https://docs.ansible.com/ansible/latest/community/index.html)
* [Ansible Development Guide](https://docs.ansible.com/ansible/devel/dev_guide/index.html)
* [Ansible Collection Development Guide](https://docs.ansible.com/ansible/devel/dev_guide/developing_collections.html#contributing-to-collections)

## Collection maintenance

The current maintainers are listed in the [MAINTAINERS](MAINTAINERS) file. If you have questions or need help, feel free to mention them in the proposals.

To learn how to maintain / become a maintainer of this collection, refer to the [Maintainer guidelines](MAINTAINING.md).

## Governance

<!--Describe how the collection is governed. Here can be the following text:-->

The process of decision making in this collection is based on discussing and finding consensus among participants.

Every voice is important. If you have something on your mind, create an issue or dedicated discussion and let's discuss it!

## Using this collection

The `pravic.pravic` collection enables use of ansible-playbook to manage a set of resources which have been declared in a playbook or in a YAML file.

Given a `playbook.yml` file of:

```yaml

- hosts: localhost
  gather_facts: false
  vars_files:
    - resources.yml
  tasks:
    - name: cloud_1
      pravic.pravic.resources:
        client: "aws"
        state: "{{ state | default('present') }}"
        resources: "{{ resources }}"
```

And a `resources.yaml` file:

```yaml
resources:
  bucket_01:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: ansible-declared-state-01
      Tags:
        - Key: otherbucket
          Value: resource:bucket_02.Properties.Arn

  bucket_02:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: ansible-declared-state-02

  bucket_03:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: ansible-declared-state-03
```

Executing `ansible-playbook playbook.yml` with a set of valid AWS credentials would create the specified S3 buckets.  Notably, the resource named `bucket_01` depends on the ARN of `bucket_02`.  The pravic collection will [resolve references](https://github.com/ansible-collections/pravic/blob/main/plugins/module_utils/resource.py) between resources and determine the correct order to execute API calls to create resources in as well as automatically supplying the value without the playbook author needing to include a task to query the S3 API for the bucket info and register the ARN as an Ansible variable.

If you do not want to define the resources in a separate YAML file, you can also define them directly in the `playbook.yml` file like this:

```yaml

- hosts: localhost
  gather_facts: false
  tasks:
    - name: cloud_1
      pravic.pravic.resources:
        client: "aws"
        state: "{{ state | default('present') }}"
        resources:
          bucket_01:
            Type: AWS::S3::Bucket
            Properties:
              BucketName: ansible-declared-state-01
              Tags:
                - Key: otherbucket
                  Value: resource:bucket_02.Properties.Arn
          bucket_02:
            Type: AWS::S3::Bucket
            Properties:
              BucketName: ansible-declared-state-02
          bucket_03:
            Type: AWS::S3::Bucket
            Properties:
              BucketName: ansible-declared-state-03
```

This collection is tested using GitHub Actions. To know more about CI, refer to [CI.md]https://github.com/ansible-collections/pravic/blob/main/CI.md].

## Release notes

See the [changelog](https://github.com/ansible-collections/pravic/tree/main/CHANGELOG.rst).

## Roadmap

<!-- Optional. Include the roadmap for this collection, and the proposed release/versioning strategy so users can anticipate the upgrade/update cycle. -->

## More information

<!-- List out where the user can find additional information, such as working group meeting times, slack/IRC channels, or documentation for the product this collection automates. At a minimum, link to: -->

- [Ansible Collection overview](https://github.com/ansible-collections/overview)
- [Ansible User guide](https://docs.ansible.com/ansible/devel/user_guide/index.html)
- [Ansible Developer guide](https://docs.ansible.com/ansible/devel/dev_guide/index.html)
- [Ansible Collections Checklist](https://github.com/ansible-collections/overview/blob/main/collection_requirements.rst)
- [Ansible Community code of conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html)
- [The Bullhorn (the Ansible Contributor newsletter)](https://us19.campaign-archive.com/home/?u=56d874e027110e35dea0e03c1&id=d6635f5420)
- [News for Maintainers](https://github.com/ansible-collections/news-for-maintainers)

## Licensing

<!-- Include the appropriate license information here and a pointer to the full licensing details. If the collection contains modules migrated from the ansible/ansible repo, you must use the same license that existed in the ansible/ansible repo. See the GNU license example below. -->

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
