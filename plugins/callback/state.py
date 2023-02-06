# (C) 2022 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
    name: state
    type: aggregate
    short_description: gathers resources state
    description:
      - Ansible callback plugin for collecting the resources state
    requirements:
      - whitelisting in configuration.
'''

import json
from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_NAME = "pravic.pravic.state"
    CALLBACK_TYPE = "aggregate"

    def __init__(self, display=None, options=None):
        super(CallbackModule, self).__init__(display=display, options=options)
        self.state_file = None

    def v2_runner_on_start(self, host, task):
        vm = task.get_variable_manager()
        self.state_file = vm.get_vars(host=host, task=task).get("state_file")

    def v2_runner_on_ok(self, result):
        try:
            with open(self.state_file) as fp:
                state = json.load(fp)
        except Exception:
            state = {}
        state.update(result._result.get("resources", {}))
        with open(self.state_file, "w") as fp:
            json.dump(state, fp, indent=True)
