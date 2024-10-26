import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Haskell(Stack):
    NAME = "haskell"
    RENO = "reno"

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 server_path, server_cert_path, server_key_path,
                 server_static_file_dir, server_static_filename,
                 client_path, ca_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_path = server_path
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
        self.client_path = client_path
        self.ca_path = ca_path

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
            "{} --cert {}".format(self.server_path, self.server_cert_path),
            "-k {}".format(self.server_key_path),
            "-G {} ".format(cc_algo),
            "-p {}".format(port_no)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "timeout", duration_s,
            "{}".format(self.client_path),
            "-c {}".format(self.ca_path),
            "-D", # disables saving of the response
             "{} {} index.html".format(self.server_ip, port_no),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Picoquic.CUBIC, Picoquic.RENO, Picoquic.BBR, Picoquic.FAST]
