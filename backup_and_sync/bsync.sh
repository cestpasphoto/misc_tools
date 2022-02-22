#!/bin/bash

OTTOKARFILES=(
'/usr/local/bin/transcode.py'
'/usr/local/bin/synchro.sh'
'/usr/local/sbin/diff_backup_sizes.sh' '/usr/local/sbin/dump_root_tree.sh'
'/usr/local/sbin/bborg.py'
'/usr/local/sbin/bsync.sh'
'/usr/local/sbin/syslog_summary.py'
)
THARKEYFILES=(
'/usr/local/bin/transcode.py'
'/usr/local/bin/synchro.sh'
'/usr/local/sbin/diff_backup_sizes.sh' '/usr/local/sbin/dump_root_tree.sh'
'/usr/local/sbin/bborg.py'
'/usr/local/sbin/bsync.sh'
'/usr/local/sbin/syslog_summary.py'
)

if [ "$EUID" -ne 0 ]; then
	echo "Please run as root"
	exit 18
fi

# Detection ordi
if [[ `grep -c "J4105" /proc/cpuinfo` -ge 1 ]]; then
	# echo "Tharkey detecte"
	LOCALFILES=("${THARKEYFILES[@]}")
	REMOTEFILES=("${OTTOKARFILES[@]}")
	REMOTE="ottokar"
elif [[ `grep -c "i5-9400" /proc/cpuinfo` -ge 1 ]]; then
	# echo "Ottokar detecte"
	LOCALFILES=("${OTTOKARFILES[@]}")
	REMOTEFILES=("${THARKEYFILES[@]}")
	REMOTE="serveur"
else
	grep "model name" /proc/cpuinfo 
	echo "CPU inconnu"
	exit 99
fi

ping -c1 -W1 -q $REMOTE &>/dev/null || exit 0

for ((i=0;i<${#LOCALFILES[@]};++i)); do
	# echo ${REMOTEFILES[i]} "-->" ${LOCALFILES[i]}
	[[ -f ${LOCALFILES[i]} ]] || touch -t 0001010000 ${LOCALFILES[i]}
	rsync --archive --update --itemize-changes best@$REMOTE:${REMOTEFILES[i]} ${LOCALFILES[i]}
done
