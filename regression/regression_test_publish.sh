#!/usr/bin/env bash

if [ $0 != "-bash" ] ; then
    pushd `dirname "$0"` 2>&1 > /dev/null
fi
dir=$(pwd)
if [ $0 != "-bash" ] ; then
    popd 2>&1 > /dev/null
fi

HTMLDIR=$(echo $dir | sed 's^/regression^^g' | rev | cut -d '/' -f 1 | rev)

sudo mkdir -p /var/www/html/$HTMLDIR
sudo cp $dir/main.html /var/www/html/$HTMLDIR/index.html
sudo rsync -az $dir/input_samples/ /var/www/html/$HTMLDIR/input_samples/
sudo rsync -az $dir/output_samples/ /var/www/html/$HTMLDIR/output_samples/
		