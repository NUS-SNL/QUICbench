import subprocess, time
from utils.remote_cmd import get_remote_cmd

def test_rtt(server_ip):
    subprocess.run(["ping", "-c", "3", server_ip])

def test_bandwidth(server_hostname, server_ip):
    p = subprocess.Popen(
        get_remote_cmd(server_hostname, ["iperf3", "-s", "-1"])
    )
    time.sleep(1)
    subprocess.run(["iperf3", "-c", server_ip, "-R", "-t", "6"])
    p.wait()
