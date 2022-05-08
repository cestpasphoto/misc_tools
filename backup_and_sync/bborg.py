#!/usr/bin/env python3
import sys
import argparse
import json
import subprocess
import os
from math import log10, pow
from datetime import datetime
from bborg_config import build_configs, borgbase_info, detect_computer, detect_os
import tempfile

glob_archive_max_length = 20



def common_parser():
	parser = argparse.ArgumentParser(description='wrapper around borg-backup')
	parser.add_argument('mode'           , choices=['backup', 'info', 'find', 'diff', 'prune', 'check', 'monitor'] , help='the name of the tool to be used')
	parser.add_argument('--target' , '-t', action='store', default=None                     , help='target to backup/extract ("short" by default)')
	verbos = parser.add_mutually_exclusive_group()
	verbos.add_argument('-v'             , action='count', default=2                        , help='increase verbosity')
	verbos.add_argument('--quiet'  , '-q', action='count', default=0                        , help='decrease verbosity')
	return parser

def break_lock(repo_, verbosity):
	if '@' in repo_:
		if verbosity >= 3:
			print('Cant break lock on remote repo')
		return False
	cmd = ['find', repo_, '-maxdepth', '1', '-mmin', '-60', '-type', 'f']
	recent_files = len(subprocess.check_output(cmd).decode('utf-8').splitlines())
	if recent_files <= 1:
		if verbosity >= 0:
			print(f'Repo {repo_} is old enough, trying to break lock')
		cmd = ['borg', 'break-lock', repo_, '--critical']
		status = subprocess.run(cmd)
		if status.returncode == 0:
			return True
	return False
	

def last_id_in_repo(repo_, verbosity=2, prefix=None, last_one_only=False):
	cmd = ['borg', 'list', repo_, '--critical', '--json']
	if prefix:
		cmd += ['--prefix', prefix]
	if last_one_only:
		cmd += ['--last', '1']

	for try_ in range(2):
		try:
			liste = json.loads(subprocess.check_output(cmd).decode('utf-8'))
		except:
			if try_ > 0:
				if verbosity < 3:
					raise Exception('Could not access '+repo_+', permission issue?', str(cmd)) from None
				else:
					raise Exception('Could not access '+repo_+', permission issue?', str(cmd))
		else:
			break
		break_lock(repo_, verbosity)
	
	def to_int(s):
		try:
			return int(s)
		except:
			return 0
	try:
		all_id    = [ to_int(archive_['name'].split('-')[-1]) for archive_ in liste['archives'] ]
		result = max(all_id)
		if verbosity >= 3:
			print(f'Last archive name = {result}')
		return result
	except:
	 	print('Could not find last id', file=sys.stderr)
	 	return -1

def all_id_of_prefix(repo_, prefix):
	cmd = ['borg', 'list', repo_, '--critical', '--json', '--prefix', prefix]
	try:
		liste = json.loads(subprocess.check_output(cmd).decode('utf-8'))
	except:
		raise Exception('Could not access '+repo_+', permission issue?', str(cmd)) from None
	
	def to_int(s):
		try:
			return int(s)
		except:
			return 0
	all_id = [ to_int(archive_['name'].split('-')[-1]) for archive_ in liste['archives'] ]
	return all_id


###############################################################################

