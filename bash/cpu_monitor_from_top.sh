#!/bin/bash

REPORT="time_report.csv"

print_cpu_stats()
{
    # $1 = pid
    # $2 = timeout
    IFS=
    stats="$(top -p $1 -b -n $2)"
    # printf "%s" $stats
    # echo $stats

    declare -i line=3
    declare -i offset=9

    for (( i = 0; i < $2; ++i ));
    do
        head=$(( $i*9 + 3))
        # echo "$head"
        us_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $2}')
        sy_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $4}')
        ni_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $6}')
        id_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $8}')
        wa_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $10}')
        hi_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $12}')
        si_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $14}')
        st_time=$(echo $stats | head -n $head | tail -n 1 | awk '{print $16}')

        printf "%.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f\n" $us_time $sy_time $ni_time $id_time $wa_time $hi_time $si_time $st_time >> $REPORT
    done
}

main()
{
    print_cpu_stats $1 $2
}

main $1 $2
