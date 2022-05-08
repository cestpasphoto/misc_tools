
import sys
import subprocess

def detect_computer(other=False):
	with open('/proc/cpuinfo') as f:
		cpuinfo = f.read()
	if 'i5-9400' in cpuinfo:
		return 'ottokar' if not other else 'tharkey'
	elif 'J4105' in cpuinfo:
		return 'tharkey' if not other else 'ottokar'
	else:
		print('unknown computer detected', file=sys.stderr)
		return 'unknown'

def detect_os():
	root_type = subprocess.check_output(['df', '--output=fstype', '/']).decode('utf-8')
	if 'overlay' in root_type:
		return 'livecd'
	elif 'ext4' in root_type:
		return 'os'
	else:
		print('unknown OS detected', file=sys.stderr)
		return 'unknown'

def build_configs(other_computer=False):
	configs, groups = {}, {}
	common_opts=['--one-file-system', '--compression', 'zstd,9']
	computer = detect_computer(other_computer)

	def add_item(archive_id, source, repo, remote_repo=None, is_block=False, exclude=[], comp_options=common_opts, decomp_options=[], chunk_size=None, prune_options=None, pre_comp_func=None, post_comp_func=None):
		archive_name = archive_id+'-'
		if archive_id in configs:
			print(f'Warning: {archive_id} is defined multiple times')
		if prune_options is None:
			prune_options = ['8d', '2', '3', '4', '5'] # keep-within, keep-daily, keep-weekly, keep-monthly, keep-yearly
		elif prune_options == 'keep-less':
			prune_options = ['3d', '1', '1', '2', '3']
		chunk_options = ['--chunker-params=14,23,17,4095'] if chunk_size == 17 else [] # use default chunker params = 19,23,21,4095
		configs[archive_id] = {
			'source': source,
			'repo': repo,
			'backup_name': archive_name,
			'is_block': is_block,
			'comp_opt': comp_options + chunk_options + ['--checkpoint-interval', '300'] + [func(source+folder) for folder in exclude for func in (lambda x: '--exclude', lambda x: x)],
			'decomp_opt': decomp_options,
			'prune_opt': prune_options,
			'pre_comp': pre_comp_func,
			'post_comp': post_comp_func
		}
		if remote_repo:
			remote_id = 'remote_' + archive_id
			configs[remote_id] = configs[archive_id].copy()
			configs[remote_id]['backup_name'] = 'remote_' + archive_name
			configs[remote_id]['repo'] = remote_repo

	def pre_dd_func(sys_dir, computer):
		pre_dd  = f''
		for disk in ['sda', 'sdb' if computer == 'tharkey' else 'nvme0n1']:
			pre_dd += f'sgdisk --backup={sys_dir}/{disk}_header.sgdisk /dev/{disk} > /dev/null ; '
			pre_dd += f'dd if=/dev/{disk} of={sys_dir}/{disk}_header.dd bs=2048 count=1 status=none ; '
			pre_dd += f'sgdisk --print /dev/{disk} > {sys_dir}/partitions_sectors.txt ; '
		pre_dd += f'blkid > '+sys_dir+'/partitions_id.txt ; '
		pre_dd += f'/usr/local/sbin/dump_root_tree.sh'
		return pre_dd

	post_block = 'journalctl --vacuum-size=200M --quiet ; aptitude clean ; rm -rf /root/.cache/pip/ /home/best/.cache/pip/'
	pre_block  = 'fstrim /'

	if computer == 'tharkey':
		b_root, b_perso, b_public = '/backup/serveur/system', '/backup/serveur/perso', '/backup/public/publicdata'
		b_remote_root, b_remote_perso, b_remote_public = 'root@ottokar:/backup/ottokar/system', 'root@ottokar:/backup/ottokar/perso', 'root@ottokar:/backup/public/publicdata'
		sys_dir = '/data/serveur/system'
		disk_efi, disk_boot, disk_root = '/dev/disk/by-partuuid/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', '/dev/disk/by-partuuid/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', '/dev/disk/by-partuuid/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
		
		add_item('othersHDD'       , '/mnt/hdd/data/'         , b_perso, b_remote_perso , exclude=['public/films/', 'public/series/'], prune_options='keep-less')
		add_item('perso'           , '/mnt/sa320/data/'       , b_perso, b_remote_perso , exclude=['public/'])
		add_item('remote_downloads', '/mnt/sa320/data/public/'         , b_remote_public, exclude=['musique/'], comp_options=['--exclude', '*.part'], prune_options=['3d', '2', '2', '0', '0'])
		add_item('remote_public'   , '/mnt/hdd/data/'                  , b_remote_public, exclude=['nextcloud/'], comp_options=[], prune_options=['5d', '3', '3', '3', '0'])
	elif computer == 'ottokar':
		b_root, b_perso, b_public = '/backup/ottokar/system', '/backup/ottokar/perso', '/backup/public/publicdata'
		b_remote_root, b_remote_perso, b_remote_public = 'root@serveur:/backup/serveur/system', 'root@serveur:/backup/serveur/perso', 'root@serveur:/backup/public/publicdata'
		sys_dir = '/data/ottokar/system'
		disk_efi, disk_boot, disk_root = '/dev/disk/by-partuuid/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', '/dev/disk/by-partuuid/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', '/dev/disk/by-partuuid/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'

		add_item('VM'           , '/mnt/VM/'            , b_root , b_remote_root  , chunk_size=17, prune_options='keep-less')
		add_item('perso'        , '/mnt/dd/data/'       , b_perso, b_remote_perso , exclude=['public/'])
		add_item('remote_public', '/mnt/dd/data/public/'         , b_remote_public, comp_options=[], prune_options='keep-less')

	# Common items
	pre_dd = pre_dd_func(sys_dir, computer)
	add_item('home'          , '/home'   , b_perso, b_remote_perso, comp_options=['--exclude', '*/.cache/mozilla'])
	add_item('fs'            , '/'       , b_root , b_remote_root , chunk_size=17, comp_options=common_opts+['--numeric-ids'], decomp_options=['--numeric-ids'], exclude=['home/'])
	add_item('block'         , disk_root , b_root , b_remote_root , chunk_size=17, is_block=True, pre_comp_func=pre_block, post_comp_func=post_block, prune_options='keep-less')
	add_item('bootefi'       , disk_efi  , b_root , b_remote_root , chunk_size=17, is_block=True, prune_options='keep-less')
	add_item('efi'           , disk_boot , b_root , b_remote_root , chunk_size=17, is_block=True, prune_options='keep-less')
	add_item('disk'          , sys_dir   , b_root , b_remote_root , chunk_size=17, pre_comp_func=pre_dd)
	add_item('public'        , None      , b_public) # Fake target pointing to b_public, no need for actual options

	groups = {
		'short'    : ['home', 'fs', 'bootefi', 'efi', 'disk'],
		'long_root': ['block', 'VM'],
		'long_data': ['perso', 'othersHDD'],
		'remote_short'    : ['remote_home', 'remote_fs', 'remote_bootefi', 'remote_efi', 'remote_disk'],
		'remote_long_root': ['remote_block', 'remote_VM'],
		#'remote_long_data': ['remote_perso', 'remote_othersHDD', 'remote_public', 'remote_downloads'],
		'remote_long_data': ['remote_perso', 'remote_othersHDD', 'remote_public'],
		'_interactive': ['bootefi', 'efi', 'block', 'fs' ]
	}
	groups = { k:[c for c in v if c in configs] for k,v in groups.items() } # remove item not relevant for current computer
	groups['remote_all'] = groups['remote_short'] + groups['remote_long_root'] + groups['remote_long_data'] 

	if detect_os() == 'livecd':
		print('LIVECD DETECTE (ignorer les erreurs "umount", acceptez nouveaux repos)')
		from os import geteuid
		if geteuid() != 0:
			print("*** J'ai besoin des droits root, relancer avec sudo ***")
			exit(10)
		root_part = configs['block']['source']
		hdd_part  = '/dev/sda1' if computer == 'tharkey' else '/dev/sdb1'
		subprocess.run(['mkdir', '-p', '/home/user/root/', '/home/user/hdd/']  , check=True)
		subprocess.run(['umount', '/home/user/root/']                          , check=False)
		subprocess.run(['umount', '/home/user/hdd/']                           , check=False)
		subprocess.run(['mount', root_part, '/home/user/root/']                , check=True)
		subprocess.run(['mount', hdd_part , '/home/user/hdd/' ]                , check=True)
		for v in configs.values():
			if not v['is_block']:
				v['source'] = '/home/user/root' + v['source']
			v['repo']   = '/home/user/hdd'  + v['repo']
			v['pre_comp'] = v['post_comp'] = None

	return configs, groups

def borgbase_info():
	computer = detect_computer()
	if computer == 'tharkey':
		sshkey, remote = '/root/.ssh/id_xxxxxxxx', 'xxxxxxxx@xxxxxxxx.repo.borgbase.com:repo'
	else:
		sshkey, remote = '/root/.ssh/id_xxxxxxxx', 'xxxxxxxx@xxxxxxxx.repo.borgbase.com:repo'
	# --rsh option works too, for instance:
	# borg info xxxxxxxx@xxxxxxxx.repo.borgbase.com:repo --rsh "ssh -i /root/.ssh/id_be_st"

	return computer, sshkey, remote