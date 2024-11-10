import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Xquic(Stack):
    NAME = "xquic"
    CUBIC = "cubic"
    BBR = "bbr"
    BBRV2 = "bbrv2"
    RENO = "reno"

    CC_NAME_MAP = {
        "cubic": "c",
        "bbr": "b",
        "bbrv2": "B",
        "reno": "r"
    }

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 server_path, client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_path = server_path
        self.client_path = client_path

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
            "cd {} &&".format(self.server_path),
            "timeout", duration_s,
            "./test_server -s 2000000000 -c {}".format(Xquic.CC_NAME_MAP[cc_algo]),
            "-C -p {}".format(port_no),
            "-o /dev/null > /dev/null 2>&1"
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "cd {} &&".format(self.client_path),
            "timeout", duration_s,
            "./test_client -d 0 -a {} -p {} -T -C".format(self.server_ip, port_no),
            "-o /dev/null > /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Xquic.CUBIC, Xquic.BBR, Xquic.BBRV2, Xquic.RENO]