def _backup_item(archive_id, configs, verbosity=2):
	config = configs[archive_id]
	new_id = last_id_in_repo(config['repo'], verbosity) + 1
	archive_name = f'{config["backup_name"]}{str(new_id)}'

	# pre-comp script
	if config['pre_comp']: subprocess.run(config['pre_comp'], shell=True)

	# compression
	full_name = f'"{config["repo"]}"::{archive_name}' if config['is_block'] else f'{config["repo"]}::{archive_name}'
	if config['is_block']:
		cmd  = f'dd if={config["source"]} bs=64M status=none |'
		cmd += f'borg create {"--progress " if verbosity >= 2 else ""}'
		cmd += f'{" ".join(config["comp_opt"])} {full_name} -'
	else:
		cmd  = ['borg', 'create']
		cmd += ['--progress'] if verbosity >= 2 else []
		cmd += config["comp_opt"] + [full_name, config['source']]

	for try_ in range(2):
		try:
			subprocess.run(cmd, check=True, shell=config['is_block'])
		except subprocess.CalledProcessError as e:
			print(f'borg create failed with error code {e.returncode}')
			if e.returncode > 1: 
				if try_ > 0: 
					if verbosity < 3:
						raise Exception('Error during backup_item: '+' '.join(cmd)) from None
					else:
						raise Exception('Error during backup_item: '+' '.join(cmd))
			else:
				break # returncode == 1 means warning
		except:
			if try_ > 0:
				if verbosity < 3:
					raise Exception('Error during backup_item: '+' '.join(cmd)) from None
				else:
					raise Exception('Error during backup_item: '+' '.join(cmd))
		else:
			break
		break_lock(config['repo'], verbosity)

	if verbosity >= 1:
		display_infos(config['repo'], archive=archive_name, short=(verbosity<=2))

	# post-comp script
	_write_last_id(config['backup_name'][:-1], new_id, detect_computer())
	if config['post_comp']: subprocess.run(config['post_comp'], shell=True)

	return archive_name

def _write_last_id(bkp_name, bkp_id, computer):
	def _parse(content):
		parsed = [x.split('=') for x in content if not x.startswith('#') and len(x.split('='))==2]
		parsed_dict = {k: int(v) for (k,v) in parsed}
		return parsed_dict

	def _serialize(parsed_content):
		list_ = [k+'='+str(v) for k,v in parsed_content.items()]
		header = "# This is where we store the ID of last borg archives\n# do NOT MODIFY this file\n\n"
		return header + '\n'.join(sorted(list_)) + '\n'

	db_file, tmp_file = '/root/borg_last_id.txt', '/tmp/borg_last_id.txt'
	remote_db_file = 'root@' + ('ottokar' if computer=='tharkey' else 'tharkey') + ':' + db_file
	#print('DEBUG:', bkp_name, bkp_id, computer, remote_db_file)
	# read locally
	try:
		with open(db_file, 'r') as f:
			content = f.readlines()
	except:
		print('Failure to read last_id file, creating a new one')
		content = []
	local_dict = _parse(content)
	# Insert new iD
	bkp_name = computer.upper() + '_' + bkp_name.upper()
	# if bkp_name not in local_dict.keys():
	# 	print('Backup item', bkp_name, 'is new, adding to the list')
	local_dict[bkp_name] = bkp_id

	# try to read remote and merge it
	try:
		subprocess.run(['scp', remote_db_file, tmp_file], check=True, capture_output=True)
		with open(tmp_file, 'r') as f:
			remote_content = f.readlines()
		remote_ok = True
		remote_dict = _parse(remote_content)
		keys = set(list(local_dict.keys()) + list(remote_dict.keys()))
		local_dict = { k: max(local_dict.get(k, -1), remote_dict.get(k, -1)) for k in keys }
		subprocess.run(['rm', tmp_file])
	except:
		#print('Remote computer not detected')
		remote_ok = False

	# write locally and remotely
	with open(db_file, 'w') as f:
		f.write(_serialize(local_dict))
	if remote_ok:
		subprocess.run(['scp', db_file, remote_db_file], capture_output=True)

def backup():
	parser = common_parser()
	args = parser.parse_args()
	if args.target is None: args.target = 'short'
	args.v -= args.quiet

	configs, groups = build_configs()
	if args.target in configs.keys():
		_backup_item(args.target, configs, verbosity=args.v)
	elif args.target in groups:
		for item in groups[args.target]:
			_backup_item(item, configs, verbosity=args.v)
	elif args.target == 'borgbase':
		borgbase(verbosity=args.v)
	else:
		print('Unknown target')


###############################################################################

def info_parse():
	parser = common_parser()
	parser.add_argument('--last'  , '-l', action='store', type=int, default=10, help='How many archives to print')
	args = parser.parse_args()
	args.v -= args.quiet

	configs, groups = build_configs()
	info(args, configs)

