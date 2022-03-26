import subprocess
from operator import itemgetter
from utils.remote_cmd import get_remote_cmd_sudo

# for introducing delay for ingress packets
def add_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface):
    cmd = (
        "sudo modprobe ifb;"
        "sudo ip link set dev {ingress_interface} up;"
        "sudo tc qdisc add dev {interface} ingress;"
        "sudo tc filter add dev {interface} parent ffff: protocol ip u32 match u32 0 0 flowid 1:1 action mirred egress redirect dev {ingress_interface};"
    ).format(interface=interface, ingress_interface=ingress_interface)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)

def set_netem(server_hostname, server_pw_path, interface, ingress_interface, netem_conf):
    print("Setting network emulation:")
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo tc qdisc del dev {} root".format(interface)), shell=True)
    
    add_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface)

    RTT_ms, bandwidth_Mbps, buffer_bdp = itemgetter("RTT_ms", "bandwidth_Mbps", "buffer_bdp")(netem_conf)
    delay_ms = RTT_ms / 2
    buffer_bytes = int(RTT_ms * bandwidth_Mbps * 1000 / 8)
    cmd = (
        "sudo tc qdisc add dev {interface} root handle 1:0 netem delay {delay_ms}ms rate {bandwidth_Mbps}Mbit limit 12500;"
        "sudo tc qdisc add dev {interface} parent 1:1 handle 10: bfifo limit {buffer_bytes};"
        "sudo tc qdisc add dev {ingress_interface} root netem delay {delay_ms}ms;"
        "sudo tc qdisc show dev {interface} && sudo tc qdisc show dev {ingress_interface}"
    ).format(interface=interface, ingress_interface=ingress_interface, delay_ms=delay_ms, bandwidth_Mbps=bandwidth_Mbps, buffer_bytes=buffer_bytes)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)
