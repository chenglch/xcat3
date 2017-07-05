instdisk=`cat /tmp/xcat.install_disk`
modprobe ext4 >& /dev/null
modprobe ext4dev >& /dev/null
if grep ext4dev /proc/filesystems > /dev/null; then
	FSTYPE=ext3
elif grep ext4 /proc/filesystems > /dev/null; then
	FSTYPE=ext4
else
	FSTYPE=ext3
fi
BOOTFSTYPE=ext3
EFIFSTYPE=vfat

if uname -r|grep -q '^3.*el7'; then
    BOOTFSTYPE=xfs
    FSTYPE=xfs
    EFIFSTYPE=efi
fi

echo "ignoredisk --only-use=$instdisk" >> /tmp/partitionfile
if [ `uname -m` = "ppc64" -o `uname -m` = "ppc64le" ]; then
	echo 'part None --fstype "PPC PReP Boot" --ondisk '$instdisk' --size 8' >> /tmp/partitionfile
fi
if [ -d /sys/firmware/efi ]; then
	echo 'part /boot/efi --size 50 --ondisk '$instdisk' --fstype '$EFIFSTYPE >> /tmp/partitionfile
fi

#TODO: ondisk detection, /dev/disk/by-id/edd-int13_dev80 for legacy maybe, and no idea about efi.  at least maybe blacklist SAN if mptsas/mpt2sas/megaraid_sas seen...
echo "part /boot --size 512 --fstype $BOOTFSTYPE --ondisk $instdisk" >> /tmp/partitionfile
echo "part swap --recommended --ondisk $instdisk" >> /tmp/partitionfile
echo "part pv.01 --size 1 --grow --ondisk $instdisk" >> /tmp/partitionfile
echo "volgroup system pv.01" >> /tmp/partitionfile
echo "logvol / --vgname=system --name=root --size 1 --grow --fstype $FSTYPE" >> /tmp/partitionfile

#specify "bootloader" configuration in "/tmp/partitionfile" if there is no user customized partition file
BOOTLOADER="bootloader "

#Specifies which drive the boot loader should be written to
#and therefore which drive the computer will boot from.
[ -n "$instdisk" ] && BOOTLOADER=$BOOTLOADER" --boot-drive=$(basename $instdisk)"

echo "$BOOTLOADER" >> /tmp/partitionfile