def short_display(infos):
	def display_size(s):
		if s == 0:
			return '  0  B '
		units = ['B ', 'kB', 'MB', 'GB', 'TB']
		unit = int(log10(s*3)/3)
		divided_s = s/pow(10, unit*3)
		return f'{divided_s:3.1f} {units[unit]}'

	def display_date(date_string):
		date = datetime.fromisoformat(date_string)
		age = datetime.now() - date
		if age.days < 1:
			return date.strftime('%H:%M:%S')
		elif age.days < 7:
			return date.strftime('%a %H:%M')
		elif age.days < 365:
			return date.strftime('%b %d')
		return date.strftime('%b %Y')

	def strip_string(s, length):
		if len(s)<=length:
			return s
		return '…'+s[-length:]


	for archive in infos['archives']:
		global glob_archive_max_length
		if len(archive['name']) > glob_archive_max_length:
			glob_archive_max_length = min(len(archive['name']),30)
		big_archive = (archive['stats']['deduplicated_size'] > 0.01*archive['stats']['compressed_size']) and (archive['stats']['deduplicated_size'] > 100000)
		msg = (
			f"{strip_string(archive['name'], glob_archive_max_length):>{glob_archive_max_length}}  "
			f"comp={display_size(archive['stats']['compressed_size']):>8}  "
			f"uniq={display_size(archive['stats']['deduplicated_size']):>8}{'«' if big_archive else ' '} "
			f"date={display_date(archive['end'])+' ('+str(round(archive['duration']))+'s)':<15} "
			f"repo={display_size(infos['cache']['stats']['unique_csize']):>8}"
		)
		print(msg)

def display_infos(repo, archive=None, last=None, short=True, prefix=None):
	if archive:
		cmd =  ['borg', 'info', repo+'::'+archive, '--critical'] + (['--prefix', prefix] if prefix else [])
	elif last:
		cmd =  ['borg', 'info', repo, '--critical', '--last', str(last)] + (['--prefix', prefix] if prefix else [])
	else:
		raise Exception('Archive and Last can be both None') from None

	if short:
		cmd.append('--json')
		try:
			infos = json.loads(subprocess.check_output(cmd).decode('utf-8'))
		except:
			raise Exception('Could not access '+repo+', permission issue?') from None
		short_display(infos)
	else:
		try:
			result = subprocess.check_output(cmd).decode('utf-8')
		except:
			raise Exception('Could not access '+repo+', permission issue?') from None
		print(result)

def info(args, configs):
	if args.target in configs.keys():
		config = configs[args.target]
		display_infos(config['repo'], last=args.last, short=(args.v<=2), prefix=config['backup_name'])
	elif args.target is None:
		for repo in set([ config['repo'] for config in configs.values() if '@' not in config['repo'] ]):
			display_infos(repo, last=args.last, short=(args.v<=2), prefix='')
			print('-'*15)
	else:
		print('Unknown target')

###############################################################################

def find_parse():
	parser = common_parser()
	parser.add_argument('path_or_pattern',              nargs=1, help='Path or pattern to look for')
	parser.add_argument('--last',     '-l', action='store', type=int, default=3, help='How many archives per prefix to look in')
	parser.add_argument('--extract',  '-x', action='store_true' , help='Extract files after showing them (valid only if request is a path, not a pattern)')
	parser.add_argument('--no-suffix','-S', action='store_true' , help='Dont add a suffix when extracting file. Only valid with --extract, and sets --last to 1')
	parser.add_argument('--remote'        , action='store_true' , help='Look for remote files in local archives')
	args = parser.parse_args()
	args.v -= args.quiet

	if args.target is not None:
		print('--target value is not used in find mode')
	if args.no_suffix:
		if args.extract:
			if args.last != 1:
				print('--no-suffix option will force --last to 1')
			args.last = 1
		else:
			print('--no-suffix option has no meaning without --extract, discards it')
	configs, groups = build_configs(other_computer=args.remote)
	_find_core(args.path_or_pattern[0], verbosity=args.v, configs=configs, remote=args.remote, how_many_versions=args.last, force_extract=args.extract, no_suffix=args.no_suffix)

