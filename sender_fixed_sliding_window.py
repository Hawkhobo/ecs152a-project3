# Code has been sampled from Muhammad Haroon's code, with modifications.
# Original code: https://github.com/Haroon96/ecs152a-fall-2023/blob/main/week7/docker/sender.py

"""
Theory Crafting:

- we know that a packet has not arrived, if the seq_id of the packet sent != the ack_id of the packet recieved

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
WINDOW_SIZE = 10

# read data
with open('./docker/file.mp3', 'rb') as f:
    data = f.read()
 
def updateDupAcks(acks):
    for key in acks:

        # if current ack, break out
        if (acks[key] == acks[ack_id]):
            break              
        
        # Check if given ack is received, else duplicate ack
        ackReceived, ackDuped = acks[key]
        if not ackReceived:
            ackDuped += 1
            acks[key] = (ackReceived, ackDuped)
            # Fast Retransmit
            if ackDuped >= 3:
                acks[key] = (ackReceived, 0)
                retransmit = int.to_bytes(key, SEQ_ID_SIZE, byteorder='big', signed=True) + data[key : key + MESSAGE_SIZE]
                udp_socket.sendto(retransmit, ('localhost', 5001))

def updateSlidingWindow(acks, seq_id_tmp, packet_delay, packetCount):
    for key in acks: 

        ackReceived, ackDuped = acks[key]
        
        if not ackReceived:
            break
        else:
            # slide window by 1
            message = int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
            messages.append((seq_id_tmp, message))
            acks[seq_id_tmp] = (False, 0)
            seq_id_tmp += MESSAGE_SIZE

            # send new message in window
            udp_socket.sendto(message, ('localhost', 5001))
            packet_delay = time()
            packetCount += 1

            # pop received message (this keeps runtime within sliding window)
            acks.pop(key)
        
    return seq_id, packet_delay, packetCount, key


total_packet_delay = 0
packetCount = 0

# create a udp socket
start_throughput = time()
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:

    # bind the socket to a OS port
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(1)
    
    # start sending data from 0th sequence
    seq_id = 0

    # create messages
    messages = []
    acks = {}
    seq_id_tmp = seq_id
    for i in range(WINDOW_SIZE):
        # construct messages
        # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
        message = int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
        messages.append((seq_id_tmp, message))
        acks[seq_id_tmp] = (False, 0)
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
            acks[ack_id] = (True, 0)

            # Inspect key-values (unacked messages) previous to current key-value (received ack)
            # within sliding window 
            updateDupAcks(acks)       

            # update sliding window, provided we don't run into a False ack
            seq_id_tmp, packet_delay, packetCount, key = updateSlidingWindow(acks, seq_id_tmp, packet_delay, packetCount)

            # print out current duplicate to resolve (or, the last received packet if there are no duplicates)
            print(f'ack: {acks[key]}')

            seq_id = seq_id_tmp
            if seq_id < len(data) and not acks:
                break

        except socket.timeout:
            # no ack received, resend unacked messages
            for sid, message in messages:
                if not acks[sid]:
                    udp_socket.sendto(message, ('localhost', 5001))
        
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
    udp_socket.sendto(int.to_bytes(-1, 4, signed=True, byteorder='big'), ('localhost', 5001))
    
    # close the connection
    udp_socket.close()
    