'''
Send messages/files from stash.

Calling mail without params will prompt for input.
Passing '-' in the message param will read from stdin pipe.

usage: mail.py [-h] [-s SUBJECT] [-v] [-f FILE] [-e] [sendto] [message]

positional arguments:
  sendto                Send email to.
  message               Email Message. Passing '-' will pass stdin from pipe.

optional arguments:
  -h, --help            show this help message and exit
  -s SUBJECT, --subject SUBJECT
                        Email Subject.
  -v, --verbose         Verbose print
  -f FILE, --file FILE  Attachment to send.
  -e                    Edit .mailrc
'''
from __future__ import print_function

import argparse
import os
import smtplib
import sys
from email import encoders
from email.utils import formatdate

from six.moves import input
from six.moves.configparser import RawConfigParser
from six.moves.email_mime_base import MIMEBase
from six.moves.email_mime_multipart import MIMEMultipart
from six.moves.email_mime_text import MIMEText

APP_DIR = os.environ['STASH_ROOT']


class Mail(object):
    def __init__(self,cfg_file='',verbose=False):
        #from config
        self.cfg_file = cfg_file
        self.verbose  = verbose
        self.user     = ''
        self.passwd   = ''
        self.auth     = False
        self.mailfrom = ''
        self.host     = 'smtp.fakehost.com'
        self.port     = 537
        self.tls      = False
        self.read_cfg()
        
    def _print(self,msg):
        if self.verbose:
            print(msg)
            
    def read_cfg(self):
        parser = RawConfigParser()
        parser.read(self.cfg_file)
        if not parser.has_section('mail'):
            print('Creating cfg file.')
            self.make_cfg()
        
        self.auth     = parser.get('mail','auth')
        self.user     = parser.get('mail','username')
        self.passwd   = parser.get('mail','password')
        self.mailfrom = parser.get('mail','mailfrom')
        self.host     = parser.get('mail','host')
        self.port     = parser.get('mail','port')
        self.tls      = parser.get('mail','tls')
            
    def edit_cfg(self):
        global _stash
        _stash('edit -t %s' %self.cfg_file)
        sys.exit(0)
        
    def make_cfg(self):
        cfg='''[mail]
host = smtp.mailserver.com
port = 587
mailfrom = Your email
tls = false
auth = true
username = Your user name
password = Your user password
'''
        with open(self.cfg_file,'w') as f:
            f.write(cfg)
        self.edit_cfg()
        
        
    def send(self,sendto='',
                 subject='',
                 attach='',
                 body=' '): 
        print('Sending email')
        msg = MIMEMultipart()
        msg["From"]    = self.mailfrom
        msg["To"]      = sendto
        msg["Subject"] = subject
        msg['Date']    = formatdate(localtime=True)
        
        #add messagw
        self._print('Attaching msg: %s' %body)
        message = MIMEText('text', "plain")
        message.set_payload(body+'\n')
        msg.attach(message)
        # attach a file
        if attach:
            self._print('Attachment found: %s'% attach)
            part = MIMEBase('application', "octet-stream")
            part.set_payload( open(attach,"rb").read() )
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % attach)
            msg.attach(part)
        
        self._print('Creating SMTP')
        server = smtplib.SMTP(self.host,int(self.port))
        
        if self.tls == 'True' or self.tls == 'true':
            server.starttls()
            self._print('tls started.')
        if self.auth == 'True' or self.auth == 'true':
            try:
                self._print('Logging into to SMTP: %s %s'%(self.user,self.passwd))
                server.login(self.user, self.passwd)  # optional
            except Exception as e:
                print('Failed Login %s'%e)
                sys.exit(0)
            
        else:
            try:
                self._print('Connecting to SMTP')
                server.connect()
            except Exception as e:
                print('Failed to connect %s'%e)
                sys.exit(0)
     
        try:
            self._print('Sending mail to: %s' %sendto)
            server.sendmail(self.mailfrom, sendto, msg.as_string())
            print('mail sent.')
            server.close()
        except Exception as e:
            errorMsg = "Unable to send email. Error: %s" % str(e)
        

 
if __name__ == "__main__":
    CONFIG = APP_DIR+'/.mailrc'
    ap = argparse.ArgumentParser()
    ap.add_argument('-s','--subject',default='',action='store',dest='subject',help='Email Subject.')
    ap.add_argument('-v','--verbose',action='store_true',help='Verbose print')
    ap.add_argument('-f','--file',action='store',default='',help='Attachment to send.')
    ap.add_argument('-e', action='store_true', help='Edit .mailrc',default=False)
    ap.add_argument('sendto',action='store',default='',nargs='?',help='Send email to.')
    ap.add_argument('message',action='store',default='',nargs='?',help='Email Message. Passing \'-\' will pass stdin from pipe.')
    args = ap.parse_args()
    smail = Mail(CONFIG,args.verbose)
    if args.e == True:
        smail.edit_cfg()
    elif args.message or args.file and args.sendto:
        if args.message == '-':
            args.message = sys.stdin.read()
        smail.send(sendto=args.sendto,
                    subject=args.subject,
                    attach=args.file,
                    body=args.message)
    else:
        #try except blocks used do to stash reading EOF on no input
        sendto = input('Send to: ') or None
        if not sendto:
            sys.exit(0)
        subject = input('Subject: ') or ''
        msg = input('Message: ') or ''
        file = input('Attachment: ') or ''
        smail.send(sendto=sendto,
                    subject=subject,
                    attach=file,
                    body=msg)
