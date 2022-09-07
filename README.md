# QUIC bench
#### _Benchmarking tool for IETF QUIC stacks_

QUIC bench is a tool for automatic benchmarking of IETF QUIC stacks to help us understand their transport-layer performance.
After being deployed on a testbed, and with the configurations specified, it can run benchmarking experiments, capture transport-layer metrics, 
and generate visualizations of these metrics.

## Overview

QUIC bench comprises mainly of a Python script `run_bench.py` that takes in configurations specified
in json format and runs a single benchmarking experiment, automating the entire QUIC performance
benchmarking end-to-end process. The script performs the following steps in order:
1. Configure kernel parameters on both machines
2. Configure server-side network interface to emulate network conditions
3. Run tests to ensure that the network is emulated correctly
4. Run each trial of the benchmarking experiment
    1. Start capturing packet traces on the server-side network interface
    2. Run QUIC/TCP flows for a fixed duration
    3. Extract metrics from packet traces and store results on the server machine
5. Teardown server-side network emulation

## Experimental Setup

The following setup is required for QUIC bench to work correctly.

### Testbed
A client and server machine has to be set up and connected via a local network. QUIC bench has only been tested on Ubuntu 20.04, but should work in most unix environments.

### Client-side
- Install QUIC bench repo
- Install individual IETF QUIC stacks

### Server-side
- Install QUIC bench repo
- Install individual IETF QUIC stacks

## Usage
### Configurations
The following configurations have to be specified and passed to QUIC bench for it to run the benchmarking experiments.

#### General configuration

This config specifies configurations specific to this particular testbed setup, such as the server machine’s IP address and hostname, and values of kernel parameters to be changed as `kernel_params`.

Example:
```
{
    "server_ip": "10.0.0.1",
    "server_hostname": "edith",
    "server_pw_path": "/home/quic/quic_experiments/edith_pw",
    "server_repo_path": "/home/quic/quic_experiments/QUIC-bench",
    "interface": "enp1s0f1",
    "server_ingress_interface": "ifb0",
    "kernel_params": {
        "net.core.rmem_max": "12582912",
        "net.core.rmem_default": "1703936",
        "net.core.wmem_max": "12582912",
        "net.core.wmem_default": "1703936",
        "net.ipv4.tcp_rmem": "10240 87380 12582912",
        "net.ipv4.tcp_wmem": "10240 87380 12582912"
    }
}
```

#### Stacks configuration

This config specifies configurations that are specified to the QUIC stacks, such as the paths to the server/client executable. It will be used to run the QUIC stacks.

Example:
```
{
    "chromium": {
        "cubic_server_path": "/home/quic/quic_experiments/chromium-cubic/src/out/Debug/quic_server",
        "bbr_server_path": "/home/quic/quic_experiments/chromium-bbr/src/out/Debug/quic_server",
        "bbrv2_server_path": "/home/quic/quic_experiments/chromium-bbr_v2/src/out/Debug/quic_server",
        "server_cert_path": "/home/quic/quic_experiments/chromium-cubic/src/net/tools/quic/certs/out/leaf_cert.pem",
        "server_key_path": "/home/quic/quic_experiments/chromium-cubic/src/net/tools/quic/certs/out/leaf_cert.pkcs8",
        "client_path": "/home/quic/quic_experiments/chromium-cubic/src/out/Debug/quic_client"
    }
}
```

#### Experiment configuration

This config specifies the parameters of the benchmarking experiment to run. The emulated network parameters can be specified in `netem_conf` and the stacks to run in `stacks_combinations`. The folder `benchmarks` contains the experiment configurations we used in our performance benchmarks.

Example:
```
{
    "experiment_name": "sample",
    "experiment_results_dir": "/home/quic/quic_bench_results/sample",
    "num_trials": 2,
    "netem_conf": {
        "RTT_ms": 50,
        "bandwidth_Mbps": 20,
        "buffer_bdp": 1
    },
    "flow_duration_s": 120,
    "virtual_interface": "enp1s0f1-br0",
    "stacks_combinations": [
        {
            "name": "mvfst-cubic_tcp-cubic",
            "stacks": [
                { "name": "mvfst", "cc_algo": "cubic", "port_no": "4000" },
                { "name": "tcp", "cc_algo": "cubic", "port_no": "7000" }
            ]
        },
        {
            "name": "chromium-cubic_quiche-cubic",
            "stacks": [
                { "name": "chromium", "cc_algo": "cubic", "port_no": "5000" },
                { "name": "quiche", "cc_algo": "cubic", "port_no": "6000" }
            ]
        }
    ]
}
```

### Run QUIC bench
```
python3 run_bench.py -s={path to stack config} -k={path to general config} -e={path to experiment config}
```

## Extension - Adding a new QUIC stack

QUIC bench has been designed for easy extension, and to run QUIC bench with a new IETF QUIC stack that's not currently supported, only minor changes to this repo have to be made:
1. Create a new class that inherits from Stack and implement the Stack interface methods that specifies how to run the server/client of this new QUIC stack
2. Add an entry to the stack configuration file for this QUIC stack - parameters specified here will be used to instantiate the class created previously
3. Modify the `init_stacks` method in `run_bench.py` to instantiate the class for the new QUIC stack

## License

MIT
