'''
ssh client for stash. ssh looks for a valid key generated buy ssh-keygen in .ssh.
You can open an intereactive shell by not passing a command. If a command is passed,
the single command is ran with output then ssh exits.

Once a valid ssh session has been created the special command pythonista [get|put|edit] file1 [file2]
can be used. Use pythonista -h for more info

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
import os
import re
import threading
import time

import console
from paramiko import AutoAddPolicy, SSHClient


def get_pyte():
    import tempfile
    commands = '''
    echo StaSh ssh installing pyte...
    wget https://codeload.github.com/selectel/pyte/zip/master -o ~/Documents/site-packages/pyte.zip
    mkdir ~/Documents/site-packages/pyte_folder
    unzip ~/Documents/site-packages/pyte.zip -d ~/Documents/site-packages/pyte_folder
    rm -r ~/Documents/site-packages/pyte.zip
    mv ~/Documents/site-packages/pyte_folder/pyte ~/Documents/site-packages/
    rm -r ~/Documents/site-packages/pyte_folder
    echo done
    '''
    temp = tempfile.NamedTemporaryFile()
    try:
        temp.write(commands)
        temp.seek(0)
        globals()['_stash'].runtime.exec_sh_file(temp.name)
    finally:
    # Automatically cleans up the file
        temp.close()

try:
    import pyte
except:
    print 'pyte module not found.'
    get_pyte()
    import pyte

class StashSSH(object):

    def __init__(self):
        self.ssh_running = False
        self.screen = pyte.screens.DiffScreen(100,60)
        self.screen.dirty.clear()
        #self.screen.set_mode(pyte.modes.DECTCEM)
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)
        self.pause_output = False

    def connect(self,host='', passwd=None, port=22):
        print 'Connecting...'
        self.user, self.host = self.parse_host(host)
        self.stash = globals()['_stash']
        self.passwd = passwd
        self.port = port
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        try:
            print 'Looking for SSH keys...'
            self.ssh.connect(self.host,
                            username=self.user,
                            password=self.passwd,
                            port=self.port,
                            key_filename=self.find_ssh_keys())
        except:
            try:
                print 'No SSH key found. Trying password...'
                self.ssh.connect(self.host,
                                 username=self.user,
                                 password=self.passwd,
                                 port=self.port)
            except:
                print '*Auth Error*'
                return False
        self.ssh_running = True
        return True

    def find_ssh_keys(self):
        files = []
        APP_DIR = os.environ['STASH_ROOT']
        for file in os.listdir(APP_DIR+'/.ssh'):
            if '.' not in file:
                files.append(APP_DIR+'/.ssh/'+file)
        return files

    def parse_host(self,arg):
        user,host = arg.split('@')
        #host, path = temp.split(':')
        return user, host

    def stdout_thread(self):
        while self.ssh_running:
            if self.chan.recv_ready() and not self.pause_output:
                #output += self.chan.recv(1024)
                rcv = self.chan.recv(1024)
                self.stream.feed(u'%s'%rcv)
            if self.screen.dirty:
                self.screen.dirty.clear()
                self.update_screen()

    def update_screen(self):
        count = len(self.screen.display)
        for item in reversed(self.screen.display):
            if str(item) != ' '*100:
                break
            count -=1
        text = '\n'.join(self.screen.display[:count]).rstrip() + ' '
        self.stash.term.truncate(0, flush=False)
        self.stash.term.write(text)

    def single_exec(self,command):
        sin,sout,serr = self.ssh.exec_command(command)
        for line in sout.readlines():
            line = line.replace('\n','')
        for line in serr.readlines():
            print line.replace('\n','')

    def get_remote_path(self):
        self.pause_output = True
        self.chan.send('pwd \n')
        while True:
            if self.chan.recv_ready():
                rcv = self.chan.recv(1024)
                #print ' '.join([str((ord(a),a)) for a in rcv])
                #print ' '.join([a for a in rcv])
                res = re.search(r'pwd ?\r\n(.*)\r\n',rcv)
                path = res.group(1)
                self.pause_output = False
                break
        return path+'/'


    def get_file(self,remote, local):
        sftp = self.ssh.open_sftp()
        path = self.get_remote_path()
        sftp.get(path+remote,local)
        sftp.close()
        print 'File transfered.'

    def put_file(self,local,remote):
        sftp = self.ssh.open_sftp()
        path = self.get_remote_path()
        sftp.put(local,path+remote)
        sftp.close()
        print 'File transfered.'

    def edit_file(self,remote_file):
        import tempfile
        import runpy
        import editor

        try:
            temp = tempfile.NamedTemporaryFile(dir=os.path.expanduser('~/Documents'), suffix='.py')
            cur_path = editor.get_path()
            sftp = self.ssh.open_sftp()
            path = self.get_remote_path()
            res = sftp.getfo(path+remote_file,temp)
            #editor.open_file(temp.name)
            temp.seek(0)
            print '***When you are finished editing the file, you must come back to console to confirm changes***'
            editor.open_file(temp.name)
            time.sleep(1.5)
            console.hide_output()
            input = raw_input('Save Changes? Y,N: ')
            editor.open_file(cur_path)
            if input == 'y' or input =='Y':
                with open(temp.name,'r') as f:
                    sftp.putfo(f,path+remote_file)
                    print 'File transfered.'
        except Exception, e:
            print e
        finally:
            temp.close()
        #
        #temp.write(file.read())


    def interactive(self):
        self.transport = self.ssh.get_transport()
        self.chan = self.transport.open_session()
        self.chan.get_pty()
        self.chan.set_combine_stderr(True)
        self.chan.exec_command('bash -s')
        t1 = threading.Thread(target=self.stdout_thread)
        t1.start()
        while True:
            if self.chan.send_ready():
                tmp = raw_input()
                ssh_args = tmp.split(' ')
                if ssh_args[0] == 'exit':
                    self.exit()
                    break
                # sftp to and from pythonista
                elif ssh_args[0] == 'pythonista':
                    ssh_args.pop(0)
                    try:
                        tmp = argparse.ArgumentParser()
                        tmp.add_argument('type', choices=('get','put', 'edit','test'),help='Mode: [get|put|edit]')
                        tmp.add_argument('file1', action='store',help='put: local file. get: remote file. edit: remote file')
                        tmp.add_argument('file2', action='store',nargs='?', help='get: local file, put: remote file path, edit: blank')
                        ssh_args = tmp.parse_args(ssh_args)

                        if ssh_args.type == 'put':
                            self.put_file(ssh_args.file1,ssh_args.file2)
                        elif ssh_args.type == 'get':
                            self.get_file(ssh_args.file1,ssh_args.file2)
                        elif ssh_args.type == 'edit':
                            self.edit_file(ssh_args.file1)
                        elif ssh_args.type == 'test':
                            self.get_remote_path()
                    #pass to avoid invalid arguments from exiting ssh.
                    except:
                        pass

                else:
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
