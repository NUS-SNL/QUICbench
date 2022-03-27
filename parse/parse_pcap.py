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
FRAME_LEN = "frame.len"
UDP_SRCPORT = "udp.srcport"
UDP_CHECKSUM = "udp.checksum"
UDP_DATA = "data.data"
TCP_SRCPORT = "tcp.srcport"
TCP_SEQNO = "tcp.seq_raw"
TCP_CHECKSUM = "tcp.checksum"
TCP_TIMESTAMP = "tcp.options.timestamp.tsecr"
TCP_TIMESTAMP_VAL = "tcp.options.timestamp.tsval"


def get_parse_pcap_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp_conf", "-e", help="path to experiment configuration", type=str)
    parser.add_argument("--name", "-n", help="name of stack combination", type=str)
    parser.add_argument("--trial_dir", "-t", help="path to directory of trial results", type=str)
    return parser.parse_args()


def convert_pcap_to_csv(pcap_path, pcap_csv_path):
    cmd = "tshark -r {} -T fields -o \"gui.column.format:\\\"Time\\\",\\\"%Aut\\\"\" ".format(pcap_path)
    for field in [TIME, RELATIVE_TIME, IP_IDENTIFIER, FRAME_LEN, UDP_SRCPORT, UDP_CHECKSUM, UDP_DATA, 
                  TCP_SRCPORT, TCP_SEQNO, TCP_CHECKSUM, TCP_TIMESTAMP, TCP_TIMESTAMP_VAL]:
        cmd += "-e {} ".format(field)
    cmd += "-E header=y -E separator=, -E quote=d -E occurrence=f > {}".format(pcap_csv_path)
    subprocess.run(cmd, shell=True, check=True)


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
        if trace_duration_s < flow_duration_s * 0.85:
            raise RuntimeError("flow terminated prematurely.")

        throughput_trace_path = os.path.join(trial_dir, port_no + THROUGHPUT_TRACE_SUFFIX)
        write_to_csv(throughput_trace_path, ["time (s)", "throughput (Mbps)"], average_rates)


def main():
    args = get_parse_pcap_args()
    with open(args.exp_conf) as f:
        exp_conf = json.load(f)
    stack_combi = get_stack_combi(exp_conf, args.name)
    valid_port_nos = get_port_nos_from_combi(stack_combi)
    
    interface_pcap_path = os.path.join(args.trial_dir, INTERFACE_PCAP_FILENAME)
    interface_pcap_csv_path = interface_pcap_path + ".csv"
    convert_pcap_to_csv(interface_pcap_path, interface_pcap_csv_path)

    df = pd.read_csv(interface_pcap_csv_path, dtype=str)
    df[RELATIVE_TIME] = df[RELATIVE_TIME].astype(dtype=float)
    df[FRAME_LEN] = df[FRAME_LEN].astype(dtype=float)

    port_no_packets_map = {}
    for port_no in valid_port_nos:
        port_no_packets_map[port_no] = df.loc[(df[UDP_SRCPORT] == port_no) | (df[TCP_SRCPORT] == port_no)]

    window_size_s = exp_conf["netem_conf"]["RTT_ms"] / 100 # 10 RTT
    output_throughput_traces(port_no_packets_map, args.trial_dir, exp_conf["flow_duration_s"], window_size_s)


if __name__ == "__main__":
    main()
