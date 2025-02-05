import os
import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Quiche(Stack):
    NAME = "quiche"
    CUBIC = "cubic"
    RENO = "reno"

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 server_cargo_path, server_path, server_cert_path, server_key_path,
                 server_static_file_dir, server_static_filename,
                 client_cargo_path, client_path, server_bin_path=None, client_bin_path=None):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_cargo_path = server_cargo_path
        self.server_path = server_path
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
        self.client_cargo_path = client_cargo_path
        self.client_path = client_path
        self.server_bin_path = server_bin_path
        self.client_bin_path = client_bin_path

    def run_remote_server(self, port_no, cc_algo, duration_s):
        cmd = self.run_server_cmd(port_no, cc_algo, duration_s)
        cmd = get_remote_cmd(self.server_hostname, cmd)
        print(" ".join(cmd))
        return subprocess.Popen(cmd)

    def run_remote_server_wlogs(self, port_no, cc_algo, duration_s, log_path):
        cmd = self.run_server_cmd_wlogs(port_no, cc_algo, duration_s, log_path)
        cmd = get_remote_cmd(self.server_hostname, cmd)
        return subprocess.Popen(cmd)

    def run_client(self, port_no, cc_algo, duration_s):
        cmd = self.run_client_cmd(port_no, duration_s)
        cmd = " ".join(cmd)
        print(cmd)
        return subprocess.Popen(cmd, shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        if self.server_bin_path:
             return map(str, [
                "timeout", duration_s,
                "{}".format(self.server_bin_path),
                "--cert {}".format(self.server_cert_path), "--key {}".format(self.server_key_path),
                "--listen 0.0.0.0:{}".format(port_no), "--root {}".format(self.server_static_file_dir),
                "--index {}".format(self.server_static_filename), "--cc-algorithm {}".format(cc_algo)
            ]) 
        return map(str, [
            "timeout", duration_s,
            "{} run --manifest-path={} --bin quiche-server --".format(self.server_cargo_path, self.server_path),
            "--cert {}".format(self.server_cert_path), "--key {}".format(self.server_key_path),
            "--listen 0.0.0.0:{}".format(port_no), "--root {}".format(self.server_static_file_dir),
            "--index {}".format(self.server_static_filename), "--cc-algorithm {}".format(cc_algo)
        ])

    def run_server_cmd_wlogs(self, port_no, cc_algo, duration_s, log_path):
        log_dir = os.path.dirname(log_path)
        if self.server_bin_path:
            return map(str, [
                "export QLOGDIR={};".format(log_dir),
                "timeout", duration_s,
                "{}".format(self.server_bin_path),
                "--cert {}".format(self.server_cert_path), "--key {}".format(self.server_key_path),
                "--listen 0.0.0.0:{}".format(port_no), "--root {}".format(self.server_static_file_dir),
                "--index {}".format(self.server_static_filename), "--cc-algorithm {}".format(cc_algo), ";",
                "mv {} {}".format(os.path.join(log_dir, "*.sqlog"), log_path)
            ]) 
        return map(str, [
            "export QLOGDIR={};".format(log_dir),
            "timeout", duration_s,
            "{} run --manifest-path={} --bin quiche-server --".format(self.server_cargo_path, self.server_path),
            "--cert {}".format(self.server_cert_path), "--key {}".format(self.server_key_path),
            "--listen 0.0.0.0:{}".format(port_no), "--root {}".format(self.server_static_file_dir),
            "--index {}".format(self.server_static_filename), "--cc-algorithm {}".format(cc_algo), ";",
            "mv {} {}".format(os.path.join(log_dir, "*.sqlog"), log_path)
        ])        

    def run_client_cmd(self, port_no, duration_s):
        if self.client_bin_path:
            return map(str, [
                "timeout", duration_s,
                "{}".format(self.client_bin_path),
                "--no-verify", "https://{}:{}".format(self.server_ip, port_no),
                "> /dev/null 2>&1"
            ])
        return map(str, [
            "timeout", duration_s,
            "{} run --manifest-path={} --bin quiche-client --".format(self.client_cargo_path, self.client_path),
            "--no-verify", "https://{}:{}".format(self.server_ip, port_no),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Quiche.CUBIC, Quiche.RENO]
