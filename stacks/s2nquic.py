import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class S2nQuic(Stack):
    NAME = "s2nquic"
    CUBIC = "cubic"
    NUM_BYTES_TO_TRANSFER = 2000000000 # 2GB

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 server_path, server_static_file_dir, server_static_filename,
                 client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_path = server_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
        self.client_path = client_path

    def run_remote_server(self, port_no, cc_algo, duration_s):
        # there's only CUBIC for s2n quic
        if cc_algo != S2nQuic.CUBIC:
            raise ValueError("{} is not a valid cc_algo for quicgo".format(cc_algo))

        cmd = self.run_server_cmd(port_no, cc_algo, duration_s)
        cmd = get_remote_cmd(self.server_hostname, cmd)
        return subprocess.Popen(cmd)

    def run_client(self, port_no, cc_algo, duration_s):
        # there's only CUBIC for s2n quic
        if cc_algo != S2nQuic.CUBIC:
            raise ValueError("{} is not a valid cc_algo for quicgo".format(cc_algo))

        cmd = self.run_client_cmd(port_no, duration_s)
        return subprocess.Popen(" ".join(cmd), shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            "timeout", duration_s,
            "{} perf server".format(self.server_path),
            "--ip 0.0.0.0 --port {}".format(port_no),
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "timeout", duration_s,
            "{} perf client".format(self.client_path),
            "--ip {} --port {}".format(self.server_ip, port_no),
            "--receive {}".format(NUM_BYTES_TO_TRANSFER),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [S2nQuic.CUBIC]
