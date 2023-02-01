# Copyright: (c) 2023, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import traceback
from ansible.module_utils.common.text.converters import to_text


def module_fail_from_exception(module, exception):
    msg = to_text(exception)
    tb = "".join(
        traceback.format_exception(None, exception, exception.__traceback__)
    )
    return module.fail_json(msg=msg, exception=tb)


class CloudException(Exception):
    pass
