import subprocess
from utils.remote_cmd import get_remote_cmd_sudo

def delete_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface):
    cmd = (
        "sudo tc qdisc del dev {interface} handle ffff: ingress;"
        "sudo tc qdisc del dev {ingress_interface} root;"
        "sudo ip link set dev {ingress_interface} down;"
    ).format(interface=interface, ingress_interface=ingress_interface)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)

def clear_netem(server_hostname, server_pw_path, interface, ingress_interface):
    print("Clearing network emulation:")
    delete_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface)
    cmd = (
        "sudo tc qdisc del dev {} root;"
        "sudo tc qdisc show dev enp1s0f1"
    ).format(interface)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)
