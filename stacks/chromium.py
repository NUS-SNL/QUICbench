import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Chromium(Stack):
    NAME = "chromium"
    CUBIC = "cubic"
    BBR = "bbr"
    BBRV2 = "bbrv2"
    NUM_BYTES_TO_TRANSFER = 2000000000 # 2GB

    def __init__(self, server_ip, server_hostname, cubic_server_path, 
                 bbr_server_path, bbrv2_server_path, server_cert_path, 
                 server_key_path, client_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_paths = {
            Chromium.CUBIC: cubic_server_path,
            Chromium.BBR: bbr_server_path,
            Chromium.BBRV2: bbrv2_server_path,
        }
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
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
            self.server_paths[cc_algo], "--certificate_file={}".format(self.server_cert_path),
            "--key_file={}".format(self.server_key_path), "--port={}".format(port_no),
            "--quic_ietf_draft=true", "--generate_dynamic_responses=true"
        ])

    def run_server_cmd_wlogs(self, port_no, cc_algo, duration_s, log_path):
        return map(str, [
            "timeout", duration_s,
            self.server_paths[cc_algo], "--certificate_file={}".format(self.server_cert_path),
            "--key_file={}".format(self.server_key_path), "--port={}".format(port_no),
            "--quic_ietf_draft=true", "--generate_dynamic_responses=true", "--v=1",
            "2> {}".format(log_path)
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            "timeout", duration_s,
            self.client_path, "--host={}".format(self.server_ip), "--port={}".format(port_no),
            "--disable_certificate_verification", "--quic_ietf_draft=true", "--num_requests=1",
            "--drop_response_body=true", "https://{}/{}".format(self.server_ip, Chromium.NUM_BYTES_TO_TRANSFER)
        ])

    @staticmethod
    def get_cc_algos():
        return [Chromium.CUBIC, Chromium.BBR, Chromium.BBRV2]
