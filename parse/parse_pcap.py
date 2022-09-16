import os
import sys
import argparse
import json
import subprocess
import pandas as pd

sys.path.insert(1, os.path.join(sys.path[0], '..')) # allow importing from parent dir (repo)

from constants import *
from utils.exp_conf import get_stack_combi, get_port_nos_from_combi
from utils.files import write_to_csv


# constants for pcap headers
TIME = "_ws.col.Time"
RELATIVE_TIME = "frame.time_relative"
IP_IDENTIFIER = "ip.id"
IP_SRC = "ip.src"
IP_DST = "ip.dst"
FRAME_LEN = "frame.len"
UDP_SRCPORT = "udp.srcport"
UDP_DSTPORT = "udp.dstport"
UDP_CHECKSUM = "udp.checksum"
UDP_DATA = "data.data"
TCP_SRCPORT = "tcp.srcport"
TCP_DSTPORT = "tcp.dstport"
TCP_SEQNO = "tcp.seq_raw"
TCP_CHECKSUM = "tcp.checksum"
TCP_TIMESTAMP = "tcp.options.timestamp.tsecr"
TCP_TIMESTAMP_VAL = "tcp.options.timestamp.tsval"


def get_parse_pcap_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp_conf", "-e", help="path to experiment configuration", type=str)
    parser.add_argument("--general_conf", "-g", help="path to general configuration", type=str)
    parser.add_argument("--name", "-n", help="name of stack combination", type=str)
    parser.add_argument("--trial_dir", "-t", help="path to directory of trial results", type=str)
    return parser.parse_args()


def convert_pcap_to_csv(pcap_path, pcap_csv_path):
    cmd = "tshark -r {} -T fields -o \"gui.column.format:\\\"Time\\\",\\\"%Aut\\\"\" ".format(pcap_path)
    for field in [TIME, RELATIVE_TIME, IP_IDENTIFIER, IP_SRC, IP_DST, FRAME_LEN,
                  UDP_SRCPORT, UDP_DSTPORT, UDP_CHECKSUM, UDP_DATA, 
                  TCP_SRCPORT, TCP_DSTPORT, TCP_SEQNO, TCP_CHECKSUM, TCP_TIMESTAMP, TCP_TIMESTAMP_VAL]:
        cmd += "-e {} ".format(field)
    cmd += "-E header=y -E separator=, -E quote=d -E occurrence=f > {}".format(pcap_csv_path)
    subprocess.run(cmd, shell=True, check=True)


def obtain_packets_from_pcap(pcap_path, valid_port_nos, server_ip):
    pcap_csv_path = pcap_path + ".csv"
    convert_pcap_to_csv(pcap_path, pcap_csv_path)

    df = pd.read_csv(pcap_csv_path, dtype=str)
    df[RELATIVE_TIME] = df[RELATIVE_TIME].astype(dtype=float)
    df[FRAME_LEN] = df[FRAME_LEN].astype(dtype=float)
    df.fillna('', inplace=True)

    port_outgoing_packets_map = {}
    port_incoming_packets_map = {}
    for port_no in valid_port_nos:
        port_outgoing_packets_map[port_no] = df.loc[(df[IP_SRC] == server_ip) & ((df[UDP_SRCPORT] == port_no) | (df[TCP_SRCPORT] == port_no))]
        port_incoming_packets_map[port_no] = df.loc[(df[IP_DST] == server_ip) & ((df[UDP_DSTPORT] == port_no) | (df[TCP_DSTPORT] == port_no))]

    os.remove(pcap_csv_path) # delete csv file after use
    
    return port_outgoing_packets_map, port_incoming_packets_map


def get_moving_window_average_rates(packets_df, window_size_s):
    average_rates = []
    window_size_sum = 0
    window_start_pointer = 0
    window_start_time = packets_df.iloc[0][RELATIVE_TIME]

    for index, packet in packets_df.iterrows():
        time, packet_size = packet[RELATIVE_TIME], packet[FRAME_LEN]
        window_size_sum += packet_size
        if time - window_start_time > window_size_s:
            window_rate = window_size_sum / (time - window_start_time)
            window_rate_Mbps = round(window_rate * 8 / 1000000, 5)
            average_rates.append(
                [time, window_rate_Mbps]
            )
            window_size_sum -= packets_df.iloc[window_start_pointer][FRAME_LEN]
            window_start_pointer += 1
            window_start_time = packets_df.iloc[window_start_pointer][RELATIVE_TIME]

    return average_rates


def output_throughput_traces(port_no_packets_map, trial_dir, flow_duration_s, window_size_s):
    for port_no, packets_df in port_no_packets_map.items():
        average_rates = get_moving_window_average_rates(packets_df, window_size_s)
        
         # check for premature flow termination
        trace_duration_s = average_rates[-1][0] - average_rates[0][0]
        if trace_duration_s < flow_duration_s * 0.9 * TRUNCATE_TRACES_BY:
            raise RuntimeError("flow terminated prematurely.")
        else:
            # truncate flow duration
            average_rates = list(filter(lambda row : row[0] < flow_duration_s * TRUNCATE_TRACES_BY, average_rates))

        throughput_trace_path = os.path.join(trial_dir, port_no + THROUGHPUT_TRACE_SUFFIX)
        write_to_csv(throughput_trace_path, ["time (s)", "throughput (Mbps)"], average_rates)


