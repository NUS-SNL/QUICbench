import subprocess
from operator import itemgetter
from utils.remote_cmd import get_remote_cmd_sudo
from flags import USE_CLIENT_NETEM

# for introducing delay for ingress packets
def add_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface):
    cmd = (
        "sudo modprobe ifb;"
        "sudo ip link set dev {ingress_interface} up;"
        "sudo tc qdisc add dev {interface} ingress;"
        "sudo tc filter add dev {interface} parent ffff: protocol ip u32 match u32 0 0 flowid 1:1 action mirred egress redirect dev {ingress_interface};"
    ).format(interface=interface, ingress_interface=ingress_interface)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)

# for capturing packets before qdisc egress to measure queuing delay/packets dropped by buffer
def add_virtual_interface(server_hostname, server_pw_path, server_ip, interface, virtual_interface):
    cmd = (
        "sudo brctl addbr {virtual_interface};"
        "sudo brctl addif {virtual_interface} {interface};"
        "sudo ip link set dev {virtual_interface} up;"
        "sudo ip addr add dev {virtual_interface} {server_ip}/8;"
        "sudo ip addr flush dev {interface};"
    ).format(interface=interface, virtual_interface=virtual_interface, server_ip=server_ip)
    subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)

def set_netem(server_hostname, server_pw_path, server_ip, interface, ingress_interface, netem_conf, virtual_interface=None, client_interface=None):
    print("Setting network emulation:")
    if USE_CLIENT_NETEM:
        print("USE_CLIENT_NETEM = True")
        if not client_interface:
            raise Exception("USE_CLIENT_NETEM set to True but client interface is None!")
        subprocess.run("sudo tc qdisc del dev {} root".format(client_interface), shell=True)
        subprocess.run("sudo tc qdisc del dev {} ingress".format(client_interface), shell=True)

        RTT_ms, bandwidth_Mbps, buffer_bdp, background_delay_ms, added_delay_ms =\
            itemgetter("RTT_ms", "bandwidth_Mbps", "buffer_bdp", "background_delay_ms", "added_delay_ms")(netem_conf) 
        
        # Separate these so the buffer is made using the target delay of RTT_ms,
        # but we set the netem using the added delay
        if RTT_ms != background_delay_ms + added_delay_ms:
            raise Exception(f"RTT_ms not equal to sum of background and added delay: {RTT_ms} != {background_delay_ms} + {added_delay_ms}")

        # add_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface)


        buffer_bytes = int(RTT_ms * bandwidth_Mbps * 1000 / 8 * buffer_bdp)
        bandwidth_Kbps = bandwidth_Mbps * 1000
        # https://unix.stackexchange.com/questions/100785/bucket-size-in-tbf
        burst_bytes = int(bandwidth_Mbps * 1000000 / 250 / 8) 
        # 9 Nov 2024: multiplied by 1.5 because a lower burst has issues when there are too many packets for tcp
        burst_bytes = int(1.5 * burst_bytes)

        cmd = (
            "sudo modprobe ifb;"
            "sudo ip link set {ingress_interface} up;"
            "sudo tc qdisc add dev {client_interface} ingress;"
            "sudo tc filter add dev {client_interface} parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev {ingress_interface};"
            "sudo tc qdisc add dev {ingress_interface} root handle 1:0 netem delay {added_delay_ms}ms limit 12500;"
            "sudo tc qdisc add dev {ingress_interface} parent 1:1 handle 10: tbf rate {bandwidth_Kbps}kbit limit {buffer_bytes} burst {burst_bytes};"
            "sudo tc qdisc show dev {ingress_interface}"
        ).format(interface=interface, ingress_interface=ingress_interface,
            added_delay_ms=added_delay_ms, bandwidth_Kbps=bandwidth_Kbps, buffer_bytes=buffer_bytes, burst_bytes=burst_bytes, client_interface=client_interface)
        # print(cmd)
        subprocess.run(cmd, shell=True)


    else:
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo tc qdisc del dev {} root".format(interface)), shell=True)

        RTT_ms, bandwidth_Mbps, buffer_bdp = itemgetter("RTT_ms", "bandwidth_Mbps", "buffer_bdp")(netem_conf)

        if virtual_interface:
            add_virtual_interface(server_hostname, server_pw_path, server_ip, interface, virtual_interface)

        add_ingress_interface(server_hostname, server_pw_path, interface, ingress_interface)

        delay_ms = RTT_ms // 2
        buffer_bytes = int(RTT_ms * bandwidth_Mbps * 1000 / 8 * buffer_bdp)
        bandwidth_Kbps = bandwidth_Mbps * 1000
        # https://unix.stackexchange.com/questions/100785/bucket-size-in-tbf
        burst_bytes = int(bandwidth_Mbps * 1000000 / 250 / 8) 
        # 9 Nov 2024: multiplied by 1.5 because a lower burst has issues when there are too many packets for tcp
        burst_bytes = int(1.5 * burst_bytes)
        cmd = (
            "sudo tc qdisc add dev {interface} root handle 1:0 netem delay {delay_ms}ms limit 12500;"
            "sudo tc qdisc add dev {interface} parent 1:1 handle 10: tbf rate {bandwidth_Kbps}kbit limit {buffer_bytes} burst {burst_bytes};"
            "sudo tc qdisc add dev {ingress_interface} root netem delay {delay_ms}ms;"
            "sudo tc qdisc show dev {interface} && sudo tc qdisc show dev {ingress_interface}"
        ).format(interface=interface, ingress_interface=ingress_interface,
            delay_ms=delay_ms, bandwidth_Kbps=bandwidth_Kbps, buffer_bytes=buffer_bytes, burst_bytes=burst_bytes)
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, cmd), shell=True)
