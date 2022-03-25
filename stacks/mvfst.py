import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Mvfst(Stack):
    CUBIC = "cubic"
    BBR = "bbr"
    RENO = "newreno"

    def __init__(self, server_ip, server_hostname, server_path, client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_path = server_path
        self.client_path = client_path

    def run_remote_server(self, port_no, cc_algo, duration_s):
        cmd = self.run_server_cmd(port_no, cc_algo, duration_s)
        cmd = get_remote_cmd(self.server_hostname, cmd)
        return subprocess.Popen(cmd)

    def run_client(self, port_no, duration_s):
        cmd = self.run_client_cmd(port_no, duration_s)
        return subprocess.Popen(cmd)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return [
            "timeout", duration_s,
            self.server_path, "-mode=server", "-host=0.0.0.0", "-pacing=true",
            "-port={}".format(port_no), "-congestion={}".format(cc_algo)
        ]

    def run_client_cmd(self, port_no, duration_s):
        return [
            self.client_path, "-mode=client", "-duration={}".format(duration_s),
            "-host={}".format(self.server_ip), "-port={}".format(port_no)
        ]
