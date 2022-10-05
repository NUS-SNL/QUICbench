import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Quinn(Stack):
    NAME = "quinn"
    CUBIC = "cubic"
    RENO = "reno"

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 server_cargo_path, cubic_server_path, reno_server_path,
                 server_cert_path, server_key_path,
                 server_static_file_dir, server_static_filename,
                 client_cargo_path, client_path,
                 ca_path, ca_hostname):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_cargo_path = server_cargo_path
        self.server_paths = {
            Quinn.CUBIC: cubic_server_path,
            Quinn.RENO: reno_server_path,
        }
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
        self.client_cargo_path = client_cargo_path
        self.client_path = client_path
        self.ca_path = ca_path
        self.ca_hostname = ca_hostname

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
            "{} run --manifest-path={} --example server --".format(self.server_cargo_path, self.server_paths[cc_algo]),
            "--cert {} --key {}".format(self.server_cert_path, self.server_key_path),
            "--listen 0.0.0.0:{} {}".format(port_no, self.server_static_file_dir)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "timeout", duration_s,
            "{} run --manifest-path={} --example client --".format(self.client_cargo_path, self.client_path),
            "--ca {} --host {}".format(self.ca_path, self.ca_hostname),
            "https://{}:{}/{}".format(self.server_ip, port_no, self.server_static_filename),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Quinn.CUBIC, Quinn.RENO]
