# coding: utf-8
'''Creates a zip archive of your Pythonista files and serves them via HTTP in your local network.'''

import sys
if sys.version_info[0] >= 3:
	from http.server import SimpleHTTPRequestHandler, HTTPServer
else:
	from SimpleHTTPServer import SimpleHTTPRequestHandler
	from BaseHTTPServer import HTTPServer

import os, shutil, tempfile, console
import socket

PORT = 8080

def get_ip_address():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(('google.com', 80))
	ip_address = s.getsockname()[0]
	s.close()
	return ip_address

def main():
	doc_path = os.path.expanduser('~/Documents')
	os.chdir(doc_path)
	backup_path = os.path.join(doc_path, 'Backup.zip')
	if os.path.exists(backup_path):
		os.remove(backup_path)
	print('Creating backup archive...')
	shutil.make_archive(os.path.join(tempfile.gettempdir(), 'Backup'), 'zip')
	shutil.move(os.path.join(tempfile.gettempdir(), 'Backup.zip'), backup_path)
	print('Backup archive created, starting HTTP server...\n')
	local_url = 'http://localhost:%i/Backup.zip' % (PORT,)
	wifi_url = 'http://%s:%i/Backup.zip' % (get_ip_address(), PORT)
	server = HTTPServer(('', PORT), SimpleHTTPRequestHandler)
	console.clear()
	print('You can tap the following link to open the backup Zip archive in Safari (from where you can transfer it to other apps on this device):')
	console.write_link(local_url + '\n', 'safari-' + local_url)
	print('\nIf you want to transfer the backup to another device in your local WiFi network, enter the following URL in a web browser on the other device:')
	print(wifi_url)
	print('\n====\nTap the stop button in the editor or console when you\'re done.')
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.shutdown()
		server.socket.close()
		print('Server stopped')

if __name__ == '__main__':
	main()
