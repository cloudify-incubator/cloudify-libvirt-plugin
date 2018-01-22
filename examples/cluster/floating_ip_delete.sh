/sbin/ip address del $EXTERNAL_IP/24 dev $EXTERNAL_INTERFACE
/sbin/iptables -D FORWARD -d $INTERNAL_IP -j ACCEPT
/sbin/iptables -D  PREROUTING -t nat -d $EXTERNAL_IP -j DNAT --to-destination $INTERNAL_IP
