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
WINDOW_SIZE = 1

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

    startTimes = {}
    endTimes = {}

    dupCount = 0
    prevAck = 0

    dupAck = False
    timeout = False

    cwnd = WINDOW_SIZE
    ssthresh = 64
    
    # start sending data from 0th sequence
    ack_id = 0
    while seq_id < len(data):

        messages = []
        acks = {}

        seq_id_tmp = seq_id
        for i in range(cwnd):

            if sent_empty:
                break

            # construct messages
            message = int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
            
            # constructs the empty packet if we have sent all previous data
            if seq_id_tmp > len(data) and not sent_empty:
                message = int.to_bytes(len(data), SEQ_ID_SIZE, byteorder='big', signed=True)
                sent_empty = True

            messages.append((seq_id_tmp, message))
            acks[seq_id_tmp] = False

            if seq_id_tmp not in startTimes:
                startTimes[seq_id_tmp] = time()

            udp_socket.sendto(message, ('localhost', 5001))

            # move seq_id tmp pointer ahead
            seq_id_tmp += MESSAGE_SIZE
            
        # wait for acknowledgement
        retransmitted = False
        while True:
            
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                ack_message = ack[SEQ_ID_SIZE:]
                
                if ack_message == b'fin':
                    break

                # update acks below cumulative ack
                for a in acks:
                    if a < ack_id and acks[a] != True:
                        acks[a] = True
                        if a not in endTimes:
                                endTimes[a] = time()
                
                if prevAck == ack_id and not retransmitted:
                    dupCount += 1

                    if dupCount == 3:
                        dupAck = True
                        raise socket.timeout
                else:
                    prevAck = ack_id
                    dupCount = 0
                    retransmitted = False

                    timeoutDuration = 0.1
                    udp_socket.settimeout(0.1)
                
                # all acks received, move on
                if all(acks.values()):

                    if not timeout:
                        if cwnd >= ssthresh:
                            cwnd += 1
                        else:
                            cwnd += cwnd
                    else:
                        if dupAck:
                            cwnd = ssthresh
                        else:
                            cwnd = 1

                    timeout = False
                    dupAck = False

                    break

            except socket.timeout:

                timeout = True

                # no ack received, resend unacked messages
                for sid, message in messages:
                    if not acks[sid]:
                        udp_socket.sendto(message, ('localhost', 5001))
                        startTimes[ack_id] = time()
                        retransmitted = True
                        break
                
                # Halfs the slow start threshhold and resets window size
                ssthresh = max(cwnd // 2, 1)

                # Doubles timeout duration
                timeoutDuration += timeoutDuration
                udp_socket.settimeout(timeoutDuration)
                
        # move sequence id forward
        seq_id = seq_id_tmp
        
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
