# add ip alias
/sbin/ip address add $EXTERNAL_IP/24 dev $EXTERNAL_INTERFACE

# add iptables rules
/sbin/iptables -t nat -I PREROUTING -d $EXTERNAL_IP -j DNAT --to-destination $INTERNAL_IP
/sbin/iptables -I FORWARD -d $INTERNAL_IP -j ACCEPT
