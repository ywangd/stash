'''Host And Port Scanner'''
import socket
from datetime import datetime
# IP address to scan
net = input("IP address: ")
net1 = net.split('.')
a = '.'

# Create IP address for range scanning
net2 = net1[0] + a + net1[1] + a + net1[2] + a
st1 = int(input("Starting Number: "))
en1 = int(input("Last Number: "))
port = int(input("Port: "))
en1 = en1 + 1
print("Start scanning")
t1 = datetime.now()

# Scan 
def scan(addr):
   s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
   socket.setdefaulttimeout(1)
   result = s.connect_ex((addr, port))
   if result == 0:
      return 1
   else :
      return 0

# Start scan
def run1():
   for ip in range(st1,en1):
      addr = net2 + str(ip)
      if (scan(addr)):
         print (addr , "is up")
         
run1()
t2 = datetime.now()
total = t2 - t1
print ("Scanning completed in: " , total)