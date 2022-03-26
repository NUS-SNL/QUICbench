import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Msquic(Stack):
    NAME = "msquic"
    CUBIC = "cubic"

    def __init__(self, server_ip, server_hostname,
                 server_path, server_cert_path, server_key_path,
                 server_static_file_dir, server_static_filename,
                 client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_path = server_path
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
        self.client_path = client_path

    def run_remote_server(self, port_no, cc_algo, duration_s):
        cmd = self.run_server_cmd(port_no, cc_algo, duration_s)
        cmd = get_remote_cmd(self.server_hostname, cmd)
        return subprocess.Popen(cmd)

    def run_client(self, port_no, cc_algo, duration_s):
        cmd = self.run_client_cmd(port_no, duration_s)
        return subprocess.Popen(" ".join(cmd), shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            "timeout", duration_s,
            self.server_path, "-file:{}".format(self.server_cert_path), "-key:{}".format(self.server_key_path),
            "-root:{}".format(self.server_static_file_dir), "-listen:0.0.0.0", "-port:{}".format(port_no)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            self.client_path, "-test:D", "-timeout:{}".format(duration_s * 1000), "-custom:{}".format(self.server_ip),
            "-port:{}".format(port_no), "-urls:https://{}:{}/{}".format(self.server_ip, port_no, self.server_static_filename),
            "> /dev/null 2>&1"
        ])
