import os
import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Mvfst(Stack):
    NAME = "mvfst"
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

    def run_remote_server_wlogs(self, port_no, cc_algo, duration_s, log_path):
        cmd = self.run_server_cmd_wlogs(port_no, cc_algo, duration_s, log_path)
        cmd = get_remote_cmd(self.server_hostname, cmd)
        return subprocess.Popen(cmd)

    def run_client(self, port_no, cc_algo, duration_s):
        cmd = self.run_client_cmd(port_no, duration_s)
        return subprocess.Popen(cmd)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            "timeout", duration_s,
            self.server_path, "-mode=server", "-host=0.0.0.0", "-pacing=true",
            "-port={}".format(port_no), "-congestion={}".format(cc_algo)
        ])

    def run_server_cmd_wlogs(self, port_no, cc_algo, duration_s, log_path):
        log_dir = os.path.dirname(log_path)
        return map(str, [
            "timeout", duration_s,
            self.server_path, "-mode=server", "-host=0.0.0.0", "-pacing=true",
            "-port={}".format(port_no), "-congestion={}".format(cc_algo),
            "-server_qlogger_path={};".format(log_dir),
            "mv {} {}".format(os.path.join(log_dir, "*.qlog"), log_path)
        ])        

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            self.client_path, "-mode=client", "-duration={}".format(duration_s),
            "-host={}".format(self.server_ip), "-port={}".format(port_no)
        ])

    @staticmethod
    def get_cc_algos():
        return [Mvfst.CUBIC, Mvfst.BBR, Mvfst.RENO]
