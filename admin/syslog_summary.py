#!/usr/bin/env python3
#import sys
#import argparse
import json
import subprocess
#import os
import time

# Some entries are labelled 'warnings' but are actually not --> remove them
def is_false_warning(process, message):
	blacklist = [
		('gdm-x-session'	, '(--)'),
		('gdm-x-session'	, '(II)'),
		('gnome-shell'	        , 'St.Button'),
		('gnome-shell'	        , 'gvc_mixer_card_get_index'),
		('gsd-media-keys'	, 'gvc_mixer_card_get_index'),
		('gsd-media-keys'	, 'Unable to get default sink'),
		('MediaKeys'		, 'libva info'),
		('kernel'		, 'CONNECTOR'),
		('kernel'		, 'DRM'),
		('kernel'		, 'done.'),
		('systemd-xdg-autostart-generator', 'Not generating service for XDG autostart app'),
		('root'			, 'Cannot find default gateway 192.168.1.1 in the network'),
		('root'			, 'ERROR: Duplicate address'),
		('systemd-udevd'	, 'veth'),
		('gnome-shell' 		, 'Gjs_ui_unlockDialog_UnlockDialogClock'),
		('systemd-logind'       , 'used by new audit session, ignoring.'),
		('sshd'                 , 'send_error: write: Connection reset by peer'),
		('sshd'                 , 'kex_exchange_identification'),
		('gnome-shell'          , 'has been already deallocated — impossible'),
	]
	for (bl_proc, bl_msg) in blacklist:
		if bl_proc in process and bl_msg in message:
			return True
	return False

def gather_similar_lines(list_proc_msg):
	dict = {}
	# on rassemble les messages par 'proc'
	for (proc, msg, stamp) in list_proc_msg:
		if proc not in dict:
			dict[proc] = []
		dict[proc].append((msg, int(stamp)//1000000))
	# on rassemble ensuite les messages similaires
	for proc in dict:
		msgs_stamps = dict[proc]
		grouped_msgs = {}
		for (msg, stamp) in msgs_stamps:
			short_msg = msg.translate(str.maketrans('', '', '0123456789'))[:80]
			# grouper par date si possible
			matching_stamps = [short_msg for short_msg in grouped_msgs for (prev_msg, prev_stamp) in grouped_msgs[short_msg] if abs(stamp-prev_stamp)<5]
			if len(matching_stamps) > 0:
				grouped_msgs[matching_stamps[0]].append((msg, stamp))
				continue
			# grouper par msg sinon
			if short_msg not in grouped_msgs:
				grouped_msgs[short_msg] = []
			grouped_msgs[short_msg].append((msg, stamp))
		dict[proc] = grouped_msgs
	# on affiche
	def epoch_to_str(epoch_kernel_str):
		return time.strftime("%a %X", time.localtime(epoch_kernel_str))
	for (proc, msg_type) in dict.items():
		proc_short = proc.split('/')[-1]
		for (msg_short, full_msgs) in msg_type.items():
			print(f'[{proc_short:>12} x{len(full_msgs):<3}] {epoch_to_str(full_msgs[-1][1])} {full_msgs[-1][0][:80]}')

cmd = ['journalctl', '-p', 'warning', '-S', 'yesterday', '-o', 'json']
list_proc_msg = []
for json_line in subprocess.check_output(cmd).decode('utf-8').splitlines():
	line = json.loads(json_line)
	process   = line.get('SYSLOG_IDENTIFIER', line.get('_EXE', ''))
	message   = line.get('MESSAGE', '')
	timestamp = line.get('__REALTIME_TIMESTAMP')
	if is_false_warning(process, message):
		continue
	list_proc_msg.append((process, message, timestamp))
gather_similar_lines(list_proc_msg)