def _find_core(request, verbosity, configs, remote, how_many_versions, force_extract, no_suffix):
	# Guess if pattern or not
	if '/' not in request and '*' not in request:
		request = '*' + request + '*'
		is_pattern = True
		print(f'Request is neither a path, neither a pattern, adding joker on left+right to make it a pattern: "{request}"')
	else:
		is_pattern = '*' in request
		if not is_pattern:
			# Modify symbolic path into real path
			request = os.path.realpath(request)
		if verbosity >= 3:
			print(f'We guessed that {request} is a {"pattern, not a path" if is_pattern else "path, not a pattern"}')

	# Select archives to look in
	prefixes = {c:v for (c,v) in configs.items() if c.startswith('remote_') == remote and not v['is_block'] and v['source'] is not None}
	if not is_pattern:
		prefixes = {c:v for (c,v) in prefixes.items() if request.startswith(v['source'])}
		if len(prefixes) == 0:
			print('Could not guess what is repo for ' + request)
			exit(14)
		longest_prefix = max(prefixes.keys(), key=lambda x: len(prefixes[x]['source']))
		prefixes = {longest_prefix: prefixes[longest_prefix]}
	archives = []
	for (c, v) in prefixes.items():
		repo = v['repo'].split(':')[1] if remote else v['repo']
		list_ids = all_id_of_prefix(repo, v['backup_name'])[-how_many_versions:]
		archives += [ f"{repo}::{v['backup_name']}{id_}".format() for id_ in list_ids ]
	if verbosity >= 3:
		print(f'Looking into following archive(s): {archives}     ')

	# Look into archives and show results
	archives_with_hits = []
	for archive in archives:
		if verbosity >= 1:
			print(f'Looking into  {archive}    \r', end='')
		cmd = ['borg', 'list', '--critical', archive, f'fm:{request}' if is_pattern else request.lstrip('/')]
		if verbosity >= 3: print(' '.join(cmd))
		result = subprocess.check_output(cmd).decode('utf-8')
		if result:
			if verbosity >= 1:
				print()
				print(result.rstrip('\n'))
			archives_with_hits.append(archive)

	# Extract results if relevant
	if not force_extract:
		return
	if len(archives_with_hits) == 0:
		if verbosity >= 1:
			print('No result found, no extraction')
		return
	if is_pattern:
		if verbosity >= 1:
			print('No extraction with pattern input, try again with a path')
		return
	if verbosity >= 2:
		print('Extracting result, ', end='')
		if no_suffix:
			print('with raw filename, no suffix added')
		else:
			print('adding date suffix to filename(s)')
	curdir = os.getcwd()
	with tempfile.TemporaryDirectory() as temp_dir:
		for archive in archives_with_hits:
			cmd = ['borg', 'info', archive, '--critical', '--json']
			archive_infos = json.loads(subprocess.check_output(cmd).decode('utf-8'))
			archive_date = archive_infos['archives'][0]['start'][:10]

			dir_level = request.lstrip('/').rstrip('/').count('/')
			extracted_file = os.path.basename(request.rstrip('/'))
			renamed_file = extracted_file if no_suffix else f'{archive_date}_{extracted_file}'
			renamed_file = os.path.join(curdir, renamed_file)
			cmd = ['borg', 'extract', '--critical', '--strip-components', str(dir_level), archive, request.lstrip('/')]
			if verbosity >= 3: print(' '.join(cmd))
			subprocess.run(cmd, cwd=temp_dir)

			cmd = ['mv', '-T', '-i', os.path.join(temp_dir, extracted_file), renamed_file] # Ask before existing
			if verbosity >= 3: print(' '.join(cmd))
			subprocess.run(cmd, cwd=temp_dir)

###############################################################################

