#!/usr/bin/env python
"""
Author: Kevin Cyu, scyu@a10networks.com
"""
import argparse, sys, socket, random, struct, time
from scapy.all import *

g_port_max = 65535
g_eth_ipv4 = 0x0800
g_eth_ipv6 = 0x86DD
g_l4_udp = 17
g_l4_tcp = 6
g_l4_icmp = 1

# printing format offset
loff = 30
roff = 20

def main():
    parser = argparse.ArgumentParser()

    """
        Usage:

            1) IPv6 traffic with 1 UDP packet (src-port: 1000, dest-port: 80)

            ./myhping.py --gwv6 <Your v6 Gateway> --sipv6 <Source v6 addr> --dipv6 <Dest v6 addr> --sport 1000 --dport 80 --num 1

            2) IPv4
    """

    # program parameter config
    parser.add_argument('--intf', type=str, help="Sending interface (default=ens19)", default="ens19")
    parser.add_argument('--num', type=int, help="Send total N packets (default=1)", default=1)
    parser.add_argument('--ipv', type=int, help="IP version (4 or 6, default=6)", default=6)
    parser.add_argument('--mode', type=int, help="Set mode (0=iterative, 1=random, 2=slow)", default=0)
    parser.add_argument('--use-gw', help="Use Gateway's mac as dmac instead of getmacbyip(dip)/getmacbyip6(dip)", action="store_true")
    parser.add_argument('--debug', help="Enter debug mode, just print configuration without sending real traffic.", action="store_true")
    parser.add_argument('--answer', help="Wait for responses, not just send out this packets.", action="store_true")
    parser.add_argument('--timeout', type=int, help="Timeout for waiting response", default=2)
    parser.add_argument('--verbose', help="Verbose mode (More detail info).", action="store_true")
    # L3 (v4)
    parser.add_argument('--sip', type=str, help="Source IP address", default="20.20.20.225")
    parser.add_argument('--dip', type=str, help="Destination IP address", default="20.20.101.226")
    parser.add_argument('--gw', type=str, help="Setup Default gateway address", default="20.20.20.1")
    # L3 (v6)
    parser.add_argument('--sipv6', type=str, help="Source IPv6 address (only enable when ip version = 6)", default="2061::20.20.20.225")
    parser.add_argument('--dipv6', type=str, help="Destination IPv6 address (only enable when ip version = 6)", default="2061::20.20.101.226")
    parser.add_argument('--gwv6', type=str, help="Setup Default gateway address (v6, only enable when ip version = 6)", default="2061::20.20.20.3")
    # L4
    """
        Notice:
            If --sport / --dport not specified, it will use value from --port as source / destination port.
            For example:
            1) Sending ipv6 udp traffic for 10 UDP packets from port 1000 to 1009 (N == 10), both source and dest port want to change:
                ./myhping.py --num 10 --port 1000 --proto 17 --mode 0 (or --mode 2) ...
            2) Sending ipv6 udp traffic for 10 UDP packets, only source port want to be ranged from 1000 to 1009, and dest port = 5000:
                ./myhping.py --num 10 --port 1000 --dport 5000 --proto 17 --mode 0 (or --mode 2) ...
            3) Sending ipv6 udp traffic for 10 UDP packets with same source and dest port = 5000:
                ./myhping.py --num 10 --sport 5000 --dport 5000 --proto 17 ...
    """
    parser.add_argument('--sport', type=int, help="Specify Source Port number (default: use 'Start Port')", default=-1)
    parser.add_argument('--dport', type=int, help="Specify Destination Port number (default: use 'Start Port')", default=-1)
    parser.add_argument('--port', type=int, help="Default Start Port number (default: 1)", default=1)
    parser.add_argument('--proto', type=int, help="Specify L4 Protocol, UDP: 17(default), TCP: 6. (Other will be 'Unknown')", default=17)
    # optional
    parser.add_argument('--payload-len', type=int, help="Total length of payload filled with 'A'.", default=0)
    parser.add_argument('--payload-content', type=str, help="Customized Payload content (disable --payload-len)", default="")

    # parse
    args = parser.parse_args()
    # get value for arguments
    iface = args.intf
    ip_ver = args.ipv
    debug = args.debug
    answer = args.answer
    timeout = args.timeout
    verbose = args.verbose
    src_addr = args.sip if ip_ver == 4 else args.sipv6
    dst_addr = args.dip if ip_ver == 4 else args.dipv6
    gateway = args.gw if ip_ver == 4 else args.gwv6
    sport = args.sport
    dport = args.dport
    start_port = args.port
    proto = args.proto
    l4_proto = [None] * 255
    l4_proto[17] = "UDP"
    l4_proto[6] = "TCP"
    if proto > 255: # invalid parameter, exit program
        sys.exit("Invalid l4 protocol (Exceed valid range: {})".format(proto))
    if l4_proto[proto] == None:
        print "Unsupported l4 protocol, use payload-content as L4 header & payload"
    mode = args.mode
    modes = [
        "Send packet with linearly increasing port.",
        "Send packet with random port.",
        "Same as mode 0, but send slowly."
    ]
    payload_len = args.payload_len
    payload_content = args.payload_content

    # Static route for special case (for bug523460)
    #prefix = "55aa::/96"
    #conf.iface6 = iface
    #conf.route6.resync()
    #conf.route6.add(dst="55aa::/96", gw=gateway, dev=iface)

    """
        Handle interface type is "tunnel" (e.g. ds-lite), using L3socket instead.
        Setup:
            - s (socket instance)
            - smac (source mac addr, will be use by L2 send)
            - use_l3_sock (flag, use to distinguish which socket we should use)
    """
    dmac = ""
    try:
        s = conf.L2socket(iface)
        smac = get_if_hwaddr(iface)
        use_l3_sock = 0
    except:
        s = conf.L3socket(iface)
        smac = ""
        use_l3_sock = 1

    # Get dmac address from getmacbyip/getmacbyipv6, with dst_addr or gateway
    if ip_ver == 4:
        dmac = getmacbyip(ip=dst_addr) if args.use_gw is False else getmacbyip(ip=gateway)
        if dmac is None:
            print "[v4] Using default GW's dmac"
            dmac = getmacbyip(ip=gateway) # using default gw's mac
    else:
        dmac = getmacbyip6(ip6=dst_addr) if args.use_gw is False else getmacbyip6(ip6=gateway)
        if dmac is None:
            print "[v6] Using default GW's dmac"
            dmac = getmacbyip6(ip6=gateway) # using default gw's mac


    # print status info
    print "=============================================================="
    print "{:<{}} {:>{}}".format("Interface:", loff, iface, roff)
    print "{:<{}} {:>{}}".format("IP version:", loff, ip_ver, roff)
    print "{:<{}} {:>{}}".format("Source IP address:", loff, src_addr, roff)
    print "{:<{}} {:>{}}".format("Destination IP address:", loff, dst_addr, roff)
    print "{:<{}} {:>{}}".format("L4 Protocol:", loff, l4_proto[proto] if l4_proto[proto] is not None else "Unknown", roff)
    if l4_proto[proto] is not None:
        print "{:<{}} {:>{}}".format("Source Port number:", loff, sport if sport > 0 else start_port, roff)
        print "{:<{}} {:>{}}".format("Destination Port number:", loff, dport if dport > 0 else "Not specified", roff)
        print "{:<{}} {:>{}}".format("Start Src port number:", loff, start_port, roff)
    print "Sending mode=================================================="
    if sport < 0 and dport < 0:
        print modes[mode]
    print "Payload ======================================================"
    print "{:<{}} {:>{}}".format("Customized payload: ", loff, "enable" if payload_len > 0 or len(payload_content) > 0 else "disable", roff)
    if len(payload_content) > 0:
        payload = payload_content
        print "{:<{}} {:>{}}".format("Payload content: ", loff, payload_content, roff)
    else:
        payload = "A" * payload_len
        print "{:<{}} {:>{}}".format("Payload length: ", loff, payload_len, roff)
    print "Static config================================================="
    print "{:<{}} {:>{}}[{}]".format("Default Gateway:", loff, gateway, roff, "custom" if args.use_gw is True else "default")
    #print "Added route: [GW={}, Prefix={}, Dev={}]".format(gateway, prefix, iface)
    print "Packet out===================================================="
    print "Sending on interface {}({} -> {}), IPv{}".format(iface, smac, dmac, ip_ver)
    print "[{}] {} -> {}".format(l4_proto[proto] if l4_proto[proto] is not None else "Unknown", str(src_addr), str(dst_addr))

    if debug is True:
        print "Not send any traffic (debug mode)."
        sys.exit(0)

    total_answer_dict = {
        'ip': 0,
        'ipv6': 0,
        'tcp': 0,
        'udp': 0,
        'icmp': 0
    }

    port_pair = []

    if l4_proto[proto] is not None:
        for i in range(args.num):
            if mode is 0:
                src_port = sport if sport > 0 else (i + start_port)%g_port_max
                dst_port = dport if dport > 0 else (i + start_port)%g_port_max
            elif mode is 1:
                src_port = sport if sport > 0 else random.randint(start_port, g_port_max)
                dst_port = dport if dport > 0 else random.randint(start_port, g_port_max)
            else:
                src_port = sport if sport > 0 else (i + start_port)%g_port_max
                dst_port = dport if dport > 0 else (i + start_port)%g_port_max
                pkt = None
                udp = UDP(sport=src_port, dport=dst_port)
                tcp = TCP(sport=src_port, dport=dst_port)
                if ip_ver == 4:
                    if proto is g_l4_udp:
                        l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                              IP(src=src_addr, dst=dst_addr)/udp/payload)
                        l3pkt = IP(src=src_addr, dst=dst_addr)/udp/payload
                    elif proto is g_l4_tcp:
                        l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                              IP(src=src_addr, dst=dst_addr)/tcp/payload)
                        l3pkt = IP(src=src_addr, dst=dst_addr)/tcp/payload
                else:
                    if proto is g_l4_udp:
                        l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                              IPv6(src=src_addr, dst=dst_addr)/udp/payload)
                        l3pkt = IPv6(src=src_addr, dst=dst_addr)/udp/payload
                    elif proto is g_l4_tcp:
                        l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                              IPv6(src=src_addr, dst=dst_addr)/tcp/payload)
                        l3pkt = IPv6(src=src_addr, dst=dst_addr)/tcp/payload
                # send packet slowly
                if answer is True:
                    if use_l3_sock is 1:
                        ans, unans = sr(l3pkt, iface=iface, timeout=timeout, verbose=False)
                    else:
                        ans, unans = srp(l2pkt, iface=iface, timeout=timeout, verbose=False)
                else:
                    if use_l3_sock is 1:
                        send(l3pkt, iface=iface, inter=timeout, verbose=False)
                    else:
                        sendp(l2pkt, iface=iface, inter=timeout, verbose=False)
                # need to add here because this mode will continue
                if answer is True:
                    parse_ans(total_answer_dict, ans)
                # record port-pair
                port_pair.append({'src': src_port, 'dst': dst_port})
                continue
            udp = UDP(sport=src_port, dport=dst_port)
            tcp = TCP(sport=src_port, dport=dst_port)
            if ip_ver == 4:
                if proto is g_l4_udp:
                    l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                            IP(src=src_addr, dst=dst_addr)/udp/payload)
                    l3pkt = IP(src=src_addr, dst=dst_addr)/udp/payload
                elif proto is g_l4_tcp:
                    l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                            IP(src=src_addr, dst=dst_addr)/tcp/payload)
                    l3pkt = IP(src=src_addr, dst=dst_addr)/tcp/payload
            else:
                if proto is g_l4_udp:
                    l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                            IPv6(src=src_addr, dst=dst_addr)/udp/payload)
                    l3pkt = IPv6(src=src_addr, dst=dst_addr)/udp/payload
                elif proto is g_l4_tcp:
                    l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                            IPv6(src=src_addr, dst=dst_addr)/tcp/payload)
                    l3pkt = IPv6(src=src_addr, dst=dst_addr)/tcp/payload
            # send packet with high speed
            if answer is True:
                if use_l3_sock is 1:
                    ans, unans = s.sr(l3pkt, timeout=timeout, verbose=False)
                else:
                    ans, unans = s.sr(l2pkt, timeout=timeout, verbose=False)
            else:
                if use_l3_sock is 1:
                    s.send(l3pkt)
                else:
                    s.send(l2pkt)
            # parse answer for mode < 2
            if answer is True:
                parse_ans(total_answer_dict, ans)
            # record port-pair
            port_pair.append({'src': src_port, 'dst': dst_port})
    else:
        """
            Unknown L4 protocol, no port
            - TODO: support use_l3_sock
        """
        for i in range(args.num):
            if mode > 1:
                if ip_ver == 4:
                    pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                          IP(src=src_addr, dst=dst_addr, proto=proto)/payload)
                    l3pkt = IP(src=src_addr, dst=dst_addr, proto=proto)/payload
                else:
                    pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                          IPv6(src=src_addr, dst=dst_addr, nh=proto)/payload)
                    l3pkt = IPv6(src=src_addr, dst=dst_addr, proto=proto)/payload
                if answer is True:
                    if use_l3_sock is 1:
                        ans, unans = sr(l3pkt, iface=iface, timeout=timeout, verbose=False)
                    else:
                        ans, unans = srp(pkt, iface=iface, timeout=timeout, verbose=False)
                else:
                    if use_l3_sock is 1:
                        send(l3pkt, iface=iface, inter=1, verbose=False)
                    else:
                        sendp(pkt, iface=iface, inter=1, verbose=False)
            else:
                if ip_ver == 4:
                    l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                            IP(src=src_addr, dst=dst_addr, proto=proto)/payload)
                    l3pkt = IP(src=src_addr, dst=dst_addr, proto=proto)/payload
                else:
                    l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                            IPv6(src=src_addr, dst=dst_addr, nh=proto)/payload)
                    l3pkt = IPv6(src=src_addr, dst=dst_addr, nh=proto)/payload
                if answer is True:
                    if use_l3_sock is 1:
                        ans, unans = s.sr(l3pkt, timeout=timeout, verbose=False)
                    else:
                        ans, unans = s.sr(l2pkt, timeout=timeout, verbose=False)
                else:
                    if use_l3_sock is 1:
                        s.send(l3pkt)
                    else:
                        s.send(l2pkt)
            # in for-loop
            if answer is True:
                parse_ans(total_answer_dict, ans)

    print "=============================================================="
    print "Total sent packets: {}".format(args.num)
    if verbose is True and len(port_pair) > 0:
        print "Verbose Info=================================================="
        for pair in port_pair:
            print "{}:{} -> {}:{}".format(src_addr, pair['src'], dst_addr, pair['dst'])
        print "=============================================================="
    if answer is True:
        print "Total answered packets: "
        print "L3 stats:"
        print " {:<7} {}".format("IP:", total_answer_dict['ip'])
        print " {:<7} {}".format("IPv6:", total_answer_dict['ipv6'])
        print "L4 stats:"
        print " {:<7} {}".format("TCP:", total_answer_dict['tcp'])
        print " {:<7} {}".format("UDP:", total_answer_dict['udp'])
        print " {:<7} {}".format("ICMP:", total_answer_dict['icmp'])
    print "=============================================================="

def parse_ans(total_answer_dict, answer):
    for snd, rcv in answer:
        if rcv.type == g_eth_ipv4:
            total_answer_dict['ip'] = total_answer_dict['ip'] + 1
            if rcv[IP].proto == g_l4_udp:
                total_answer_dict['udp'] = total_answer_dict['udp'] + 1
            elif rcv[IP].proto == g_l4_tcp:
                total_answer_dict['tcp'] = total_answer_dict['tcp'] + 1
            elif rcv[IP].proto == g_l4_icmp:
                total_answer_dict['icmp'] = total_answer_dict['icmp'] + 1
        elif rcv.type == g_eth_ipv6:
            total_answer_dict['ipv6'] = total_answer_dict['ipv6'] + 1
            if rcv[IPv6].nh == g_l4_udp:
                total_answer_dict['udp'] = total_answer_dict['udp'] + 1
            elif rcv[IPv6].nh == g_l4_tcp:
                total_answer_dict['tcp'] = total_answer_dict['tcp'] + 1
            elif rcv[IPv6].proto == g_l4_icmp:
                total_answer_dict['icmp'] = total_answer_dict['icmp'] + 1


if __name__=='__main__':
    main()
