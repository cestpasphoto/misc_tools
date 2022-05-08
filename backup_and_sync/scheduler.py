#!/usr/bin/python3

import threading
import multiprocessing
from multiprocessing import shared_memory
import time
import json
import subprocess
import os
import sys
import argparse
import pickle
from datetime import datetime, timedelta


timestamps_file = '/root/anabest.json'
nb_threads = 4
max_default_duration = 4 # minutes
ratio_long_pending_jobs = 2.0 # First run tasks that have waited since long time = 2x requested period

o_bborg = '/usr/local/sbin/bborg.py'
def t_bborg(s): return 'ssh serveur "/usr/local/sbin/bborg.py ' + s + '"'
jobs_todo = [
	# High priority first                      Ottokar borg-perso v  v Tharkey SSD read         v 'h' for wallclock Hours, 'r'' for Runtime hours
	#                                      Ottokar borg-public v  ¦  |  v Tharkey HDD read
	#                                   Ottokar borg-system v  |  ¦  |  ¦  v Tharkey borg-system
	#                                   Ottokar HDD read v  ¦  |  ¦  |  ¦  |  v Tharkey borg-public
	#                                Ottokar SSD read v  |  ¦  |  ¦  |  ¦  |  ¦  v Tharkey borg-perso
	# Weekly tasks (remote)                           ¦  |  ¦  |  ¦  |  ¦  |  ¦  | 	
	{'name': 'backupT.toO.block'      , 'resources': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0], 'freq': '300h', 'max_seconds': 200 , 'cmd': f'{t_bborg("backup -t remote_block -q")}'},
	{'name': 'backupT.toO.othersHDD'  , 'resources': [0, 0, 0, 0, 1, 0, 1, 0, 0, 0], 'freq': '140h', 'max_seconds': 30  , 'cmd': f'{t_bborg("backup -t remote_othersHDD -q")}'},
	{'name': 'backupT.toO.perso'      , 'resources': [0, 0, 0, 0, 1, 0, 1, 0, 0, 0], 'freq': '140h', 'max_seconds': 20  , 'cmd': f'{t_bborg("backup -t remote_perso -q")}'},
	{'name': 'backupT.toO.public'     , 'resources': [0, 0, 0, 1, 0, 0, 1, 0, 0, 0], 'freq': '140h', 'max_seconds': 40  , 'cmd': f'{t_bborg("backup -t remote_public -q")}'},
	{'name': 'backupO.toT.block'      , 'resources': [1, 0, 0, 0, 0, 0, 0, 1, 0, 0], 'freq':  '18r', 'max_seconds': 250 , 'cmd': f'{o_bborg} backup -t remote_block -q'},
	{'name': 'backupO.toT.perso'      , 'resources': [0, 1, 0, 0, 0, 0, 0, 0, 0, 1], 'freq':   '8r', 'max_seconds': 70  , 'cmd': f'{o_bborg} backup -t remote_perso -q'},
	{'name': 'backupO.toT.public'     , 'resources': [0, 1, 0, 0, 0, 0, 0, 0, 1, 0], 'freq':  '12r', 'max_seconds': 20  , 'cmd': f'{o_bborg} backup -t remote_public -q'},
	{'name': 'backupO.toT.VM'         , 'resources': [1, 0, 0, 0, 0, 0, 0, 1, 0, 0], 'freq':  '12r', 'max_seconds': 60  , 'cmd': f'{o_bborg} backup -t remote_VM -q'},
	# Daily tasks (remote)                            ¦  |  ¦  |  ¦  |  ¦  |  ¦  |
	#{'name':'backupT.toO.daily.data' , 'resources': [0, 0, 0, 1, 0, 1, 0, 0, 0, 0], 'freq':  '70h', 'max_seconds': 1000, 'cmd': f'{t_bborg("backup -t remote_downloads -q")}'},
	{'name': 'backupO.toT.home'       , 'resources': [1, 0, 0, 0, 0, 0, 0, 0, 0, 1], 'freq':   '3r', 'max_seconds': 50  , 'cmd': f'{o_bborg} backup -t remote_home -q'},
	{'name': 'backupO.toT.fs'         , 'resources': [1, 0, 0, 0, 0, 0, 0, 1, 0, 0], 'freq':   '3r', 'max_seconds': 40  , 'cmd': f'{o_bborg} backup -t remote_fs -q'},
	{'name': 'backupO.toT.bootefi'    , 'resources': [1, 0, 0, 0, 0, 0, 0, 1, 0, 0], 'freq':   '6r', 'max_seconds': 15  , 'cmd': f'{o_bborg} backup -t remote_bootefi -q'},
	{'name': 'backupO.toT.efi'        , 'resources': [1, 0, 0, 0, 0, 0, 0, 1, 0, 0], 'freq':   '6r', 'max_seconds': 15  , 'cmd': f'{o_bborg} backup -t remote_efi -q'},
	{'name': 'backupO.toT.disk'       , 'resources': [1, 0, 0, 0, 0, 0, 0, 1, 0, 0], 'freq':   '6r', 'max_seconds': 15  , 'cmd': f'{o_bborg} backup -t remote_disk -q'},
	{'name': 'backupT.toO.home'       , 'resources': [0, 0, 0, 0, 1, 1, 0, 0, 0, 0], 'freq':  '20h', 'max_seconds': 60  , 'cmd': f'{t_bborg("backup -t remote_home -q")}'},
	{'name': 'backupT.toO.fs'         , 'resources': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0], 'freq':  '20h', 'max_seconds': 120 , 'cmd': f'{t_bborg("backup -t remote_fs -q")}'},
	{'name': 'backupT.toO.bootefi'    , 'resources': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0], 'freq':  '50h', 'max_seconds': 30  , 'cmd': f'{t_bborg("backup -t remote_bootefi -q")}'},
	{'name': 'backupT.toO.efi'        , 'resources': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0], 'freq':  '50h', 'max_seconds': 15  , 'cmd': f'{t_bborg("backup -t remote_efi -q")}'},
	{'name': 'backupT.toO.disk'       , 'resources': [0, 0, 1, 0, 0, 1, 0, 0, 0, 0], 'freq':  '50h', 'max_seconds': 50  , 'cmd': f'{t_bborg("backup -t remote_disk -q")}'},
	# Weekly tasks (local)                            ¦  |  ¦  |  ¦  |  ¦  |  ¦  | 	
	{'name': 'backupO.toB'            , 'resources': [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], 'freq': '600h', 'max_seconds': 70  , 'cmd': f'{o_bborg} backup -t borgbase -q'},
	{'name': 'backupO.toO.block'      , 'resources': [1, 0, 1, 0, 0, 0, 0, 0, 0, 0], 'freq':  '18r', 'max_seconds': 250 , 'cmd': f'{o_bborg} backup -t block -q'},
	{'name': 'backupO.toO.perso'      , 'resources': [0, 1, 0, 0, 1, 0, 0, 0, 0, 0], 'freq':   '8r', 'max_seconds': 20  , 'cmd': f'{o_bborg} backup -t perso -q'},
	{'name': 'backupO.toO.VM'         , 'resources': [1, 0, 1, 0, 0, 0, 0, 0, 0, 0], 'freq':  '12r', 'max_seconds': 40  , 'cmd': f'{o_bborg} backup -t VM -q'},
	{'name': 'monitor.sizes.onO.root' , 'resources': [0, 0, 1, 0, 0, 0, 0, 0, 0, 0], 'freq':  '31r', 'max_seconds': 20  , 'cmd': f'{o_bborg} monitor -t fs'},
	{'name': 'monitor.sizes.onO.home' , 'resources': [0, 0, 0, 0, 1, 0, 0, 0, 0, 0], 'freq':  '33r', 'max_seconds': 20  , 'cmd': f'{o_bborg} monitor -t home'},
	# Daily tasks (local)                             ¦  |  ¦  |  ¦  |  ¦  |  ¦  |
	{'name': 'backupO.toO.home'       , 'resources': [1, 0, 0, 0, 1, 0, 0, 0, 0, 0], 'freq':   '3r', 'max_seconds': 80  , 'cmd': f'{o_bborg} backup -t home -q'},
	{'name': 'backupO.toO.fs'         , 'resources': [1, 0, 1, 0, 0, 0, 0, 0, 0, 0], 'freq':   '3r', 'max_seconds': 50  , 'cmd': f'{o_bborg} backup -t fs -q'},
	{'name': 'backupO.toO.bootefi'    , 'resources': [1, 0, 1, 0, 0, 0, 0, 0, 0, 0], 'freq':   '6r', 'max_seconds': 15  , 'cmd': f'{o_bborg} backup -t bootefi -q'},
	{'name': 'backupO.toO.efi'        , 'resources': [1, 0, 1, 0, 0, 0, 0, 0, 0, 0], 'freq':   '6r', 'max_seconds': 15  , 'cmd': f'{o_bborg} backup -t efi -q'},
	{'name': 'backupO.toO.disk'       , 'resources': [1, 0, 1, 0, 0, 0, 0, 0, 0, 0], 'freq':   '6r', 'max_seconds': 20  , 'cmd': f'{o_bborg} backup -t disk -q'},
	# Other tasks (too long to fit in daily runs)     ¦  |  ¦  |  ¦  |  ¦  |  ¦  |
	{'name': 'prune.backupO.onO'      , 'resources': [0, 1, 1, 1, 1, 0, 0, 0, 0, 0], 'freq':  '24r', 'max_seconds': 250 , 'cmd': f'{o_bborg} prune --actually-delete -q'},
	{'name': 'prune.backupO.onT'      , 'resources': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1], 'freq':  '24r', 'max_seconds': 400 , 'cmd': f'{o_bborg} prune -t remote_all --actually-delete -q'},
	{'name': 'prune.backupT.onO'      , 'resources': [0, 1, 1, 1, 1, 0, 0, 0, 0, 0], 'freq':  '24r', 'max_seconds': 600 , 'cmd': f'{t_bborg("prune -t remote_all --actually-delete -q")}'},
	{'name': 'check.backup.onO.system', 'resources': [0, 1, 1, 0, 0, 0, 0, 0, 0, 0], 'freq': '100r', 'max_seconds': 200 , 'cmd': f'{o_bborg} check -t fs -q'},
	{'name': 'check.backup.onO.perso' , 'resources': [0, 1, 0, 0, 1, 0, 0, 0, 0, 0], 'freq': '100r', 'max_seconds': 200 , 'cmd': f'{o_bborg} check -t perso -q'},
	{'name': 'check.backup.onO.public', 'resources': [0, 1, 0, 1, 0, 0, 0, 0, 0, 0], 'freq': '200r', 'max_seconds': 3000, 'cmd': f'{o_bborg} check -t public -q'},
]