def interactive():
	def ask_until(input_print, choices):
		choice = input(input_print)
		while choice not in choices:
			print('Les choix possibles sont: ' + ', '.join(choices))
			choice = input(input_print)
		print('')
		return choice

	print('Choisis entre reparation grub, restoration ou sauvegarde')
	choix1 = ask_until('grub,restoration,sauvegarde [g,r,s]: ', ['g', 'r', 's'])
	if choix1.lower() == 'g':
		# https://doc.ubuntu-fr.org/tutoriel/comment_restaurer_grub#via_un_cd_ubuntu_procedure_sans_chroot
		computer = detect_computer()
		mount_dir, disk = ('/media/debian', '/dev/sda') if computer == 'tharkey' else ('/media/debian_jessie', '/dev/sdb')
		cmd = [ 'grub-install', f'--root-directory={mount_dir}', disk ]
		print('Going to execute: ' + ' '.join(cmd))
		confirm = ask_until('Confirmer [o,n]: ', ['o', 'n'])
		if confirm == 'n':
			print('Exiting')
			return

		print('-'*80)
		subprocess.run(cmd, check=True)
	elif choix1.lower() == 'r':
		configs, groups = build_configs()
		items = groups['_interactive']
		print('Voici les items dispos: ' + str(items) + ' (root = / en version fichier, block = / en version dd)')
		choix2 = ask_until('Quel item extraire ? ', items)

		config = configs[choix2]
		display_infos(config['repo'], last=10, short=True, prefix=config['backup_name'])
		choix3 = input('Quelle sauvegarde ? ')
		print('')

		print(f'EXTRAIRE {choix2} {choix3} sur {config["source"]} ?')
		confirm = ask_until('Confirmer [o,n]: ', ['o', 'n'])
		if confirm == 'n':
			print('Exiting')
			return

		print('-'*80)
		_extract_item(choix2, configs, offline_method=True, name=choix3, verbosity=5)

	elif choix1.lower() == 's':
		configs, groups = build_configs()
		items = groups['_interactive']
		print('Voici les items dispos: ' + str(items) + ' (root = / en version fichier, block = / en version dd)')
		choix2 = ask_until('Quel item sauvegarder ? ', items)

		print(f'SAUVEGARDER {choix2} maintenant ?')
		confirm = ask_until('Confirmer [o,n]: ', ['o', 'n'])
		if confirm == 'n':
			print('Exiting')
			return

		print('-'*80)
		_backup_item(choix2, configs, verbosity=5)

###############################################################################

