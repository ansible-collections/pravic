import subprocess
import os
from abc import abstractmethod

from ansible.plugins.connection import ConnectionBase
from ansible.utils.display import Display
from ansible.plugins.loader import connection_loader
from ansible.module_utils.six import text_type, binary_type
from ansible.parsing.yaml.loader import AnsibleLoader


class CloudConnectionBase(ConnectionBase):
    """Local kubernetes connection plugin"""

    def __init__(self, play_context, new_stdin, *args, **kwargs):
        super(CloudConnectionBase, self).__init__(play_context, new_stdin, *args, **kwargs)

        self._client = None
        self._display = Display()

        self._local = connection_loader.get("local", play_context, "/dev/null")
        self._local.set_options()

    def create_environment(self):
        doc_yaml = AnsibleLoader(self.documentation()).get_single_data()
        env = os.environ
        for key in doc_yaml.get("options"):
            if self.get_option(key):
                env.update({f"{self.cloud_provider().upper()}_CLIENT_{key.upper()}": self.get_option(key)})
        return env

    @abstractmethod
    def cloud_provider(self):
        pass

    @abstractmethod
    def documentation(self):
        pass

    @abstractmethod
    def connection_name(self):
        pass

    def exec_command(self, cmd, in_data=None, sudoable=True):
        """Run a command in the container"""
        super(CloudConnectionBase, self).exec_command(cmd, in_data=in_data, sudoable=sudoable)

        self._display.vvv(
            "EXEC %s" % (cmd,), host=self._play_context.remote_addr
        )

        env = self.create_environment()
        env.update({'cloud_provider': self.cloud_provider()})

        p = subprocess.Popen(
            cmd,
            shell=isinstance(cmd, (text_type, binary_type)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        stdout, stderr = p.communicate(in_data)
        return (p.returncode, stdout, stderr)

    def put_file(self, in_path, out_path):
        """Transfer a file from local to remote"""
        return self._local.put_file(in_path, out_path)

    def fetch_file(self, in_path, out_path):
        """Fetch a file from remote to local"""
        return self._local.fetch_file(in_path, out_path)

    @property
    def transport(self):
        return self.connection_name

    def _connect(self):
        """Connect : Nothing to do"""
        super(CloudConnectionBase, self)._connect()
        if not self._connected:
            self._display.vvv(
                "ESTABLISH {0} CONNECTION".format(self.transport),
                host=self._play_context.remote_addr,
            )
            self._connected = True

    def close(self) -> None:
        """Terminate the connection. Nothing to do"""
        super(CloudConnectionBase, self).close()
        self._connected = False
