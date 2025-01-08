import os
import subprocess
from utils.remote_cmd import get_remote_cmd, get_remote_cmd_sudo, get_scp_file_to_remote_cmd
from stacks.stack import Stack
import re

class Nginx(Stack):
    NAME = "nginx"
    RENO = "newreno"

    def __init__(self, server_ip, server_hostname, server_pw_path, server_path, server_cert_path, server_key_path,
                 server_static_file_dir, server_static_filename, client_path, ca_path, nginx_conf_path):
        self.server_ip = server_ip
        self.server_hostname = server_hostname
        self.server_pw_path = server_pw_path
        self.server_path = server_path
        self.server_cert_path = server_cert_path
        self.server_key_path = server_key_path
        self.server_static_file_dir = server_static_file_dir
        self.server_static_filename = server_static_filename
        self.client_path = client_path
        self.ca_path = ca_path
        self.nginx_conf_path = nginx_conf_path
    
    def update_nginx_config(self, port_no):
        with open(self.nginx_conf_path, 'r') as file:
            config = file.read()

        # Update SSL certificate paths
        config = re.sub(r'ssl_certificate\s+.*;', f'ssl_certificate {self.server_cert_path};', config)
        config = re.sub(r'ssl_certificate_key\s+.*;', f'ssl_certificate_key {self.server_key_path};', config)
        config = re.sub(r'ssl_trusted_certificate\s+.*;', f'ssl_trusted_certificate {self.ca_path};', config)
        
        # Update static file directory and index
        config = re.sub(r'root\s+.*;', f'root {self.server_static_file_dir};', config)
        config = re.sub(r'index\s+.*;', f'index {self.server_static_filename};', config)
        
        # Update server port
        listen_port_pattern = r'listen\s+\[::\]:\d+\s+quic;'
        config = re.sub(r'listen\s+\d+\s+quic;', f'listen {port_no} quic;', config)
        config = re.sub(listen_port_pattern, f'listen [::]:{port_no} quic;', config)
        
        # Update Alt-Svc port advertisement
        config = re.sub(r'add_header\s+Alt-Svc\s+.*;', f'add_header Alt-Svc \'h3=":{port_no}"; ma=86400\';', config)

        with open(self.nginx_conf_path, 'w') as file:
            file.write(config)
        cmd = get_scp_file_to_remote_cmd(self.server_hostname,self.nginx_conf_path,self.nginx_conf_path )
        subprocess.run(cmd)
        print(f"NGINX configuration updated with port {port_no} and new paths.")


    def run_remote_server(self, port_no, cc_algo, duration_s):
        print("STARTING REMOTE")
        cmd = self.run_server_cmd(port_no, cc_algo, duration_s)
        # nginx requires us to update the config file separately before running
        self.update_nginx_config(port_no)
        cmd = " ".join(cmd)
        cmd = get_remote_cmd_sudo(self.server_hostname, self.server_pw_path, cmd)
        print(cmd)
        return subprocess.Popen(cmd, shell=True)
    
    def run_client(self, port_no, cc_algo, duration_s):
        cmd = self.run_client_cmd(port_no, duration_s)
        cmd = " ".join(cmd)
        print(cmd)
        return subprocess.Popen(cmd, shell=True)

    def run_server_cmd(self, port_no, cc_algo, duration_s):
        return map(str, [
            f"{self.server_path}", "-c", f"{self.nginx_conf_path}",
            "&", "sleep", duration_s, "&&", "sudo",
            f"{self.server_path}", "-s", "stop"
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
        return [Nginx.RENO]
