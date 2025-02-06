import subprocess
from utils.remote_cmd import get_remote_cmd_sudo
from flags import USE_CLIENT_NETEM

def delete_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface):
    cmd = (
        "sudo tc qdisc del dev {interface} handle ffff: ingress;"
        "sudo tc qdisc del dev {ingress_interface} root;"
        "sudo ip link set dev {ingress_interface} down;"
    ).format(interface=interface, ingress_interface=ingress_interface)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)

def delete_virtual_interface(server_hostname, server_pw_path, server_ip, interface, virtual_interface):
    cmd = (
        "sudo ip addr add dev {interface} {server_ip}/8;"
        "sudo ip addr flush dev {virtual_interface};"
        "sudo ip link del dev {virtual_interface};"
    ).format(interface=interface, virtual_interface=virtual_interface, server_ip=server_ip)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)    

def clear_netem(server_hostname, server_pw_path, server_ip, interface, ingress_interface, virtual_interface=None, client_interface=None):
    print("Clearing network emulation:")
    if USE_CLIENT_NETEM:
        print("USE_CLIENT_NETEM = True")
        if not client_interface:
            raise Exception("USE_CLIENT_NETEM set to True but client interface is None!")
        cmd = (
            "sudo tc qdisc del dev {client_interface} handle ffff: ingress;"
            "sudo tc qdisc del dev {ingress_interface} root;"
            "sudo ip link set dev ifb0 down;"
            "sudo tc qdisc del dev {client_interface} root;"
            "sudo tc qdisc show dev {client_interface}"
        ).format(client_interface=client_interface, ingress_interface=ingress_interface)
        subprocess.run(cmd, shell=True)
        # delete_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface)

    else:
        delete_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface)
        if virtual_interface:
            delete_virtual_interface(server_hostname, server_pw_path, server_ip, interface, virtual_interface)
        cmd = (
            "sudo tc qdisc del dev {} root;"
            "sudo tc qdisc show dev enp1s0f1"
        ).format(interface)
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)