def show_diff():
	parser = common_parser()
	parser.add_argument('archive1', default=None, nargs='?', help='Oldest archive to compare. If omitted, going to interactive mode')
	parser.add_argument('archive2', default=None, nargs='?', help='Newest archive to compare, or "." to compare again current filesystem')
	parser.add_argument('--file',    '-f', action='store'      , help='Show detailed diff on specific file (or directory)')
	args = parser.parse_args()
	#if args.target is None: args.target = 'fs'
	args.v -= args.quiet
	configs, groups = build_configs()

	# Define archive
	if args.archive1 is None or args.archive2 is None:
		if args.target in configs.keys():
			config = configs[args.target]
		elif args.target is None:
			if args.file is None:
				print('Need to specify either a target, either a file, either both archives names')
				exit(13)
			else:
				matching_ids = [ archive_id for archive_id in configs.keys() if args.file.startswith(configs[archive_id]['source']) ]
				if len(matching_ids) == 0:
					print('Could not guess what is repo from file ' + file)
					exit(14)
				matching_id = max(matching_ids, key=len)
				config = configs[matching_id]
				if args.v >= 2:
					print(f'Guessed that target is ' + matching_id)
		else:
			print('Unknown target')
			exit(14)

		archive1 = ''
		last = 5
		while archive1 == '':
			display_infos(config['repo'], last=last, short=(args.v<=2), prefix=config['backup_name'])
			archive1 = input('Type archive1 name (oldest), or press Enter to print more targets: ')
			last *= 3
		archive2 = input('Type archive2 name (newest) or . to select current file system: ')
	else:
		archive1, archive2 = args.archive1, args.archive2
		if archive1 == '.':
			print('. accepted only for achive2 not for achive1')
			exit(22)
		prefix = archive1.split('-')[0] + '-'
		matching_ids = [ archive_id for archive_id in configs.keys() if configs[archive_id]['backup_name'] == prefix ]
		if len(matching_ids) == 0:
			print('Could not guess what is repo from archive name ' + archive1)
			exit(12)
		config = configs[ matching_ids[0] ]
		if archive2 == '.' and not args.file:
			print('I need to do backup of ' + matching_ids[0] + ' before computing diff')
			archive2 = _backup_item(matching_ids[0], configs, verbosity=args.v)

	# Compute differences
	if args.v >= 2:
		print(f'*** Compare {archive1} et {archive2} dans {config["repo"]} ***')
	if args.file:
		relative_source = os.path.relpath(config['source'], configs['fs']['source'])
		with tempfile.TemporaryDirectory() as temp_dir1:
			with tempfile.TemporaryDirectory() as temp_dir2:
				print(f'*** Montage de {archive1} sur {temp_dir1} et {archive2} sur {temp_dir2} ***')
				print('-'*80)
				try:
					subprocess.run(['borg', 'mount', f'{config["repo"]}::{archive1}', temp_dir1])
					if archive2 != '.':
						subprocess.run(['borg', 'mount', f'{config["repo"]}::{archive2}', temp_dir2])
					else:
						temp_dir2 = ''

					subprocess.run(['diff', '--recursive', '--side-by-side', '--suppress-common-lines', temp_dir1+'/'+args.file, temp_dir2+'/'+args.file])
					print()
					subprocess.run(['diff', '--recursive', '--unified=0', temp_dir1+'/'+args.file, temp_dir2+'/'+args.file])
					
					subprocess.run(['borg', 'umount', temp_dir1])
					if archive2 != '.':
						subprocess.run(['borg', 'umount', temp_dir2])
				except:
					raise Exception('Error during mount+rsync in online extraction with mount dir='+temp_dir)
	else:
		print('-'*80)
		cmd  = ['borg', 'diff', f'{config["repo"]}::{archive1}', f'{archive2}']
		subprocess.run(cmd, check=True)

###############################################################################

def prune():
	parser = common_parser()
	parser.add_argument('--actually-delete', action='store_true', help='Dry run if not enabled, else actually delete selected archives')
	args = parser.parse_args()
	args.v -= args.quiet

	configs, groups = build_configs()
	if args.target is None:
		repos_to_compact = set()
		for config in configs.values():
			if '@' in config['repo']:
				continue
			prune_config(config, args.v, dry_run=not(args.actually_delete))
			repos_to_compact.add(config['repo'])
		compact_repos(repos_to_compact, args.v, dry_run=not(args.actually_delete))

		# Check all archives covered in configs
		for repo in set([ config['repo'] for config in configs.values() ]):
			if '@' in repo:
				continue
			cmd =  ['borg', 'list', repo, '--json']
			infos = json.loads(subprocess.check_output(cmd).decode('utf-8'))['archives']
			prefixes_in_repo = set([ info['name'].split('-')[0] for info in infos if '_old-' not in info['name'] and 'remote_' not in info['name']])
			prefixes_in_configs = set([ conf['backup_name'][:-1] for conf in configs.values() ])
			if prefixes_in_repo.difference(prefixes_in_configs):
				print('Some archives were not related to any config prefix:', prefixes_in_repo.difference(prefixes_in_configs), repo)
	elif args.target in configs.keys():
		config = configs[args.target]
		prune_config(config, args.v, dry_run=not(args.actually_delete))
		compact_repos([config['repo']], args.v, dry_run=not(args.actually_delete))
	elif args.target in groups:
		repos_to_compact = set()
		for item in groups[args.target]:
			config = configs[item]
			prune_config(config, args.v, dry_run=not(args.actually_delete))
			repos_to_compact.add(config['repo'])
		compact_repos(repos_to_compact, args.v, dry_run=not(args.actually_delete))
	else:
		print('Unknown target')

