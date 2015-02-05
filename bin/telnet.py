'''
telnet.py - simple telnet
usage: telnet.py [-h] host [port] [timeout]

positional arguments:
  host        host
  port        port default:23
  timeout     Timeout default:5s

optional arguments:
  -h, --help  show this help message and exit
'''
import telnetlib
import time
import threading
import argparse
import sys

DELAY = 0.5
            
class Telnet(object):
    def __init__(self,host,port=23,timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = False
        
    def connect(self):
        try:
            print 'Connecting to %s port %d' %(self.host,self.port)
            self.telnet = telnetlib.Telnet(self.host,self.port,self.timeout)
            self.connected = True
            print 'Connected...'
            self.readloop = threading.Thread(target=self.readloop)
            self.readloop.start()
                                             
        except Exception,e:
            print 'Failed to connect. %s' % e

            
    def read(self):
        if self.connected:
            time.sleep(DELAY)
            return self.telnet.read_very_eager()
            
            
    def readloop(self):
        while self.connected: 
            try:
                res =  self.read()
                if res:
                    print res
            except:
                self.connected = False
                print 'EOF Reached.'
            
            
    def write(self,msg):
        if self.connected:
            try:
                self.telnet.write(msg+'\r\n')
            except Exception,e:
                print e
            
    def disconnect(self):
        if self.telnet:
            print 'Disconnect...'
            self.telnet.close()
            self.connected = False
            #if self.readloop:
            #    self.readloop.join()
            sys.exit(0)

if __name__=='__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('host',help='host')
    ap.add_argument('port',nargs='?',default=23,type=int,help='port default:23')
    ap.add_argument('timeout',nargs='?',default=5,type=int,help='Timeout default:5s')
    args = ap.parse_args()
    telnet = Telnet(args.host,args.port,args.timeout)
    telnet.connect()
    while telnet.connected:
        inp = raw_input()
        telnet.write(inp)
        if inp =='exit':
            break
    telnet.disconnect()
    
    '''
    try:
        print 'Connecting to %s port %d' %(args.host,args.port)
        tn = telnetlib.Telnet(args.host,args.port,args.timeout)
        print 'Connected...'
        
        state = 1
    except Exception,e:
        print e
        sys.exit(0)
        
    t1 = threading.Thread(target=readThread)
    t1.start()

    try:
        while state:    
            inp = raw_input()   
            tn.write(inp+'\r\n')
            if inp =='exit':
                state = 0
        t1.join()
        tn.close()
        print 'Disconnect...'
        sys.exit(0)
    except:
        if t1: t1.join()
        if tn: tn.close()
        
'''   
    
            
    
    
    

