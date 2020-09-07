#!/usr/bin/python2
#coding:utf-8
import os, time, subprocess, argparse

def sort_dict(input_dict):
    items = input_dict.items()
    items.sort()
    return [value for key, value in items]

def run_pmap_sum(pid):
    cmd = "pmap -p {}".format(pid)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    stdout = p.stdout.read()
    lines = stdout.split('\n')
    # stdout format (pmap's):
    # 00000000006de000     24K rw--- /root/http_srv_grp/tim/tim_srv
    # ...

    memory={} # dict
    for i in range(1, len(lines)-2): # skip first one (program name) and last two (total, nextline)
        key = lines[i].split()[1]
        key = key[:-1] # remove last char (K)
        key = int(key) # str to int
        if key in memory:
            memory[key] = memory[key]+1
        else:
            memory[key] = 1

    # list the summry
    total_mem = 0
    print "=========================="
    for key in sorted(memory.keys()):
        total_mem += key*memory[key]
        pstr = '%-8d KB: %d' % (key, memory[key])
        print pstr
    print "=========================="
    print "Total {} KB.".format(total_mem)

if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pid", help="Specify process id", default="1")
    args = parser.parse_args()
    print "=========================="
    print "Pid={}".format(args.pid)

    run_pmap_sum(args.pid)
