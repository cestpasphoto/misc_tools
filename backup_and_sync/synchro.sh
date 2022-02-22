#!/bin/bash

# nice et IOnice
ionice -c2 -n7 -p$$
renice +10 -p $$ > /dev/null

# Charger profil
SYNCPROFIL="$1"
source /etc/synchro.conf

if [[ "$2" != "force" ]]; then
  # Annule si démarrage < 10 minutes
  if [[ `cat /proc/uptime | awk -F "." '{ print($1) }'` -le 600 ]]; then
    echo "Demarrage recent"
    exit
  fi

  # Annule si une sauvegarde a déjà été faite
  # il y a moins de 900 min soit 15h
  if [[ -e "$TIMESTAMP" && `find "$TIMESTAMP" $AGEMINI | wc -l` -ge 1 ]]; then
    echo -n "Sauvegarde trop recente  "
    stat "$TIMESTAMP" | tail -n 3 | head -n 1
    exit
  fi

  # Annule si un répertoire previous trop récent existe
  # (indique qu'une svg est en cours)
  if [[ -e "$REP/previous" && `find "$REP/previous" -cmin -120 | wc -l` -ge 1 ]]; then
    echo "Previous trop recent (svg en cours ?)"
    exit
  fi
fi


# Etape 1: création d'un nouveau réperoire
NOUVEAUREPSHORT="svg.`date +%F.%Hh%M`"
NOUVEAUREP="$REP/$NOUVEAUREPSHORT"
mkdir "$NOUVEAUREP"

# Etape 2: rsync
rm -f "$REP/previous"
cp -d "$REP/current" "$REP/previous"
rsync -a -i --delete-after --fuzzy --link-dest="$REP/previous" $RSYNCOPT "$SRC" "$NOUVEAUREP"
if [[ "$?" != 0 && "$?" != 24 ]]; then
  echo "Erreur lors de rsync. STOP" 1>&2
  exit
fi

# Etape 3: création des liens
rm "$REP/current"
ln -s "$NOUVEAUREPSHORT" "$REP/current"
rm "$REP/previous"
touch "$TIMESTAMP"

# Etape 4: suppression des anciennes sauvegardes
#   Exemple:
#   MAX_INTERV_AGE="-1;21;4;5"
#   supprime les sauvegardes de 21j ou plus, converve une svg tous les 4j pour toutes
#   celles datant entre 5j et 21j (choisit les plus anciennes), et conserve toutes
#   celles datant de moins de 5j
if [[ "${MAX_INTERV_AGE:0:2}" == "-1" ]]; then
  MAXAGE=`echo ${MAX_INTERV_AGE} | cut -d';' -f 2`
  find "$REP" -mindepth 1 -maxdepth 1 -ctime +$MAXAGE -exec rm -rf '{}' \;
  MAX_INTERV_AGE=`echo ${MAX_INTERV_AGE} | cut -d';' -f 3-`
fi

if [[ "${MAX_INTERV_AGE}" != "" ]]; then
  SVGLIST=`find "$REP" -mindepth 1 -maxdepth 1 -printf "%C@ %p\n" | sort -h`
  echo "$SVGLIST" | awk -v s=${MAX_INTERV_AGE} -v today=`date +%s` 'BEGIN { split(s,l,";") ; i=1; thres=0 } \
   { if ($1 > today-l[i+1]*24*3600) { if (i+2 in l) i=i+2; else exit 0 } ; \
   if ($1 > thres) thres=int($1+l[i]*24*3600); else system("rm -rf \""$2"\"");  \
   }'
fi