def prune_config(config, verbosity, dry_run=True):
	cmd = ['borg', 'prune', config['repo']]
	cmd += ['-P', config['backup_name']]
	prune_keywords = ['--keep-within', '--keep-daily', '--keep-weekly', '--keep-monthly', '--keep-yearly']
	cmd += [v for pair in zip(prune_keywords, config['prune_opt']) for v in pair]
	if verbosity >= 3:
		cmd.append('--progress')
	if verbosity >= 2 and not dry_run:
		cmd.append('--stats')
	if verbosity >= 2 or dry_run:
		cmd.append('--list')
	if dry_run:
		cmd.append('--dry-run')

	if verbosity >= 2:
		print(' '.join(cmd))
	subprocess.run(cmd)
	if dry_run:
		print('*** dry run only ***')

def compact_repos(repos, verbosity, dry_run=True):
	if dry_run:
		return
	for repo in repos:
		cmd = ['borg', 'compact', repo]
		if verbosity >= 3:
			cmd.append('--progress')
		if verbosity >= 2:
			cmd.append('--verbose')
		if verbosity >= 2:
			print(' '.join(cmd))
		subprocess.run(cmd)


###############################################################################

def check():
	parser = common_parser()
	parser.add_argument('--full', '-f', action='store_true', help='Enable full check by berifying each chunk')
	args = parser.parse_args()
	args.v -= args.quiet

	configs, groups = build_configs()
	if args.target is None:
		for repo in set([ config['repo'] for config in configs.values() if '@' not in config['repo'] ]):
			check_repo(repo, args.full, args.v)
	else:
		check_repo(configs[args.target]['repo'], args.full, args.v)

def check_repo(repo, full=False, verbosity=2):
	cmd =  ['borg', 'list', repo, '--json']
	infos = json.loads(subprocess.check_output(cmd).decode('utf-8'))['archives']
	last_archive_date = infos[-1]['start']
	age = (datetime.now() - datetime.fromisoformat(last_archive_date)).days
	if verbosity >= 3: print('Last archive is ' +str(age) + ' day(s) old')
	if age > 10:
		print(f'*** WARNING last archive was created a long time ago = {age} days old ***')

	cmd = ['borg', 'check', repo]
	if verbosity >= 2: cmd.append('--progress')
	if full:
		cmd.append('--verify-data')
	else:
		cmd.append('--archives-only')
	if verbosity >= 3:
		print(' '.join(cmd))
	subprocess.run(cmd, check=True)