_lock = multiprocessing.Lock()

# retourne job à faire
# None si aucun job ne va
def look_for_job(shared_mem):
	shared_dict = read_from_memory(shared_mem)
	# If deadline is passed
	if not shared_dict['jobs_todo']:
		return None
	# Or sure to be passed
	expect_end_times = [timedelta(seconds=job['max_seconds'])+datetime.now() for job in shared_dict['jobs_todo']]
	if min(expect_end_times) > shared_dict['end']:
		print(f"Deadline passed, remove pending jobs: {[job['name'] for job in shared_dict['jobs_todo']]}")
		shared_dict['jobs_todo'] = []
		set_to_memory(shared_mem, shared_dict)
		return None


	def set_env_before_starting_job(job, resources_needed):
		shared_dict['resources_used'] = resources_needed
		shared_dict['jobs_todo'].remove(job)
		shared_dict['ongoing_jobs'].append(job['name'])
		who_modifies = 'by_serveur' if job['cmd'].startswith('ssh serveur') else 'by_ottokar'
		shared_dict['repo_modified'][who_modifies] += [r for r in [2,3,4,7,8,9] if job['resources'][r]] # Modified repos
		set_to_memory(shared_mem, shared_dict)

	# Reorder tasks: first start long-pending tasks, then long tasks (even longer than allowed), then usual tasks in order if time compatible
	high_priority_tasks = [job for job in shared_dict['jobs_todo'] if job['elapsed']/int(job['freq'][:-1]) >  ratio_long_pending_jobs]
	other_tasks         = [job for job in shared_dict['jobs_todo'] if job['elapsed']/int(job['freq'][:-1]) <= ratio_long_pending_jobs]
	if (datetime.now() - shared_dict['start']).seconds < 30: # start long tasks only if at beginning
		high_priority_tasks += [job for job in other_tasks if job['max_seconds'] >= max_default_duration*60]
		other_tasks          = [job for job in other_tasks if job['max_seconds'] <  max_default_duration*60]
	# Filter out too long tasks only for the low priority ones
	for job in other_tasks:
		if (datetime.now() + timedelta(seconds=job['max_seconds'])) > shared_dict['end']:
			# print(f"Job {job['name']} could have been done, but it may exceed maximum allocated time")
			shared_dict['jobs_todo'].remove(job)
			set_to_memory(shared_mem, shared_dict)
			other_tasks.remove(job)
	tasks_in_order = high_priority_tasks + other_tasks

	# Now, run the first task than can be ran
	for job in tasks_in_order:
		resources_needed = [a+b for a,b in zip(shared_dict['resources_used'], job['resources'])]
		is_supported = all([a<=b for a,b in zip(resources_needed, shared_dict['max_resources'])])
		if is_supported:
			set_env_before_starting_job(job, resources_needed)
			return job
	return None

