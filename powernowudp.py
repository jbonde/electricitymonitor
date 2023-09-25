import time
import socket

UDP_IP = ""
UDP_PORT = 3434 # Meter
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #reuse socket if program is opened after crash
sock.bind((UDP_IP, UDP_PORT))
message=[]
data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
message=data.decode('utf-8')
powernow=message.split(",")[3]
print(str(powernow))
