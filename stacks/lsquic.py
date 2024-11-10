import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Lsquic(Stack):
    NAME = "lsquic"
    CUBIC = "cubic"
    BBR = "bbr"

    # https://github.com/litespeedtech/lsquic/blob/master/include/lsquic.h
    CC_NAME_NO_MAP = {
        "cubic": "1",
        "bbr": "2",
    }

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 server_path, server_cert_path, server_key_path,
                 server_static_file_dir, server_static_filename,
                 client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_path = server_path
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
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
            "timeout", duration_s,
            "{} -c www.lsquic.com,{},{}".format(self.server_path, self.server_cert_path, self.server_key_path),
            "-r {} -p {}".format(self.server_static_file_dir, self.server_static_filename),
            "-s 0.0.0.0:{} -o cc_algo={}".format(port_no, Lsquic.CC_NAME_NO_MAP[cc_algo])
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "timeout", duration_s,
            "{} -p {}".format(self.client_path, self.server_static_filename),
            "-s {}:{}".format(self.server_ip, port_no),
            "-H www.lsquic.com -K"
        ])

    @staticmethod
    def get_cc_algos():
        return [Lsquic.CUBIC, Lsquic.BBR]
