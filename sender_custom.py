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


# Vegas' buffer window; 2 KB/s and 4 KB/s
alpha = 2000
beta = 4000

# Congestion Avoidance trigger
delta = 1000

# read data
with open('./docker/file.mp3', 'rb') as f:
    data = f.read()

def increaseInterval(cwnd):
    cwnd += cwnd
    return cwnd

def evaluationInterval(diff):
    if diff <= delta:
        return False
    else:
        return True

# Determine cwnd with Vegas protocol
def congestionInterval(extra_data, cwnd):
    # If between thresholds, cwnd is not updated.
    if (extra_data < alpha):
        cwnd += 1
    elif (extra_data > beta):
        cwnd -= 1
    
    return cwnd
 
# create a udp socket
start_throughput = time()
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:

    # bind the socket to a OS port
    udp_socket.bind(("0.0.0.0", 5000))

    timeoutDuration = 0.1
    udp_socket.settimeout(timeoutDuration)

    seq_id = 0
    sent_empty = False

    startTimes = {}
    endTimes = {}

    dupCount = 0
    prevAck = 0
    timeout = False

    cwnd = WINDOW_SIZE

    # vegas protocol that follows a retransmission. check if next 2 also need retransmission
    checkNext2 = 3
    
    # Allow storage of lowest (optimal) RTT seen so far. 
    baseRTT = float('inf')

    isCongest = False

    switchInterval = True

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

            udp_socket.sendto(message, ('localhost', 5001))

            if seq_id_tmp not in startTimes:
                startTimes[seq_id_tmp] = time()

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

                print(f'ack_id recv: {ack_id}')
            
                if ack_message == b'fin':
                    break

                # Measure current time for RTT calculations and comparisons
                currentTime = time()

                # ACK returned has an ID corresponding to the next ID. So need to make an adjustment
                actual_ack = ack_id - MESSAGE_SIZE
                # Compute various delay values to be used in Vegas
                # Determine BaseRTT
                if currentTime - startTimes[actual_ack] < baseRTT:
                    baseRTT = currentTime - startTimes[actual_ack]

                # Determine currentRTT
                currentRTT = currentTime - startTimes[actual_ack]
                
                # Determine expected and actual throughput
                expected = cwnd / baseRTT
                actual = cwnd / currentRTT
                
                # monitor extra data
                extra_data = (expected - actual) * baseRTT

                # diff
                diff = expected - actual
                
                # update acks below cumulative ack
                for a in acks:
                    if a < ack_id and acks[a] != True:
                        acks[a] = True
                        if a not in endTimes:
                                endTimes[a] = currentTime
                
                # monitor next 2 packets following retransmission
                """if checkNext2 < 3:
                    if checkNext2 != 0:
                        checkNext2 -= 1
                        if currentTime - startTimes[actual_ack] > timeoutDuration:
                            raise socket.timeout
                    else:
                        checkNext2 = 3"""

                # duplicate detected
                if prevAck == ack_id and not retransmitted:
                    """ # does estimated RTT exceed RTO?
                    if currentTime - startTimes[actual_ack] > timeoutDuration:
                        checkNext2 -= 1
                        raise socket.timeout
                    # If not, 3xACK still applies
                    else: """
                    dupCount += 1

                    if dupCount == 3:
                        #checkNext2 -= 1
                        raise socket.timeout
                # no duplicate detected 
                else:
                    prevAck = ack_id
                    dupCount = 0
                    retransmitted = False

                    timeoutDuration = 0.1
                    udp_socket.settimeout(0.1)
                
                # all acks received, move on
                if all(acks.values()):
                    # update congestion window
                    if not timeout:
                        # Congestion Avoidance
                        if isCongest:
                            cwnd = congestionInterval(extra_data, cwnd)

                        # Slow Start
                        else:
                            # Next slow-start round: evaluation or increase?
                            if switchInterval:
                                cwnd = increaseInterval(cwnd)
                                switchInterval = False
                    
                            else:
                                isCongest = evaluationInterval(diff)
                                switchInterval = True

                        timeout = False

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