def end_of_job(my_job, succeeded, shared_mem):
	shared_dict = read_from_memory(shared_mem)
	shared_dict['resources_used'] = [a-b for a,b in zip(shared_dict['resources_used'], my_job['resources'])]
	shared_dict['jobs_done'].append(my_job['name'])
	if my_job['name'] in shared_dict['ongoing_jobs']:
		shared_dict['ongoing_jobs'].remove(my_job['name'])
	set_to_memory(shared_mem, shared_dict)

	if succeeded:
		timestamps = json.load(open(timestamps_file, 'r'))
		timestamps[my_job['name']] = [int(time.time()), get_runtime()]
		with open(timestamps_file, 'w') as file:
			json.dump(timestamps, file, indent=2, sort_keys=True)

def do_job(thread_name, verbosity, memory_name):
	shared_mem = shared_memory.SharedMemory(memory_name)
	shared_dict = read_from_memory(shared_mem)
	jobs_todo = shared_dict['jobs_todo']
	while jobs_todo:
		# Take job
		my_job = None
		while my_job is None:
			with _lock:
				my_job = look_for_job(shared_mem)
				jobs_todo = read_from_memory(shared_mem)['jobs_todo']
			if my_job is None:
				if not jobs_todo or not shared_dict['ongoing_jobs']:
					return
				time.sleep(2)

		# Do it
		if verbosity >= 2:
			shared_dict = read_from_memory(shared_mem)
			print(f"[T{thread_name}] {my_job['name']:<25}  Overall using resources {shared_dict['resources_used']} for jobs {shared_dict['ongoing_jobs']}")
		# print('NOT DOING THE JOB')
		# import random
		# status = subprocess.run(f'sleep {random.randint(1,5)}', shell=True, capture_output=True)
		start_time = time.time()
		status = subprocess.run(my_job['cmd'], shell=True, capture_output=True)
		duration = time.time() - start_time

		# Free resources
		if duration > my_job['max_seconds'] * 1.5:
			print(f"Warning, {my_job['name']} took more time than expected: {int(duration+0.5)}s instead of <{my_job['max_seconds']}s")
		elif duration < my_job['max_seconds'] / 1.5 and status.returncode == 0:
			print(f"Warning, {my_job['name']} took much less time than expected: {int(duration+0.5)}s instead of up to {my_job['max_seconds']}s")
		with _lock:
			if status.returncode != 0:
				print(f"*** {my_job['name']} status={status.returncode} ***")
			if len(status.stdout) > 2:
				print(status.stdout.decode("utf-8"), end='')
			if len(status.stderr) > 2:
				print(status.stderr.decode("utf-8"), end='')
			end_of_job(my_job, status.returncode==0, shared_mem)
			jobs_todo = read_from_memory(shared_mem)['jobs_todo']

	shared_mem.close()

