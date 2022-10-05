import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class QuicGo(Stack):
    NAME = "quicgo"
    CUBIC = "cubic"
    RENO = "reno"

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 go_path, cubic_server_path, reno_server_path, server_static_file_dir,
                 server_static_filename, client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.go_path = go_path
        self.server_paths = {
            QuicGo.CUBIC: cubic_server_path,
            QuicGo.RENO: reno_server_path,
        }
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
            "cd {} &&".format(self.server_paths[cc_algo]),
            "timeout", duration_s,
            "{} run main.go -www {}".format(self.go_path, self.server_static_file_dir),
            "-bind 0.0.0.0:{}".format(port_no)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "cd {} &&".format(self.client_path),
            "timeout", duration_s,
            "{} run main.go -insecure".format(self.go_path),
            "https://{}:{}/{}".format(self.server_ip, port_no, self.server_static_filename),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [QuicGo.CUBIC, QuicGo.RENO]
