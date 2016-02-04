'''
sqlite3 shell modeled after sqlite3 command-line.
Created by: Chris Houser (Briarfox)

Use sqlite ?file? to open a database in the shell.
You can pass params to run one command. ex. sqlite test.db .dump > test.sql
'''
import sqlite3
import os
import cmd
import sys

class SqliteCMD(cmd.Cmd):
    '''
    Simple sqlite3 shell
    '''
    prompt = 'sqlite3>'
    def __init__(self, db=None):
        cmd.Cmd.__init__(self)
        self.database = db or ':memory:'
        self.separator = '|'
        self.conn = sqlite3.connect(self.database)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self.commands = []
        self.headers = True
        self.output = sys.stdout

    def preloop(self):
        print 'sqlite3 version %s' % sqlite3.sqlite_version
        print '.(dot) is used for all none sql commands.'
        print 'Use .help for non sqlite command list'
        print 'All sql commands must end with ;'
        if self.database == ':memory:':
            print 'Using database :memory:\nuse .open ?file? to open a database'
        else:
            print 'Using databasse: %s' % self.database

    def do_exit(self,*args):
        '''Exit shell'''
        return True

    def emptyline(self):
        pass

    def command_list(self, command):
        if ';' in command:
            SqliteCMD.prompt = 'sqlite3>'
            self.commands.append(command)
            rtn = ' '.join(self.commands)
            self.commands = []
            return rtn
        else:
            self.commands.append(command)
            SqliteCMD.prompt = '>>>'
            return False

    def display(self, line):
        if self.output == sys.stdout:
            print line
        else:
            with open(self.output, 'a+') as f:
                f.write(line+'\n')

    def do_output(self, line):
        '''.output ?file?
Set output to a file default: stdout'''
        self.output = sys.stdout if line == 'stdout' else line

    def do_separator(self, separator):
        """Set the separator, default: |"""
        self.separator = separator

    def do_headers(self,state):
        '''.headers ?on|off?
Turn headers on or off, default: on'''
        self.headers = state.lower() == 'on':

    def do_dump(self, line):
        '''.dump ?table?
Dumps a database into a sql string
If table is specified, dump that table.
'''
        try:
            if not line:
                for row in self.conn.iterdump():
                    self.display(row)
            else:
                conn = sqlite3.connect(':memory:')    
                cu = conn.cursor()
                cu.execute("attach database '" + self.database + "' as attached_db")
                cu.execute("select sql from attached_db.sqlite_master "
                            "where type='table' and name='" + line + "'")
                sql_create_table = cu.fetchone()[0]
                cu.execute(sql_create_table);
                cu.execute("insert into " + line +
                    " select * from attached_db." + line)
                conn.commit()
                cu.execute("detach database attached_db")
                self.display("\n".join(conn.iterdump()))
        except:
            print 'Invalid table specified'

    def do_backup(self, line):
        '''.backup ?DB? FILE      
Backup DB (default "main") to FILE'''
        with open(self.detabase, 'rb') as f:
            with open(line, 'wb') as new_db:
                new_db.write(f.read())

    def do_clone(self, line):
        '''.clone NEWDB           
Clone data into NEWDB from the existing database'''
        if not os.path.isfile(line):
            try:
                conn = sqlite3.connect(line)
                cur = conn.cursor()
                cur.executescript('\n'.join(self.conn.iterdump()))
                print "Switched to database: %s" % line
                self.conn = conn
                self.cur = cur
            except sqlite3.Error, e:
                print 'There was an error with the clone %s' % e.args[0]

    def do_open(self, line):
        ''' .open ?FILENAME?       
Close existing database and reopen FILENAME
'''
        if line:
            self.database = line
            self.conn = sqlite3.connect(line)
            self.conn.row_factory = sqlite3.Row
            self.cur = self.conn.cursor()

    def do_read(self, line):
        ''' .read FILENAME         
Execute SQL in FILENAME
'''
        if line:
            if os.path.isfile(line):
                with open(line,'r') as f:
                    self.cur.executescript(f.read())
                    self.conn.commit()

    def do_schema(self, line):
        ''' .schema ?TABLE?        
Show the CREATE statements
    If TABLE specified, only show tables matching
    LIKE pattern TABLE.
'''
        try:
            res = self.cur.execute("SELECT * FROM sqlite_master ORDER BY name;")
            if not line:
                for row in res:
                    self.display(row['sql'])
            else:
                for row in res:
                    if row['tbl_name'] == line:
                        self.display(row['sql'])
        except:
            pass

    def do_tables(self, line):
        ''' .tables       
List names of tables
'''
        res = self.cur.execute("SELECT * FROM sqlite_master ORDER BY name;")
        self.display(' '.join([a['tbl_name'] for a in res]))

    def onecmd(self, line):
        """Mostly ripped from Python's cmd.py"""
        if line[:1] == '.':
            cmd, arg, line = self.parseline(line[1:])
        else:
            cmd = None
        if not line:
            return self.emptyline()
        if cmd is None:
            return self.default(line)
        self.lastcmd = line
        if cmd == '':
            return self.default(line)
        else:
            try:
                func = getattr(self, 'do_' + cmd)
            except AttributeError:
                return self.default(line)
            return func(arg)

    def format_print(self, result):
        if self.headers:
            headers = [header[0] for header in self.cur.description]
            self.display(self.separator.join(headers))
        for field in result:
            self.display(self.separator.join(str(x) for x in field))

    def default(self, line):
        try:
            rtn = self.command_list(line)
            if rtn:
                self.cur.execute(rtn)
                self.conn.commit()
                if rtn.lstrip().upper().startswith('SELECT') or rtn.lstrip().upper().startswith('PRAGMA'):
                    self.format_print(self.cur.fetchall())
        except sqlite3.Error, e:
            print e
            print 'An Error occured:', e.args[0]

    def do_EOF(self, line):
        return True

if __name__ == '__main__':
    #sqlitedb = SqliteCMD()
    if len(sys.argv) == 2:
        SqliteCMD(sys.argv[1]).cmdloop()
    elif len(sys.argv) > 2:
        SqliteCMD(sys.argv[1]).onecmd(sys.argv[2])
    else:
        SqliteCMD().cmdloop()