def get_runtime():
	tuptime = subprocess.run(['tuptime', '--power', '--seconds', '--csv'], capture_output=True)
	tuptime_stdout = tuptime.stdout.decode('utf-8')
	runtime_value = int(tuptime_stdout.splitlines()[3].split(',')[-1].split(' ')[1])
	return runtime_value

def get_uptime():
	tuptime = subprocess.run(['tuptime', '--seconds', '--csv'], capture_output=True)
	tuptime_stdout = tuptime.stdout.decode('utf-8')
	uptime_value = int(tuptime_stdout.splitlines()[-1].split(',')[1][1:-1])
	return uptime_value

def define_jobs(jobs_todo, verbosity=2):
	try:
		timestamps = json.load(open(timestamps_file, 'r'))
	except:
		with open(timestamps_file, 'w') as file:
			json.dump({}, file, indent=2, sort_keys=True)
		timestamps = {}
	epoch_now, runtime_now = int(time.time()), get_runtime()

	try:
		x = timestamps[jobs_todo[0]['name']][0]
	except:
		print('Erreur pendant la lecture timestamps, correction')
		timestamps = { k:[v, 0] for k,v in timestamps.items() }
		with open(timestamps_file, 'w') as file:
			json.dump(timestamps, file, indent=2, sort_keys=True)

	if verbosity >= 2:
		print(f"{'Name':<25} {'Elapsed':>7} ({'Freq':<4})")
	for job in jobs_todo:
		freq_hours = int(job['freq'][:-1])
		freq_type  =     job['freq'][-1]

		if freq_type == 'h':
			job['elapsed'] = (epoch_now   - timestamps.get(job['name'], [0,0])[0]) // 3600
		else:
			job['elapsed'] = (runtime_now - timestamps.get(job['name'], [0,0])[1]) // 3600
		job['remaining'] = freq_hours - job['elapsed']

		if verbosity >= 2 and job['elapsed'] > freq_hours*0.75:
			print(f"{job['name']:<25}", end='')
			print(f"{'*' if job['remaining'] <= 0 else ' '}", end='')
			print(f"{job['elapsed']:>7} ({job['freq']:<4})")

	# Ne garder que les jobs qui doivent etre lances
	jobs_todo = [job for job in jobs_todo if job['remaining'] <= 0]
	if verbosity >= 2:
		print(f"Jobs: {[j['name'] for j in jobs_todo]}")

	return jobs_todo

