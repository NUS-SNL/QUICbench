import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

ENABLE_LOOP = True

class Aioquic(Stack):
    NAME = "aioquic"
    CUBIC = "cubic"
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
        newcmd = " ".join(cmd)
        print(newcmd)
        return subprocess.Popen(newcmd, shell=True)

    def run_client(self, port_no, cc_algo, duration_s):
        cmd = self.run_client_cmd(port_no, duration_s)
        # for some reason passing in " ".join(cmd) directly into subprocess.Popen does not work...
        # so we save it to a variable first
        newcmd = " ".join(cmd)
        print(newcmd)
        return subprocess.Popen(newcmd, shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        # configs taken from https://github.com/aiortc/aioquic/blob/1.2.0/examples/http3_server.py
        return map(str, [
            # necessary to export STATIC_ROOT as an env var for aioquic
            "\"export STATIC_ROOT={} &&".format(self.server_static_file_dir), 
            "timeout", duration_s,
            "python3 {} --certificate {}".format(self.server_path, self.server_cert_path),
            "--private-key {}".format(self.server_key_path),
            "--congestion-control-algorithm {} -v".format(cc_algo),
            "--host 0.0.0.0 --port {}\"".format(port_no)
        ])

    def run_client_cmd(self, port_no, duration_s):

        if ENABLE_LOOP:
            return map(str, [
                "/home/quic/quic_experiments/QUIC-bench/timeout_loop.sh", "-t", duration_s,
                "python3",
                self.client_path,
                "--insecure",
                "-v",
                "--ca-certs", self.ca_path,
                "--zero-rtt",
                "https://{}:{}/{}".format(self.server_ip, port_no, self.server_static_filename),
                "> /dev/null 2>&1"
            ])

        return map(str, [
            "timeout", duration_s,
            "python3",
            self.client_path,
            "--insecure",
            "-v",
            "--ca-certs", self.ca_path,
            "--zero-rtt",
            "https://{}:{}/{}".format(self.server_ip, port_no, self.server_static_filename),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Aioquic.CUBIC, Aioquic.RENO]


class AioquicLoop(Aioquic):
    NAME = "aioquic-loop"
