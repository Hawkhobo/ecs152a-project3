# Code has been sampled from Muhammad Haroon's code, with modifications.
# Original code: https://github.com/Haroon96/ecs152a-fall-2023/blob/main/week7/docker/sender.py

import socket
from time import time 

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
# total packets to send
WINDOW_SIZE = 100

# read data
with open('./docker/file.mp3', 'rb') as f:
    data = f.read()
 
total_packet_delay = 0
packetCount = 0
 
# create a udp socket
start_throughput = time()
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:

    # bind the socket to a OS port
    udp_socket.bind(("0.0.0.0", 5000))

    timeoutDuration = 1

    # start sending data from 0th sequence
    seq_id = 0
    windowSpace = WINDOW_SIZE

    acks = {}
    packet_start_times = {}
    packet_end_times = {}
    udp_socket.settimeout(1)

    sent_empty = False

    ack_id = 0
    while True:
        for _ in range(windowSpace):
            message = int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id: seq_id + MESSAGE_SIZE]
            
            # constructs the empty packet if we have sent all previous data
            if seq_id > len(data) and not sent_empty:
                message = int.to_bytes(len(data), SEQ_ID_SIZE, byteorder='big', signed=True)
                sent_empty = True
            
            acks[seq_id] = False
            
            if seq_id not in packet_start_times:
                packet_start_times[seq_id] = time()

            udp_socket.sendto(message, ('localhost', 5001))

            seq_id += MESSAGE_SIZE
            windowSpace -= 1

            if len(message) == 0:
                break
            
        try:
            if ack_id in packet_start_times and time() - packet_start_times[ack_id] >= timeoutDuration:
                message = int.to_bytes(ack_id, SEQ_ID_SIZE, byteorder='big', signed=True) + data[ack_id: ack_id + MESSAGE_SIZE]

                udp_socket.sendto(message, ('localhost', 5001))
                packet_start_times[ack_id] = time()
                
            ack, _ = udp_socket.recvfrom(PACKET_SIZE)
            
            ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
            ack_message = ack[SEQ_ID_SIZE:]
            
            if ack_message == b'fin':
                break

            # update acks below cumulative ack
            for a in acks:
                if a < ack_id and acks[a] != True:
                    acks[a] = True
                    windowSpace += 1
                    if a not in packet_end_times:
                            packet_end_times[a] = time()

        except socket.timeout:
            pass
     
    
    # Run the time until the last packet from the file, and NOT the final closing message. 
    end_throughput = time()

    # send final closing message
    finack = int.to_bytes(0, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    udp_socket.sendto(finack, ('localhost', 5001))   
    
    # get throughput
    throughput  = len(data) / (end_throughput - start_throughput)

    # get average packet delay
    avg_delay = 0
    for k in packet_end_times.keys():
        packet_delay = packet_end_times[k] - packet_start_times[k]
        avg_delay += packet_delay

    avg_delay /= len(packet_end_times.keys())

    # get performance metric (throughput/average per packet delay)
    performance_metric = throughput / avg_delay

    print(f'{round(throughput, 2)}, {round(avg_delay, 2)}, {round(performance_metric, 2)}')

    # close the connection
    udp_socket.close()
    