import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Ngtcp2(Stack):
    NAME = "ngtcp2"
    CUBIC = "cubic"
    RENO = "reno"
    BBR = "bbr"

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
        newcmd = " ".join(cmd)
        return subprocess.Popen(newcmd, shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        # command from README at https://github.com/ngtcp2/ngtcp2 
        # $ examples/wsslserver [OPTIONS] <ADDR> <PORT> <PRIVATE_KEY_FILE> <CERTIFICATE_FILE>
        return map(str, [
            "timeout", duration_s,
            "{} 0.0.0.0".format(self.server_path),
            "{}".format(port_no),
            "{}".format(self.server_key_path),
            "{}".format(self.server_cert_path),
            "--cc {}".format(cc_algo),
            "-q", # quiet
            "-d {}".format(self.server_static_file_dir)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "timeout", duration_s,
            "{}".format(self.client_path),
            "{} {}".format(self.server_ip, port_no),
            "--no-quic-dump --no-http-dump",
            "--exit-on-all-streams-close",
             "https://{}/index.html".format(self.server_ip),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Ngtcp2.CUBIC, Ngtcp2.RENO, Ngtcp2.BBR]
