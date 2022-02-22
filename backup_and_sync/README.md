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

