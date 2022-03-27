import os
import sys
import argparse
import json
import subprocess
import time
from datetime import datetime
from operator import itemgetter

from constants import *
from stacks.chromium import Chromium
from stacks.msquic import Msquic
from stacks.mvfst import Mvfst
from stacks.quiche import Quiche
from stacks.tcp import Tcp
from utils.remote_cmd import get_remote_cmd, get_remote_cmd_sudo, get_scp_file_to_remote_cmd
from network.set_netem import set_netem
from network.clear_netem import clear_netem
from network.test_network import *
from network.tcpdump import TCPDump


def get_prog_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stacks_conf", "-s", help="path to stacks configuration", type=str, 
        default="./config/stacks_conf_default.json")
    parser.add_argument("--general_conf", "-k", help="path to general configuration", type=str,
        default="./config/general_conf_default.json")
    parser.add_argument("--exp_conf", "-e", help="path to experiment configuration", type=str)
    return parser.parse_args()


def check_sudo_privileges(server_hostname, server_pw_path):
    subprocess.run("sudo echo 'Got sudo privileges for local machine.'", shell=True, check=True)
    try:
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo echo 'Got sudo privileges for server machine.'"),
            shell=True, check=True, timeout=1)
    except subprocess.TimeoutExpired:
        sys.exit("exiting... server password is incorrect.")


def init_stacks(stacks_conf, server_ip, server_hostname):
    chromium_stack = Chromium(server_ip, server_hostname, **stacks_conf[Chromium.NAME])
    msquic_stack = Msquic(server_ip, server_hostname, **stacks_conf[Msquic.NAME])
    mvfst_stack = Mvfst(server_ip, server_hostname, **stacks_conf[Mvfst.NAME])
    quiche_stack = Quiche(server_ip, server_hostname, **stacks_conf[Quiche.NAME])
    tcp_stack = Tcp(server_ip, server_hostname)
    return {
        Chromium.NAME: chromium_stack,
        Msquic.NAME: msquic_stack,
        Mvfst.NAME: mvfst_stack,
        Quiche.NAME: quiche_stack,
        Tcp.NAME: tcp_stack
    }


def set_kernel_params(kernel_params, server_hostname, server_pw_path):
    print("Setting kernel parameters:")
    for param, value in kernel_params.items():
        subprocess.run("sudo sysctl -w {}=\"{}\"".format(param, value), shell=True, check=True)
        subprocess.run(get_remote_cmd_sudo(server_hostname, server_pw_path, "sudo sysctl -w {}=\\\"{}\\\"".format(param, value)), 
            shell=True, check=True)


def main():
    args = get_prog_args()
    with open(args.stacks_conf) as f:
        stacks_conf = json.load(f)
    with open(args.general_conf) as f:
        general_conf = json.load(f)
    with open(args.exp_conf) as f:
        exp_conf = json.load(f)
    server_ip, server_hostname, interface, server_ingress_interface = itemgetter("server_ip", "server_hostname", "interface", "server_ingress_interface")(general_conf)

    server_pw_path = general_conf["server_pw_path"]    
    check_sudo_privileges(server_hostname, server_pw_path)
    
    stacks_kls = init_stacks(stacks_conf, server_ip, server_hostname)
    set_kernel_params(general_conf["kernel_params"], server_hostname, server_pw_path)

    set_netem(server_hostname, server_pw_path, interface, server_ingress_interface, exp_conf["netem_conf"])
    test_rtt(server_ip)
    test_bandwidth(server_hostname, server_ip)

    # Starting experiment
    experiment_results_dir, num_trials, flow_duration_s, stacks_combinations = \
        itemgetter("experiment_results_dir", "num_trials", "flow_duration_s", "stacks_combinations")(exp_conf)
    
    try:
        # set up results dir on server-side
        subprocess.run(get_remote_cmd(server_hostname, ["mkdir", experiment_results_dir]), check=True)
        for conf in [args.stacks_conf, args.general_conf, args.exp_conf]:
            subprocess.run(get_scp_file_to_remote_cmd(server_hostname, conf, experiment_results_dir), check=True)

        for combi in stacks_combinations:
            combi_name, combi_stacks  = itemgetter("name", "stacks")(combi)
            combi_results_dir = os.path.join(experiment_results_dir, combi_name)
            subprocess.run(get_remote_cmd(server_hostname, ["mkdir", combi_results_dir]), check=True)

            successful_trials = 0
            while successful_trials < num_trials:
                # run a trial for stack combination
                trial_datetime = datetime.now().strftime("%Y-%m-%d:%H:%M:%S")
                trial_results_dir = os.path.join(combi_results_dir, trial_datetime)
                subprocess.run(get_remote_cmd(server_hostname, ["mkdir", trial_results_dir]), check=True)
                
                # start servers
                stack_processes = []
                for stack in combi_stacks:
                    stack_name, stack_cc_algo, stack_port_no = itemgetter("name", "cc_algo", "port_no")(stack)
                    proc = stacks_kls[stack_name].run_remote_server(stack_port_no, stack_cc_algo, flow_duration_s + 5)
                    stack_processes.append(proc)
                
                time.sleep(2) # wait for servers to start

                # start tcpdump
                tcpdump_interface_output_file = os.path.join(trial_results_dir, INTERFACE_PCAP_FILENAME)
                tcpdump_interface = TCPDump(server_hostname, server_ip, interface, tcpdump_interface_output_file)
                tcpdump_interface.start()

                # start clients
                for stack in combi_stacks:
                    stack_name, stack_cc_algo, stack_port_no = itemgetter("name", "cc_algo", "port_no")(stack)
                    proc = stacks_kls[stack_name].run_client(stack_port_no, stack_cc_algo, flow_duration_s)
                    stack_processes.append(proc)

                # wait for all server/client processes to finish
                for proc in stack_processes:
                    proc.wait()

                # stop tcpdump
                tcpdump_interface.stop()

                successful_trials += 1

    finally:
        # clean up
        clear_netem(server_hostname, server_pw_path, interface, server_ingress_interface)


if __name__ == "__main__":
    main()