###############################################################################
def monitor_size():
	parser = common_parser()
	args = parser.parse_args()
	args.v -= args.quiet
	if args.target is None:
		args.target = 'fs'

	config = build_configs()[0][args.target]
	computer = detect_computer()
	references = {
		'fs'  : 38 if computer == 'ottokar' else 2998,
		'home': 36 if computer == 'ottokar' else 888,
	}
	no_recursion_dirs = ['./var/lib/docker/overlay2']

	def read_dir_size(dirname, depth=5):
		cmd = ['du', '-x', '-d', str(depth), '.']
		du_string = subprocess.run(cmd, cwd=dirname, capture_output=True)
		du_dict = {}
		for line in du_string.stdout.decode("utf-8").splitlines():
			fields = line.split('\t')
			size      = int(fields[0])//1000
			directory = './'.join(fields[1:])
			du_dict[directory] = size
		return du_dict

	def list_subdirs(du_dict, parent_dir):
		depth_of_parent = parent_dir.count('/')
		return [ dir_ for dir_ in du_dict if dir_.startswith(parent_dir+'/') and dir_.count('/')==depth_of_parent+1 ]

	def compare_dir_sizes(du_ref, du_cur, directory='.', threshold_MB=250):
		subdirs_ref, subdirs_cur = list_subdirs(du_ref, directory), list_subdirs(du_cur, directory)
		printed_diff = 0
		for subdir in set(subdirs_ref+subdirs_cur):
			subdir_sizeMB_ref, subdir_sizeMB_cur = du_ref.get(subdir, 0), du_cur.get(subdir, 0)
			diff_subdir = abs(subdir_sizeMB_ref-subdir_sizeMB_cur)
			if diff_subdir > threshold_MB:
				printed_diff_subsub = compare_dir_sizes(du_ref, du_cur, subdir) if subdir not in no_recursion_dirs else -1
				if printed_diff_subsub < diff_subdir / 2:
					print(f'{subdir[:45]:>45}: ref={subdir_sizeMB_ref:>5}MB vs cur={subdir_sizeMB_cur:>5}MB')
					printed_diff += diff_subdir
				else:
					printed_diff += printed_diff_subsub	
		return printed_diff

	def which_archive(repo, prefix, target_id):
		def to_int(s):
			try:
				return int(s)
			except:
				return 0
		cmd =  ['borg', 'list', repo, '--critical', '--prefix', prefix, '--json']
		try:
			liste = json.loads(subprocess.check_output(cmd).decode('utf-8'))
			all_id = [ to_int(archive_['name'].split('-')[-1]) for archive_ in liste['archives'] ]
			return prefix + str(min([ id_ for id_ in all_id if id_ >= target_id ]))
		except:
			raise Exception('Could not access '+repo+', permission issue?') from None
	
	
	archive_name = which_archive(config['repo'], config['backup_name'], references[args.target])
	with tempfile.TemporaryDirectory() as temp_dir:
		try:
			subprocess.run(['borg', 'mount', f'{config["repo"]}::{archive_name}', temp_dir, ])
			du_reference = read_dir_size(temp_dir+config['source'])
			du_current   = read_dir_size(config['source'])
			if abs(du_reference["."] - du_current["."])>300:
				print(f'{"OVERALL    ":>45}: ref={du_reference["."]:>5}MB vs cur={du_current["."]:>5}MB')
				compare_dir_sizes(du_reference, du_current)
			subprocess.run(['borg', 'umount', temp_dir])
		except:
			raise Exception('Error during mount with dir='+temp_dir)

###############################################################################

def borgbase(verbosity=1):
	computer, sshkey, remote = borgbase_info()
	env = {'BORG_RSH': f'ssh -i {sshkey}'}
	cmd  = ['borg', 'create', f'{remote}::{computer}-{{now}}', '/']
	cmd += ['--one-file-system', '--numeric-ids', '--compression', 'zstd,9']
	if verbosity >= 2:
		cmd += ['--progress', '--stats']
	if verbosity >= 3:
		print(env, ' '.join(cmd))
	subprocess.run(cmd, check=True, env=env)
	
	# cmd  = ['borg', 'info', remote, '--last', '10']

	cmd = ['borg', 'prune', remote, '--keep-weekly', '6']
	if verbosity >= 2:
		cmd += ['--progress', '--stats']
	subprocess.run(cmd, check=True, env=env)
	cmd = ['borg', 'compact', remote]
	if verbosity >= 2:
		cmd += ['--progress']
	subprocess.run(cmd, check=True, env=env)


###############################################################################

def dev():
	borgbase(verbosity=3)
	# _write_last_id('test', 69, 'tharkey')

if __name__ == '__main__':
	matchings = {'backup': backup, 'info': info_parse, 'find': find_parse, 'interactive': interactive, 'diff': show_diff, 'prune': prune, 'check': check, 'monitor': monitor_size, 'dev': dev}
	if len(sys.argv) >= 2:
		if not os.geteuid() == 0:
			sys.exit("\nOnly root can run this script\n")
		if sys.argv[1] in matchings.keys():
			func = matchings[sys.argv[1]]
			func()
			exit()
	if len(sys.argv) == 1:
		if detect_os() == 'livecd':
			print('bborg.py {' + '|'.join(matchings.keys()) + '}')
			print('mais comme tu as l air perdu, je vais lancer le mode interactif')
			print('')
			interactive()
			exit()
	print('bborg.py {' + '|'.join(matchings.keys()) + '}')

