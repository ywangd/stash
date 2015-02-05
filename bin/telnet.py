''' telnet hostname [port] [timeout]

a very simple telnet client.


'''
import socket, select, string, sys, telnetlib,time,argparse
#main function
if __name__ == "__main__":
    app = globals()['_stash']
    ap=argparse.ArgumentParser()
    ap.add_argument('host')
    ap.add_argument('port',default=23,nargs='?',type=int)
    ap.add_argument('timeout',default=2,nargs='?',type=int)
    args=ap.parse_args()
    print ap
    host = args.host
    port = args.port
    timeout=args.timeout
    
    print host,port, timeout
    try :
        s = telnetlib.Telnet(host,port,timeout)
        #s.open()
    # connect to remote host
    except :
        print 'Unable to connect'
        sys.exit()

    print 'Connected to remote host.  type [[[ to quit'
                #user entered a message
    def getuserinput():
        ui.cancel_delays()
        if app.term.inp_buf:
            msg = sys.stdin.readline()
            s.write(msg.encode('ascii')+b'\n')
            if msg=='[[[':
                print 'exit'
                s.close()
                sys.exit()
        ui.delay(getuserinput,0.1)
    getuserinput()
    while 1:
        socket_list = [ s] #stdin seems to always say it is getting events, so just pollstdin

        # Get the list sockets which are readable
        read_sockets, write_sockets, error_sockets = select.select(socket_list , [], [])
        
        for sock in read_sockets:
            #incoming message from remote server
            if sock == s:

                data = sock.read_eager()
                if not data :
                    pass
                else :
                    #print data.decode('ascii')
                    if data.decode('ascii').find('[H')>-1:  #cheap way to fake screen clear
                        app.term.clear()
                    else:
                        sys.stdout.write(data.decode('ascii'))


