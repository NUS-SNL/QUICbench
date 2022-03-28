import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Tcp(Stack):
    NAME = "tcp"
    CUBIC = "cubic"
    BBR = "bbr"
    RENO = "reno"

    def __init__(self, server_ip, server_hostname):
        self.server_ip = server_ip
        self.server_hostname = server_hostname

    def run_remote_server(self, port_no, cc_algo, duration_s):
        cmd = self.run_server_cmd(port_no, cc_algo, duration_s)
        cmd = get_remote_cmd(self.server_hostname, cmd)
        return subprocess.Popen(cmd)

    def run_client(self, port_no, cc_algo, duration_s):
        cmd = self.run_client_cmd(port_no, cc_algo, duration_s)
        return subprocess.Popen(cmd)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            "timeout", duration_s,
            "iperf3", "-s", "-p", port_no, "-1", "-i", "60"
        ])

    def run_client_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            "iperf3", "-c", self.server_ip, "-p", port_no, "-C", cc_algo,
            "-t", duration_s, "-R", "-i", "60"
        ])

    @staticmethod
    def get_cc_algos():
        return [Tcp.CUBIC, Tcp.BBR, Tcp.RENO]
