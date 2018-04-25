# add ip alias
sudo /sbin/ip address add $EXTERNAL_IP/24 dev $EXTERNAL_INTERFACE

# add iptables rules
sudo /sbin/iptables -t nat -I PREROUTING -d $EXTERNAL_IP -j DNAT --to-destination $INTERNAL_IP
sudo /sbin/iptables -I FORWARD -d $INTERNAL_IP -j ACCEPT
