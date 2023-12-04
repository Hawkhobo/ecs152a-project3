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

# read data
with open('./docker/send.txt', 'rb') as f:
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
    sent_empty = False
    # Run a timer for throughput
    while True:
        
        udp_socket.settimeout(1)
        
        # construct message
        # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
        message = int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id : seq_id + MESSAGE_SIZE]

        # constructs the empty packet if we have sent all previous data
        if seq_id > len(data) and not sent_empty:
            message = int.to_bytes(len(data), SEQ_ID_SIZE, byteorder='big', signed=True)
            sent_empty = True
            
        # send message
        udp_socket.sendto(message, ('localhost', 5001))
        packet_delay = time()
        packetCount += 1
        
        # wait for acknowledgement
        ack_id = 0
        while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                total_packet_delay += time() - packet_delay

                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')

                if ack_id != len(data) or not sent_empty:
                    break
                
            except socket.timeout:
                # no ack received, resend unacked message
                timeoutDuration += timeoutDuration
                udp_socket.settimeout(timeoutDuration)
                udp_socket.sendto(message, ('localhost', 5001))
          
        if ack_id == len(data) + 3:
            break
    
        # move sequence id forward
        seq_id += MESSAGE_SIZE      

    # Run the time until the last packet from the file, and NOT the final closing message. 
    end_throughput = time()
    
    # get throughput
    throughput  = len(data) / (end_throughput - start_throughput)

    # get average packet delay
    avg_packet_delay = total_packet_delay / packetCount

    # get performance metric (throughput/average per packet delay)
    performance_metric = throughput / avg_packet_delay

    print(f'{round(throughput, 2)}, {round(avg_packet_delay, 2)}, {round(performance_metric, 2)}')
    
    # send final closing message
    finack = int.to_bytes(0, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    udp_socket.sendto(finack, ('localhost', 5001))
    
    # close the connection
    udp_socket.close()
