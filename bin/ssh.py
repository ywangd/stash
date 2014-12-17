'''
ssh client for stash. ssh looks for a valid key generated buy ssh-keygen in .ssh.
You can open an intereactive shell by not passing a command. If a command is passed,
the single command is ran with output then ssh exits.

(exit) command will exit shell.

usage: ssh [-h] [--password PASSWORD] [-p PORT] host [command]

positional arguments:
  host                  host ex. user@host.com
  command               Command to send as a quoted string

optional arguments:
  -h, --help            show this help message and exit
  --password PASSWORD   Password for rsa/dsa key or password login
  -p PORT, --port PORT  port for ssh default: 22
'''
import argparse
import threading
import time
import re

from paramiko import SSHClient, AutoAddPolicy


class StashSSH(object):
    
    def __init__(self):
        self.ssh_running = False
        
    def connect(self,host='', passwd=None, port=22):
        print 'Connecting...'
        try:
            self.user, self.host = self.parse_host(host)
            self.passwd = passwd
            self.port = port
            self.ssh = SSHClient()
            self.ssh.set_missing_host_key_policy(AutoAddPolicy())
            self.ssh.connect(self.host,
                             username=self.user,
                             password=self.passwd,
                             port=self.port,
                             key_filename=self.find_ssh_keys())
            self.ssh_running = True
            return True
        except:
            return False
        
        
    def find_ssh_keys(self):
        files = []
        for file in os.listdir(APP_DIR+'/.ssh'):
            if '.' not in file:
                files.append(APP_DIR+'/.ssh/'+file)
        return files    
        
    def parse_host(self,arg):
        user,host = arg.split('@')
        #host, path = temp.split(':')
        return user, host
        
    def stdout_thread(self):
        output = ''
        while self.ssh_running:
            if self.chan.recv_ready():
                output += self.chan.recv(1024)
                time.sleep(.2)
                if not self.chan.recv_ready():
                    output = output.replace('\t','')
                    output = output.replace('\n\r','')
                    #output = output.replace('\r','')
                    print re.sub(r'\[?\d\d?;?\d?\d?m','',output)
                    output = ''
        
    def single_exec(self,command):
        sin,sout,serr = self.ssh.exec_command(command)
        for line in sout.readlines():
            print line.replace('\n','')
        for line in serr.readlines():
            print line.replace('\n','')
        
    def interactive(self):
        t = self.ssh.get_transport()
        self.chan = t.open_session()
        self.chan.get_pty()
        self.chan.set_combine_stderr(True)
        self.chan.exec_command('bash -s')
        t1 = threading.Thread(target=self.stdout_thread)
        t1.start()
        while True:
            if self.chan.send_ready():
                if len(sys.stdin) != 0:
                    #sys.stdout = sys.stdout[:-len(sys.stdin)]
                    tmp =  ''.join(sys.stdin.readline())
                    if tmp == 'exit':
                        self.exit()
                        
                        break
                    self.chan.send(tmp+'\n')
        
    def exit(self):
        self.ssh_running = False
        
if __name__=='__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--password', action='store', default=None, 
                    help='Password for rsa/dsa key or password login')
    ap.add_argument('-p', '--port', action='store', default=22,type=int, 
                    help='port for ssh default: 22')
    ap.add_argument('host', help='host ex. user@host.com')
    ap.add_argument('command', nargs='?', default=False, help='Command to send as a quoted string')
    args = ap.parse_args()
    
    ssh = StashSSH()
    if ssh.connect(host=args.host, passwd=args.password, port=args.port):
        if args.command:
            ssh.single_exec(args.command)
            ssh.exit()
        else:
            ssh.interactive() 
    else:
        print 'Connection Failed'


