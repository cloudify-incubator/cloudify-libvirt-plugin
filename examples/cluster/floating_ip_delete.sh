sudo /sbin/ip address del $EXTERNAL_IP/24 dev $EXTERNAL_INTERFACE
sudo /sbin/iptables -D FORWARD -d $INTERNAL_IP -j ACCEPT
sudo /sbin/iptables -D PREROUTING -t nat -d $EXTERNAL_IP -j DNAT --to-destination $INTERNAL_IP
