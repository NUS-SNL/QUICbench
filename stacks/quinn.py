import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Quinn(Stack):
    NAME = "quinn"
    CUBIC = "cubic"
    RENO = "reno"
    NUM_BYTES_TO_TRANSFER = 2000000000 # 2GB

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
        newcmd = " ".join(cmd)
        return subprocess.Popen(newcmd, shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            "timeout", duration_s,
            "{} run --manifest-path={} --release --bin perf_server --".format(self.server_cargo_path, self.server_paths[cc_algo]),
            "--listen 0.0.0.0:{}".format(port_no)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "{} run --manifest-path={} --release --bin perf_client --".format(self.client_cargo_path, self.client_path),
            "--download-size {} --duration {} --interval {}".format(Quinn.NUM_BYTES_TO_TRANSFER, duration_s, duration_s),
            "{}:{}".format(self.server_ip, port_no)
        ])

    @staticmethod
    def get_cc_algos():
        return [Quinn.CUBIC, Quinn.RENO]
