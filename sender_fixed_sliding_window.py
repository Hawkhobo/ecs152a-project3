# Code has been sampled from Muhammad Haroon's code, with modifications.
# Original code: https://github.com/Haroon96/ecs152a-fall-2023/blob/main/week7/docker/sender.py

"""
Theory Crafting:

- we know that a packet has not arrived, if the seq_id of the packet sent != the ack_id of the packet recieved
- 

"""

import socket
from time import time 

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
# total packets to send
WINDOW_SIZE = 20

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
    while seq_id < len(data):
        
        udp_socket.settimeout(1)
    
        # create messages
        messages = []
        acks = {}
        seq_id_tmp = seq_id
        for i in range(WINDOW_SIZE):
            # construct messages
            # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
            message = int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
            messages.append((seq_id_tmp, message))
            # Receiver sends acks for the message that it is waiting for, not the one it has received 
            acks[seq_id_tmp + MESSAGE_SIZE] = False
            # move seq_id tmp pointer ahead
            seq_id_tmp += MESSAGE_SIZE

        # send messages
        for _, message in messages:
            udp_socket.sendto(message, ('localhost', 5001))
            packet_delay = time()
            packetCount += 1
        
        # wait for acknowledgement
        while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                total_packet_delay += time() - packet_delay
                
                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                print(ack_id, ack[SEQ_ID_SIZE:])
                acks[ack_id] = True
                
                # all acks received, move on
                if all(acks.values()):
                    break
            except socket.timeout:
                # no ack received, resend unacked messages
                for sid, message in messages:
                    if not acks[sid]:
                        timeoutDuration += timeoutDuration
                        udp_socket.settimeout(timeoutDuration)
                        udp_socket.sendto(message, ('localhost', 5001))
                
        # move sequence id forward
        seq_id += MESSAGE_SIZE * WINDOW_SIZE
        
    # Run the time until the last packet from the file, and NOT the final closing message. 
    end_throughput = time()
    
    # get throughput
    throughput  = len(data) / (end_throughput - start_throughput)

    # get average packet delay
    avg_packet_delay = total_packet_delay / packetCount

    # get performance metric (throughput/average per packet delay)
    performance_metric = throughput / avg_packet_delay

    print(f'{round(throughput, 2)}, {round(avg_packet_delay, 2)}, {round(performance_metric, 2)}')
    
    # close the connection
    udp_socket.close()
    