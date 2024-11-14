import subprocess
from utils.remote_cmd import get_remote_cmd, get_pkill_remote_cmd, get_pkill_cmd, get_remote_cmd_sudo, get_remote_cmd_sudo_array

class TCPDump:
    """
    Represents a tcpdump instance to capture outgoing packets from server
    """

    def __init__(self, server_hostname, server_ip, interface, output_file, is_remote, server_pw_path=None):
        self.server_hostname = server_hostname
        self.server_ip = server_ip
        self.interface = interface
        self.output_file = output_file
        self.is_remote = is_remote
        self.server_pw_path = server_pw_path

    def start(self):
        if self.is_remote:
            cmd = get_remote_cmd_sudo(self.server_hostname, self.server_pw_path, " ".join(self.get_start_cmd()))
            self.proc = subprocess.Popen(cmd, shell=True)
            
        else:
            cmd = "sudo " + " ".join(self.get_start_cmd())
            print(cmd)
            self.proc = subprocess.Popen(cmd, shell=True)
        

    def stop(self):
        if self.is_remote:
            cmd = get_remote_cmd_sudo(self.server_hostname, self.server_pw_path,"pkill tcpdump")
            print(cmd)
            
            subprocess.run(cmd, check=True, shell=True)
        else:
            subprocess.run(["sudo","/usr/bin/pkill","tcpdump"])
        self.proc.wait()

    def get_start_cmd(self):
        return ["tcpdump", "-B", "8192", "-i", self.interface, "-s", "100", "-w", self.output_file]
