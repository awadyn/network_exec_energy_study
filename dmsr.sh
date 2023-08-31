#!/bin/bash
#set -x

echo "666655555555554444444444333333333322222222221111111111          "
echo "3210987654321098765432109876543210987654321098765432109876543210"
echo "----------------------------------------------------------------"
old=$(bc <<EOF
obase=10
ibase=16
$(sudo rdmsr -X -0  0x639)
EOF
)
while true; do
new=$(bc <<EOF
obase=10
ibase=16
$(sudo rdmsr -X -0  0x639)
EOF
)
#len=${#new}
if [ $new -lt $old ]; then
echo "OVERFLOW"
break
fi
#for ((i=0; i<(64-$len); i++)); do
#	echo -n 0
#done
echo $old $new
old=$new
done;

