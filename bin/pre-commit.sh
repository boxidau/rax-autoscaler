#!/usr/bin/env sh

while true; do
    read -p "How do you wish to bump version: (b)ump, (m)inor, (M)ajor or (q)uit? " bmMqQ
    case $bmMqQ in
        [b]* ) bump -qb raxas/version.py; break;;
        [m]* ) bump -qm raxas/version.py; break;;
        [M]* ) bump -qM raxas/version.py; break;;
        [qQ]* ) exit;;
        * ) echo "Please answer: (b)ump, (m)inor, (M)ajor or (q)uit";;
    esac
done
