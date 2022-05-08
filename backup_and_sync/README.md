# Backup and sync
Backup tool designed for my personal network with 2 computers: serveur (which is a server up most of the time... but not always) and ottokar (a regular desktop which is up at most few hours per week).

### bsync.sh

Synchronize important files between the 2 computers based on rsync, and display synchronized changes (or send by mail if run through cron)

### synchro.sh

_Deprecated, using script based on borg-backup now_  
Short (yet efficient) script that keeps track of one computer's folders on the other computer, with a retention policy. It uses hardware links of unix fs to mutualize storage of unmodified files.  
Configurable through a dedicated config file (see example):
* `MAX_INTERV_AGE="90;365;30;60;7;7"` : defines retention policy. In this example, it keeps all backups from the last 7 days, then a backup every 7 days for those between 7 and 60 days old, every 30 days for those between 60 and 365 days and every 90 days for those more than 365 days old. Value "-1" is to delete every backup after a specified age.
* `AGEMINI="-cmin -15"`: defines a condition on `find` to filter out some files, for instance those that has been modified too recently (no need to backup the code I am modifying right now)
* `REP` and `SRC`: destination folder and source folder (assume rsync shared folders set up)


### bborg.py

Wrapper for the excellent tool [borgbackup](https://www.borgbackup.org/). It allows several actions, the main one being _backup_: it backups the selected target into configured repo/archive with an archive name `target-index` using an increasing index. It is compatible with remote repos.
Also offers a _find_ feature which searchs for a file (using regex for instance) among all archives: convenient to find an legacy file. Can also pretty print repo info, shows which subfolders are significantly larger/smaller between two archives, shows a diff between 2 archives, and regular actions prune/check.
Provided with a sample config file.


Also provided with a "scheduler": it is designed to run once at startup and finish in less than 5 minutes. It keeps tracks of which archives ran and when, and when executed, run only backups that will fit into the 5 minutes window (parallelize backups if they don't conflict each other in terms of performance).


### borg patch

Patch for borgbackup to add a `bypasslock` option in borg mount: that allows to mount an archive without holding any lock.