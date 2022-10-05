import subprocess
from utils.remote_cmd import get_remote_cmd, get_pkill_remote_cmd

class TCPDump:
    """
    Represents a tcpdump instance to capture outgoing packets from server
    """

    def __init__(self, server_hostname, server_ip, interface, output_file):
        self.server_hostname = server_hostname
        self.server_ip = server_ip
        self.interface = interface
        self.output_file = output_file

    def start(self):
        cmd = get_remote_cmd(self.server_hostname, self.get_start_cmd())
        self.proc = subprocess.Popen(cmd)

    def stop(self):
        pattern_to_kill = " ".join(self.get_start_cmd())
        subprocess.run(get_pkill_remote_cmd(self.server_hostname, pattern_to_kill), check=True)
        self.proc.wait()

    def get_start_cmd(self):
        return ["tcpdump", "-B", "8192", "-i", self.interface, "-s", "100", "-w", self.output_file]
