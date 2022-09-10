# FILE NAMING CONVENTIONS
INTERFACE_PCAP_FILENAME = "packets.pcap"
VETH_PCAP_FILENAME = "packets-br0.pcap"
THROUGHPUT_TRACE_SUFFIX = ".tp-trace"
DELAY_TRACE_SUFFIX = ".delays"
STACK_LOG_SUFFIX = ".log"
CWND_TRACE_SUFFIX = ".cwnd-trace"

# PARSING CONSTANTS
TRUNCATE_TRACES_BY = 0.95 # percentage of flow duration to truncate traces by (don't count end of flow)
