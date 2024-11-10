import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Neqo(Stack):
    NAME = "neqo"
    CUBIC = "cubic"
    RENO = "newreno"

    def __init__(self, server_ip, server_hostname, server_pw_path,
                 ld_library_path, server_path, server_db_path,
                 server_static_filename, client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.ld_library_path = ld_library_path
        self.server_path = server_path
        self.server_db_path = server_db_path
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
            "export LD_LIBRARY_PATH={} &&".format(self.ld_library_path),
            "timeout", duration_s,
            "{} --db {} --qns-test http3".format(self.server_path, self.server_db_path),
            "--cc {} 0.0.0.0:{}".format(cc_algo, port_no)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "export LD_LIBRARY_PATH={} &&".format(self.ld_library_path),
            "timeout", duration_s,
            "{} http://{}:{}/{}".format(self.client_path, self.server_ip, port_no, self.server_static_filename),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Neqo.CUBIC, Neqo.RENO]
