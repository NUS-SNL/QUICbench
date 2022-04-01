# QUIC bench
#### _Benchmarking tool for IETF QUIC stacks_

QUIC bench is a tool for automatic benchmarking of IETF QUIC stacks to help us understand their transport-layer performance differences.
After being deployed on a testbed, and with the configurations specified, it can run benchmarking experiments, capture transport-layer metrics, 
and generate visualizations of these metrics.

## Experimental Setup

The following setup is required for QUIC bench to work correctly.

### Testbed
A client and server machine has to be set up and connected via a local network. Both machines have to be running _Ubuntu_.
QUIC bench has to be deployed on both machines. The workflow for QUIC bench is as follows
1. Configure kernel parameters on both server and client machines using _sysctl_
2. Configure the server-side network interface to emulate certain network conditions (RTT, bandwidth, buffer size)
3. Run test flows to ensure that the network has been configured correctly.
4. Run benchmarking experiments
    4.1. Start QUIC/TCP servers
    4.2. Run _tcpdump_ on server-side interface to capture packet traces
    4.3. Start QUIC/TCP clients to start flows
    4.4. After flows terminate, stop _tcpdump_ and extract metrics from packet traces
    4.5. Experiment results will be stored on the server-side
5. Teardown server-side network emulation

### Client-side
- Setup QUIC bench repo
- Setup repositories for individual IETF QUIC stacks

### Server-side
- Setup QUIC bench repo
- Setup repositories for individual IETF QUIC stacks

### Software Requirements
```

```

## Usage
### Configurations
The following configurations have to be specified and passed to QUIC bench for it to run the benchmarking experiments.
#### Stacks configuration
#### General configuration
#### Experiment configuration

### Run QUIC bench
```
python3 run_bench.py -s={path to stack config} -k={path to general config} -e={path to experiment config}
```

## License

MIT
