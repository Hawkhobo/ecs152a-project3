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
 
# create a udp socket
start_throughput = time()
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:

    # bind the socket to a OS port
    udp_socket.bind(("0.0.0.0", 5000))

    timeoutDuration = 0.1
    udp_socket.settimeout(0.1)

    seq_id = 0
    sent_empty = False
    windowSpace = WINDOW_SIZE

    startTimes = {}
    endTimes = {}

    dupCount = 0
    prevAck = 0
    retransmitted = False

    acks = {}
    messages = []

    # start sending data from 0th sequence
    ack_id = 0
    while True:

        for _ in range(windowSpace):
            message = int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id: seq_id + MESSAGE_SIZE]
            
            # constructs the empty packet if we have sent all previous data
            if seq_id > len(data) and not sent_empty:
                message = int.to_bytes(len(data), SEQ_ID_SIZE, byteorder='big', signed=True)
                sent_empty = True
            
            messages.append((seq_id, message))
            acks[seq_id] = False
            
            if seq_id not in startTimes:
                startTimes[seq_id] = time()

            udp_socket.sendto(message, ('localhost', 5001))

            seq_id += MESSAGE_SIZE
            windowSpace -= 1

            if len(message) == 0:
                break
            
        try:
            
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
                    if a not in endTimes:
                            endTimes[a] = time()

            if prevAck == ack_id and not retransmitted:
                dupCount += 1

                if dupCount == 3:
                    raise socket.timeout
            else:
                prevAck = ack_id
                dupCount = 0
                retransmitted = False

                timeoutDuration = 0.1
                udp_socket.settimeout(0.1)
                
        except socket.timeout:

            # no ack received, resend unacked messages
            for sid, message in messages:
                if not acks[sid]:
                    udp_socket.sendto(message, ('localhost', 5001))
                    startTimes[ack_id] = time()
                    retransmitted = True
                    break

            # Doubles timeout duration
            timeoutDuration += timeoutDuration
            udp_socket.settimeout(timeoutDuration)
     
    # Run the time until the last packet from the file, and NOT the final closing message. 
    end_throughput = time()

    # send final closing message
    finack = int.to_bytes(0, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    udp_socket.sendto(finack, ('localhost', 5001))   
    
    # get throughput
    throughput  = len(data) / (end_throughput - start_throughput)

    # get average packet delay
    avg_packet_delay = 0
    for k in endTimes.keys():
        packet_delay = endTimes[k] - startTimes[k]
        avg_packet_delay += packet_delay

    avg_packet_delay /= len(endTimes.keys())

    # get performance metric (throughput/average per packet delay)
    performance_metric = throughput / avg_packet_delay

    print(f'{round(throughput, 2)}, {round(avg_packet_delay, 2)}, {round(performance_metric, 2)}')

    # close the connection
    udp_socket.close()
    