def get_delay_trace(packets_df, veth_packets_df, flow_duration_s, window_size_s):
    def get_hash(pkt):
        return (pkt[IP_IDENTIFIER], pkt[UDP_CHECKSUM], pkt[UDP_DATA], pkt[TCP_SEQNO],
                pkt[TCP_CHECKSUM], pkt[TCP_TIMESTAMP], pkt[TCP_TIMESTAMP_VAL])
    def time_difference_ms(time1, time2):    
        def convert_time_to_s(time):
            h_m_s = time.replace(',', '.').split(':')
            multipliers = [3600, 60, 1]
            tot = 0
            for i in range(len(h_m_s)):
                tot += float(h_m_s[i]) * multipliers[i]
            return tot
        time1 = convert_time_to_s(time1)
        time2 = convert_time_to_s(time2)
        mod = 24 * 3600
        return round(((time1 - time2 + mod) % mod) * 1000, 5)

    veth_packets_hashmap = {}
    for index, veth_packet in veth_packets_df.iterrows():
        # in the tcpdump, some of the UDP packets doesn't have its data for some unknown reason,
        # and so we skip these packets as they cannot be uniquely identified
        if veth_packet[UDP_SRCPORT] and not veth_packet[UDP_DATA]:
            continue
        pkt_hash = get_hash(veth_packet)
        if pkt_hash in veth_packets_hashmap:
            raise RuntimeError("hash collision")
        veth_packets_hashmap[pkt_hash] = veth_packet[TIME]

    delay_trace = []
    delay_moving_window_trace = []
    window_size_sum = 0
    window_start_pointer = 0
    window_start_time = 0
    packets_hashset = set()
    
    for index, packet in packets_df.iterrows():
        if packet[RELATIVE_TIME] >= TRUNCATE_TRACES_BY * flow_duration_s: # truncate trace
            break
        if packet[UDP_SRCPORT] and not packet[UDP_DATA]:
            continue
        pkt_hash = get_hash(packet)
        if pkt_hash not in veth_packets_hashmap:
            continue
        if pkt_hash in packets_hashset:
            raise RuntimeError("hash collision")
        packets_hashset.add(pkt_hash)

        time = packet[RELATIVE_TIME]
        delay = time_difference_ms(packet[TIME], veth_packets_hashmap[pkt_hash])
        delay_trace.append((time, delay))

        window_size_sum += delay
        if time - window_start_time > window_size_s:
            avg_delay = round(window_size_sum / (len(delay_trace) - window_start_pointer), 5)
            delay_moving_window_trace.append([time, avg_delay])
            window_size_sum -= delay_trace[window_start_pointer][1]
            window_start_pointer += 1
            window_start_time = delay_trace[window_start_pointer][0]

    return delay_moving_window_trace


def output_delay_traces(port_no_packets_map, veth_port_no_packets_map, trial_dir, flow_duration_s, window_size_s, delay_to_sub):
    for port_no, packets_df in port_no_packets_map.items():
        veth_packets_df = veth_port_no_packets_map[port_no]
        delay_trace = get_delay_trace(packets_df, veth_packets_df, flow_duration_s, window_size_s)

        delay_trace = [[x[0], round(x[1] - delay_to_sub, 5)] for x in delay_trace] # subtract delay (account for netem delay)

        delay_trace_path = os.path.join(trial_dir, port_no + DELAY_TRACE_SUFFIX)
        write_to_csv(delay_trace_path, ["time (s)", "delay (ms)"], delay_trace)


def main():
    args = get_parse_pcap_args()
    with open(args.exp_conf) as f:
        exp_conf = json.load(f)
    with open(args.general_conf) as f:
        general_conf = json.load(f)        
    stack_combi = get_stack_combi(exp_conf, args.name)
    valid_port_nos = get_port_nos_from_combi(stack_combi)
    server_ip = general_conf["server_ip"]
    
    # obtain throughput traces
    interface_pcap_path = os.path.join(args.trial_dir, INTERFACE_PCAP_FILENAME)
    port_outgoing_packets_map, port_incoming_packets_map = obtain_packets_from_pcap(interface_pcap_path, valid_port_nos, server_ip)

    window_size_s = exp_conf["netem_conf"]["RTT_ms"] / 100 # 10 RTT
    output_throughput_traces(port_outgoing_packets_map, args.trial_dir, exp_conf["flow_duration_s"], window_size_s)

    # obtain delay traces
    veth_pcap_path = os.path.join(args.trial_dir, VETH_PCAP_FILENAME)
    if not os.path.exists(veth_pcap_path):
        return
    veth_port_outgoing_packets_map, veth_port_incoming_packets_map = obtain_packets_from_pcap(veth_pcap_path, valid_port_nos, server_ip)
    output_delay_traces(port_outgoing_packets_map, veth_port_outgoing_packets_map, args.trial_dir, 
        exp_conf["flow_duration_s"], window_size_s, exp_conf["netem_conf"]["RTT_ms"]/2)


if __name__ == "__main__":
    main()
