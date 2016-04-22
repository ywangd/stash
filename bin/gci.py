# coding: utf-8
"""interface to pythons built-in garbage collector

Warning: this command may crash StaSh. Only use it if you know what dou are doing!"""
import gc,argparse,sys

def main():
	parser=argparse.ArgumentParser(description="access to pythons built-in garbage collector")
	parser.add_argument("command",help="what to do",choices=["enable","disable","status","collect","threshold","debug","break"],action="store")
	parser.add_argument("args",help="argument for command",action="store",nargs="*")
	ns=parser.parse_args()
	if ns.command=="enable":
		gc.enable()
	elif ns.command=="disable":
		gc.disable()
	elif ns.command=="collect":
		gc.collect()
	elif ns.command=="status":
		print "GC enabled:              {s}".format(s=gc.isenabled())
		tracked=gc.get_objects()
		n=len(tracked)
		print "Tracked objects:         {n}".format(n=n)
		size=sum([sys.getsizeof(e) for e in tracked])
		del tracked#this list may be big, better delete it
		print "Size of tracked objects: {s} bytes".format(s=size)
		print "Garbage:                 {n}".format(n=len(gc.garbage))
		gsize=sum([sys.getsizeof(e) for e in gc.garbage])
		print "Size of garbage:         {s} bytes".format(s=gsize)
		print "Debug:                   {d}".format(d=gc.get_debug())
	elif ns.command=="threshold":
		if len(ns.args)==0:
			print "Threshold:\n   G1: {}\n   G2: {}\n   G3: {}".format(*gc.get_threshold())
		elif len(ns.args)>3:
			print "Error: to many arguments for threshold!"
			sys.exit(1)
		else:
			try:
				ts=tuple([int(e) for e in ns.args])
			except ValueError:
				print "Error: expected arguments to be integer!"
				sys.exit(1)
			gc.set_threshold(*ts)
	elif ns.command=="debug":
		if len(ns.args)==0:
			print "Debug: {d}".format(d=gc.get_debug())
		elif len(ns.args)==1:
			try:
				flag=int(ns.args[0])
			except ValueError:
				print "Error: expected argument to be an integer!"
				sys.exit(1)
			gc.set_debug(flag)
		else:
			print "Error: expected exactly one argument for threshold!"
			sys.exit(1)
	elif ns.command=="break":
		if len(gc.garbage)==0:
			print "Error: No Garbage found!"
			sys.exit(1)
		else:
			for k in dir(garbage[0]):
				try: delattr(garbage,k)
				except: pass
			del gc.garbage[:]

if __name__=="__main__":
	main()
