#!/bin/bash

# Index a list of URLs from a file
# usage : ./mass_index.sh <filename> <lang> <ip> <port>
# where :
# - <lang> is the lang of URLs content
# - <ip> + <port> is the path to search engine API

filename="$1"
while read -r line
do
    name="$line"
    curl -X POST -F "url=$name" -F "language=$2" "http://$3:$4/index"
done < "$filename"
