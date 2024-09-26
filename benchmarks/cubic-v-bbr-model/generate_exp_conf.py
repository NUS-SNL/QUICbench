import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], '../..')) # allow importing from parent dir (repo)

from utils.files import read_json_as_dict, dump_dict_as_json

def main():
    bw = 100
    for bdp in range(2, 21):
        bdp = bdp / 2
        
        exp_conf = {
            "experiment_name": "cubic-v-bbr-model-{}bw-{}bdp".format(bw, bdp),
            "experiment_results_dir": "/home/quic/quic_bench_results/cubic-v-bbr-model/{}bw-{}bdp".format(bw, bdp),
            "num_trials": 1,
            "netem_conf": {
                "RTT_ms": 50,
                "bandwidth_Mbps": bw,
                "buffer_bdp": bdp
            },
            "flow_duration_s": 120,
            "virtual_interface": "enp1s0f1-br0",
            "stacks_combinations": [
                {
                    "name": "tcp-bbr_tcp-cubic",
                    "stacks": [
                        {
                            "name": "tcp",
                            "cc_algo": "bbr",
                            "port_no": "4000"
                        },
                        {
                            "name": "tcp",
                            "cc_algo": "cubic",
                            "port_no": "4001"
                        }
                    ]
                },
                {
                    "name": "mvfst-bbr_tcp-cubic",
                    "stacks": [
                        {
                            "name": "mvfst",
                            "cc_algo": "bbr",
                            "port_no": "4000"
                        },
                        {
                            "name": "tcp",
                            "cc_algo": "cubic",
                            "port_no": "4001"
                        }
                    ]
                },
                {
                    "name": "xquic-bbr_tcp-cubic",
                    "stacks": [
                        {
                            "name": "xquic",
                            "cc_algo": "bbr",
                            "port_no": "4000"
                        },
                        {
                            "name": "tcp",
                            "cc_algo": "cubic",
                            "port_no": "4001"
                        }
                    ]
                },
                {
                    "name": "tcp-bbr_xquic-cubic",
                    "stacks": [
                        {
                            "name": "tcp",
                            "cc_algo": "bbr",
                            "port_no": "4000"
                        },
                        {
                            "name": "xquic",
                            "cc_algo": "cubic",
                            "port_no": "4001"
                        }
                    ]
                },
                {
                    "name": "mvfst-bbr_xquic-cubic",
                    "stacks": [
                        {
                            "name": "mvfst",
                            "cc_algo": "bbr",
                            "port_no": "4000"
                        },
                        {
                            "name": "xquic",
                            "cc_algo": "cubic",
                            "port_no": "4001"
                        }
                    ]
                },
                {
                    "name": "xquic-bbr_xquic-cubic",
                    "stacks": [
                        {
                            "name": "xquic",
                            "cc_algo": "bbr",
                            "port_no": "4000"
                        },
                        {
                            "name": "xquic",
                            "cc_algo": "cubic",
                            "port_no": "4001"
                        }
                    ]
                },                
            ]
        }
        
        dump_dict_as_json(
            exp_conf,
            os.path.join(os.path.dirname(os.path.realpath(__file__)), exp_conf["experiment_name"] + ".json")
        )
    

if __name__ == "__main__":
    main()