def set_to_memory(shared_mem, data):
	pickle_data = pickle.dumps(data)
	n = len(pickle_data)
	# print(f'pickle size = {n}')
	shared_mem.buf[:n] = pickle_data

def read_from_memory(shared_mem):
	return pickle.loads(shared_mem.buf)

def sync_cache(local_execution, repos_to_update):
	# info about remote computer first, and bigger repo first
	remote_repo  = ['/backup/serveur/system/', '/backup/public/publicdata/', '/backup/serveur/perso/']
	local_repo  = ['/backup/ottokar/system/', '/backup/public/publicdata/', '/backup/ottokar/perso/']
	remote_name = 'serveur'
	if not local_execution:
		remote_repo, local_repo = local_repo, remote_repo
		who_to_ssh, remote_name = 'serveur', 'ottokar'
	all_commands = [
		f"borg info root@{remote_name}:{remote_repo[0]}",
		f"borg info root@{remote_name}:{remote_repo[1]}",
		f"borg info root@{remote_name}:{remote_repo[2]}",
		f"borg info {local_repo[0]}",
		f"borg info {local_repo[1]}",
		f"borg info {local_repo[2]}",
	]

	# convert format of repos_to_update
	repos_to_update_newformat = [(r-2) if r < 5 else (r-4) for r in repos_to_update] # 2,3,4 -> 0,1,2 (ottokar),  7,8,9 -> 3,4,5 (serveur)
	if local_execution: # Switch 0,1,2 and 3,4,5 if running on ottokar to match order of all_commands
		repos_to_update_newformat = [(r+3) if r<3 else (r-3) for r in repos_to_update_newformat]
	
	# execute command when associated repo has been modified
	for i in range(len(all_commands)):
		if i in repos_to_update_newformat:
			cmd = f"ssh {who_to_ssh} '{all_commands[i]}'" if not local_execution else all_commands[i]
			# print(cmd)
			status = subprocess.run(cmd, shell=True, capture_output=True)
	

