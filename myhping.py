#!/usr/bin/env python
"""
Author: Kevin Cyu, scyu@a10networks.com
"""
import argparse, sys, socket, random, struct, time
from scapy.all import *

g_port_max = 65535
g_eth_ipv4 = 0x0800
g_eth_ipv6 = 0x86DD
g_l4_udp = 0
g_l4_tcp = 1

# printing format offset
loff = 30
roff = 20

def main():
    parser = argparse.ArgumentParser()

    # program parameter config
    parser.add_argument('--intf', type=str, help="Sending interface (default=ens19)", default="ens19")
    parser.add_argument('--num', type=int, help="Send total N packets (default=1)", default=1)
    parser.add_argument('--ipv', type=int, help="IP version (4 or 6)", default=6)
    parser.add_argument('--mode', type=int, help="Set mode (0=iterative, 1=random, 2=slow)", default=0)
    parser.add_argument('--use-gw', help="Use Gateway as dmac", action="store_true")
    # L3 (v4)
    parser.add_argument('--sip', type=str, help="Source IP address", default="20.20.20.225")
    parser.add_argument('--dip', type=str, help="Destination IP address", default="20.20.101.226")
    parser.add_argument('--gw', type=str, help="Setup Default gateway address", default="20.20.20.1")
    # L3 (v6)
    parser.add_argument('--sipv6', type=str, help="Source IPv6 address (only enable when ip version = 6)", default="2001:20:20:20::225")
    parser.add_argument('--dipv6', type=str, help="Destination IPv6 address (only enable when ip version = 6)", default="2001:20:20:101::226")
    parser.add_argument('--gwv6', type=str, help="Setup Default gateway address (v6, only enable when ip version = 6)", default="2001:20:20:20::1")
    # L4
    parser.add_argument('--sport', type=int, help="Source Port number", default=-1)
    parser.add_argument('--dport', type=int, help="Destination Port number", default=-1)
    parser.add_argument('--port', type=int, help="Start Src Port number", default=1)
    parser.add_argument('--proto', type=int, help="Specify L4 Protocol, UDP: 0(default), TCP: 1.", default=0, choices=range(0, 2))
    # optional
    # parser.add_argument('--payload', help="Enable customized payload content.", action="store_true")
    parser.add_argument('--payload-len', type=int, help="Total length of payload filled with 'A'.", default=0)
    parser.add_argument('--payload-content', type=str, help="Customized Payload content (disable --payload-len)", default="")


    # parse
    args = parser.parse_args()

    # get value for arguments
    iface = args.intf
    ip_ver = args.ipv
    src_addr = args.sip if ip_ver == 4 else args.sipv6
    dst_addr = args.dip if ip_ver == 4 else args.dipv6
    gateway = args.gw if ip_ver == 4 else args.gwv6
    sport = args.sport
    dport = args.dport
    start_port = args.port
    proto = args.proto
    l4_proto = ["UDP", "TCP"]
    if l4_proto[proto] == None:
        print "Invalid l4 protocol, use UDP (default)"
        proto = 0
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

    s = conf.L2socket(iface)
    smac = get_if_hwaddr(iface)
    dmac = ""

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
    print "{} {}".format("Interface:".ljust(loff, ' '), iface.rjust(roff, ' '))
    print "{} {}".format("IP version:".ljust(loff, ' '), str(ip_ver).rjust(roff, ' '))
    print "{} {}".format("Source IP address:".ljust(loff, ' '), src_addr.rjust(roff, ' '))
    print "{} {}".format("Destination IP address:".ljust(loff, ' '), dst_addr.rjust(roff, ' '))
    print "{} {}".format("L4 Protocol:".ljust(loff, ' '), l4_proto[proto].rjust(roff, ' '))
    print "{} {}".format("Source Port number:".ljust(loff, ' '), (str(sport).rjust(roff, ' ') if sport > 0 else str(start_port).rjust(roff, ' ')))
    print "{} {}".format("Destination Port number:".ljust(loff, ' '), (str(dport).rjust(roff, ' ') if dport > 0 else "Not specified".rjust(roff, ' ')))
    print "{} {}".format("Start Src port number:".ljust(loff, ' '), str(start_port).rjust(roff, ' '))
    print "Sending mode=================================================="
    print modes[mode]
    print "Payload ======================================================"
    print "{} {}".format("Customized payload: ".ljust(loff, ' '), "enable".rjust(roff, ' ') if payload_len > 0 or len(payload_content) > 0 else "disable".rjust(roff, ' '))
    if len(payload_content) > 0:
        payload = payload_content
        print "{} {}".format("Payload content: ".ljust(loff, ' '), payload_content.rjust(roff, ' '))
    else:
        payload = "A" * payload_len
        print "{} {}".format("Payload length: ".ljust(loff, ' '), str(payload_len).rjust(roff, ' '))
    print "Static config================================================="
    print "{} {}[{}]".format("Default Gateway:".ljust(loff, ' '), gateway.rjust(roff, ' '), "enable" if args.use_gw is True else "disable")
    #print "Added route: [GW={}, Prefix={}, Dev={}]".format(gateway, prefix, iface)
    print "Packet out===================================================="
    print "Sending on interface {}({} -> {}) to IPv{} addr {}".format(iface, smac, dmac, ip_ver, str(dst_addr))


    for i in range(args.num):
        if args.mode is 0:
            src_port = sport if sport > 0 else (i + start_port)%g_port_max
            dst_port = dport if dport > 0 else (i + start_port)%g_port_max
        elif args.mode is 1:
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
                    pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                          IP(src=src_addr, dst=dst_addr)/udp/payload)
                elif proto is g_l4_tcp:
                    pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                          IP(src=src_addr, dst=dst_addr)/tcp/payload)
            else:
                if proto is g_l4_udp:
                    pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                          IPv6(src=src_addr, dst=dst_addr)/udp/payload)
                elif proto is g_l4_tcp:
                    pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                          IPv6(src=src_addr, dst=dst_addr)/tcp/payload)
            # send packet slowly
            sendp(pkt, iface=iface, inter=1)
            continue
        udp = UDP(sport=src_port, dport=dst_port)
        tcp = TCP(sport=src_port, dport=dst_port)
        if ip_ver == 4:
            if proto is g_l4_udp:
                l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                        IP(src=src_addr, dst=dst_addr)/udp/payload)
            elif proto is g_l4_tcp:
                l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv4)/
                        IP(src=src_addr, dst=dst_addr)/tcp/payload)
        else:
            if proto is g_l4_udp:
                l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                        IPv6(src=src_addr, dst=dst_addr)/udp/payload)
            elif proto is g_l4_tcp:
                l2pkt = (Ether(src=smac, dst=dmac, type=g_eth_ipv6)/
                        IPv6(src=src_addr, dst=dst_addr)/tcp/payload)
        # send packet with high speed
        s.send(l2pkt)

    print "=============================================================="
    print("Total packets: ", args.num)

if __name__=='__main__':
    main()
