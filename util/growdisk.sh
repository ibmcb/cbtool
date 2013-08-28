#!/bin/bash

function usage {
	echo "usage: [src disk] [dest disk] [new size in GIGAbytes]"
	exit 1
}

function verify {
	if [ $1 -gt 0 ] ; then
		echo "$2 step failed."
		exit 1
	fi
}

echo "note: this script assumes the partition you want to resize is the *only* partition on the disk and is a primary partition."

src=$1
dest=$2
gb=$3
headroom=1
((bytes=(gb + headroom)*1024*1024*1024))
loop="loop1"


if [ x"$1" == x ] ; then
	usage
fi
if [ x"$2" == x ] ; then usage
	usage
fi
if [ x"$3" == x ] ; then
	usage
fi

if [ ! -e $src ] ; then
	echo "source disk $src does not exist"
	exit 1
fi

if [ -e $src.raw ] ; then
	echo "previous conversion failed. please delete $src.raw before proceeding."
	exit 1
fi

if [ -e $dest.raw ] ; then
	echo "previous conversion failed. please delete $dest.raw before proceeding."
	exit 1
fi

if [ x"$(whoami)" != xroot ] ; then
	echo "please run this script as root"
	exit 1
fi

if [ -e $dest ] ; then
	echo "previous conversion failed. please delete $dest file before proceeding."
	exit 1
fi
	
format=$(qemu-img info $src | grep format | sed "s/.*\: //g")

if [ x"$format" != "xqcow2" ] && [ x"$format" != "xqed" ] ; then
	echo "unsupported base disk file format: $format"
	exit 1
fi

((blocks=bytes/4096))
((actual=bytes/1024/1024/1024))

echo "mounting original disk to fsck with nbd before growing"

qemu-nbd -c /dev/nbd0 $src

verify $? "attach qemu-nbd to $src"

echo "fscking nbd-mounted image"

fsck -fy /dev/nbd0p1

verify $? "fsck /dev/nbd0p1"

echo "detaching qemu-nbd from original image"

qemu-nbd -d /dev/nbd0 

verify $? "qemu-nbd -d /dev/nbd0 $src"

echo "Converting original image to $src.raw $actual GB ... "
qemu-img convert -O raw $src $src.raw
verify $? "convert to raw"

echo "Creating new raw sparse destination file ... $dest.raw"
dd if=/dev/null of=${dest}.raw bs=4096 seek=$blocks
verify $? "convert to raw"

echo "getting offset..."
offset=$(echo "512 * $(fdisk -l $src.raw  | grep "Linux" | sed "s/ \+/ /g" | cut -d " " -f 3)" | bc)

verify $? "discover offset"
echo "offset is: $offset"

echo "Copying old bytes to between raw files..."
dd if=$src.raw of=$dest.raw conv=notrunc bs=$offset
verify $? "copying old data"

echo "removing old raw file ... "
rm -f $src.raw
verify $? "deleting old raw file"

echo "Mounting new raw file as loopback ... "
losetup -o $offset /dev/$loop $dest.raw
verify $? "mounted destination as loopback using /dev/$loop"

echo "deleting partition 1 on $dest.raw ... "
parted -s $dest.raw rm 1
verify $? "deleted old partition"

((bigger=gb+headroom))
echo "creating new partition 1 ... $bigger GB"
parted -s $dest.raw mkpart primary 32.3kB ${bigger}GB
verify $? "deleted old partition"

echo "resizing filesystem ... "
resize2fs /dev/$loop ${gb}G
verify $? "resize filesystem"
sync
sleep 10

echo "removing loopback device"
losetup -d /dev/$loop
verify $? "removing loopback"

echo "converting back to $format"
qemu-img convert -O $format $dest.raw $dest
verify $? "convert to $format"

echo "removing new raw file ... "
rm -f $dest.raw
verify $? "deleting new raw file"

echo "finished!"
