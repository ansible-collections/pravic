# CI

##  Pravic Collection

GitHub Actions are used to run the Continuous Integration for ansible-collections/pravic collection. The workflows used for the CI can be found [here](https://github.com/ansible-collections/pravic/tree/main/.github/workflows). These workflows include jobs to run the sanity tests, linters and changelog check. The following table lists the python and ansible versions against which these jobs are run.

| Jobs | Description | Python Versions | Ansible Versions |
| ------ |-------| ------ | -----------|
| changelog |Checks for the presence of Changelog fragments | 3.9 | devel |
| Linters | Runs `yamlint`, `black` and `flake8` on plugins and tests | 3.9 | devel |
| Sanity | Runs absible sanity checks | 3.9, 3.10 | Stable-2.14, Stable-2.15+ |
| Integration tests | Executes the integration test suites| 3.9 | devel |
