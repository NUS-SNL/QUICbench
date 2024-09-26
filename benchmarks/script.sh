
for x in 50rtt-20bw-5.0bdp
do
    python3 generate_exp_conf.py -b base_conf/${x}.json -t tp -n tpratios-n-${x} -r /home/quic/quic_bench_results/tpratios-n-${x}
done