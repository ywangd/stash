# An implementation of ifconfig for stash

import socket
# For now main simply lists the interfaces available.
# A future update will hopefully add more features


def main():
	listInterfaces()
	
	
def listInterfaces():
	interfaces = socket.if_nameindex()
	for interface in interfaces:
		ifname = str(interface[1])
		print(ifname)
		
if __name__ == "__main__":
	main()
