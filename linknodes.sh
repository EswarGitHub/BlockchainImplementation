#!/bin/bash

port=$1

if [ -z "$port" ] #if port isn't assigned
then
  echo Need to specify port number
  exit 1
fi

FILES=(blockchain.py)

mkdir Code$port

for file in "${FILES[@]}"
do
  echo Syncing $file
  ln Code/$file Code$port/$file
done

echo Synced new Code folder for port $port

exit 1
