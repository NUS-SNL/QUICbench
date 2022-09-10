import re
from collections import defaultdict
from common import main, get_time_diff

PACKET_SIZE_BYTES = 1500

def retrieve_time(timestamp):
    return float(timestamp[:-1])

def retrieve_cwnd(cwnd):
    # convert from no. of packets to kB
    return float(cwnd) * PACKET_SIZE_BYTES / 1000

def tcp_parse_func(log_path):
    # retrieve single flow cwnd trace from tcp-probe trace
    socket_events_map = defaultdict(list)
    with open(log_path) as f:
        for line in f.readlines():
            if "tcp_probe" in line:
                # is a tcp_probe trace
                fields = re.split('\[0\d\d\]', line)[1].split()                
                timestamp = fields[1]
                key_values = {}
                for key_value in fields[3:]:
                    key_value = key_value.split('=')
                    key_values[key_value[0]] = key_value[1]
                socket_events_map[key_values['sock_cookie']].append((timestamp, key_values))
        
    # flow belonging to socket with greatest number of events is the desired TCP flow
    max_events_count = max(map(len, socket_events_map.values()))
    events = None
    for socket, socket_events in socket_events_map.items():
        if len(socket_events) == max_events_count:
            events = socket_events
            break

    # parse events
    cwnd_trace = []
    base_timestamp = retrieve_time(events[0][0])
    for timestamp, key_values in events:
        cwnd_trace.append((retrieve_time(timestamp) - base_timestamp, retrieve_cwnd(key_values['snd_cwnd'])))
    
    return cwnd_trace


if __name__ == "__main__":
    main(tcp_parse_func)
