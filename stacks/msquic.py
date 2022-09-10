import subprocess
from utils.remote_cmd import get_remote_cmd
from stacks.stack import Stack

class Msquic(Stack):
    NAME = "msquic"
    CUBIC = "cubic"

    MSQUIC_LOGS_TMPDIR = "/tmp/msquic_logs/"
    MSQUIC_LOGS_TMPFILE = "/tmp/msquic.babel.txt"

    def __init__(self, server_ip, server_hostname,
                 server_path, server_cert_path, server_key_path,
                 server_static_file_dir, server_static_filename,
                 client_path, clog_sidecar_path, clog2text_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_path = server_path
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
        self.client_path = client_path
        self.clog_sidecar_path = clog_sidecar_path
        self.clog2text_path = clog2text_path

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
        return subprocess.Popen(" ".join(cmd), shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            "timeout", duration_s,
            self.server_path, "-file:{}".format(self.server_cert_path), "-key:{}".format(self.server_key_path),
            "-root:{}".format(self.server_static_file_dir), "-listen:0.0.0.0", "-port:{}".format(port_no)
        ])

    def run_server_cmd_wlogs(self, port_no, cc_algo, duration_s, log_path):
        return map(str, [
            "mkdir {};".format(Msquic.MSQUIC_LOGS_TMPDIR),
            "lttng destroy --all;",
            "lttng create msquic -o={};".format(Msquic.MSQUIC_LOGS_TMPDIR),
            "lttng enable-event --userspace CLOG_*;",
            "lttng add-context --userspace --type=vpid --type=vtid;",
            "lttng start;",
            "timeout", duration_s,
            self.server_path, "-file:{}".format(self.server_cert_path), "-key:{}".format(self.server_key_path),
            "-root:{}".format(self.server_static_file_dir), "-listen:0.0.0.0", "-port:{}".format(port_no), ";",
            "lttng stop msquic;",
            "babeltrace --names all {}* > {};".format(Msquic.MSQUIC_LOGS_TMPDIR, Msquic.MSQUIC_LOGS_TMPFILE),
            "{} -i {} -s {} -o {} --showTimestamp --showCpuInfo &> /dev/null;".format(
                self.clog2text_path,
                Msquic.MSQUIC_LOGS_TMPFILE,
                self.clog_sidecar_path,
                log_path
            ),
            "rm {};".format(Msquic.MSQUIC_LOGS_TMPFILE),
            "rm -rf {};".format(Msquic.MSQUIC_LOGS_TMPDIR),
            "lttng destroy --all;",
        ])

    def run_client_cmd(self, port_no, duration_s):
        return map(str, [
            self.client_path, "-test:D", "-timeout:{}".format(duration_s * 1000), "-custom:{}".format(self.server_ip),
            "-port:{}".format(port_no), "-urls:https://{}:{}/{}".format(self.server_ip, port_no, self.server_static_filename),
            "> /dev/null 2>&1"
        ])

    @staticmethod
    def get_cc_algos():
        return [Msquic.CUBIC]