if __name__ == "__main__":
	if not os.geteuid() == 0:
		sys.exit("\nOnly root can run this script\n")
	
	parser = argparse.ArgumentParser(description='scheduler')
	verbos = parser.add_mutually_exclusive_group()
	verbos.add_argument('-v'             , action='count', default=2   , help='increase verbosity')
	verbos.add_argument('-q'             , action='count', default=0   , help='decrease verbosity')
	parser.add_argument('--force' , '-f' , action='store', default=None, help='force execute task')
	parser.add_argument('--long'  , '-L' , action='store_true'         , help='Execute all tasks, whatever maximum duration is')
	parser.add_argument('--hourly', '-H' , action='store_true'         , help='Execute short and long tasks (default)')
	args = parser.parse_args()
	args.v -= args.q

	if args.hourly and get_uptime() < 1800:
		if args.v >= 2:
			print('Too soon after boot to start the "hourly" version')
		exit()

	if args.force:
	 	jobs_todo = [j for j in jobs_todo if j['name']==args.force]
	jobs_todo = define_jobs(jobs_todo, args.v)
	start_time = datetime.now()
	end_time = datetime.max if args.long or args.force else (start_time + timedelta(minutes=max_default_duration))
	shared_mem = shared_memory.SharedMemory(create=True, size=10000)
	set_to_memory(shared_mem, {'resources_used': [0]*10, 'max_resources': [1]*10, 'ongoing_jobs': [], 'jobs_done': [], 'jobs_todo': jobs_todo, 'start': start_time, 'end': end_time, 'repo_modified': {'by_ottokar': [], 'by_serveur': []}})

	threads = []
	for index in range(nb_threads):
		x = multiprocessing.Process(target=do_job, args=(index,args.v,shared_mem.name,))
		threads.append(x)
		x.start()
	for index, thread in enumerate(threads):
		thread.join()

	shared_dict = read_from_memory(shared_mem)
	print()
	print(f"now={datetime.now().time()} vs max_end={shared_dict['end'].time()}, and fyi start={shared_dict['start'].time()}")
	# print('modified repos:', shared_dict['repo_modified'])

	print('Syncing caches of both computers')
	for index in range(2):
		local_execution = index%2
		other_computer = 'by_serveur' if local_execution else 'by_ottokar'
		x = multiprocessing.Process(target=sync_cache, args=(local_execution, shared_dict['repo_modified'][other_computer]))
		threads.append(x)
		x.start()
	for index, thread in enumerate(threads):
		thread.join()
	
	shared_mem.unlink()
	shared_mem.close()
	print(f"now={datetime.now().time()}")

