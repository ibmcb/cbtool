#!/bin/bash

EXPECTED_ARGS=1
if [ $# -ne $EXPECTED_ARGS ]
then
  echo "Usage: $(basename $0) <fio_terse_output_file>"
  exit 1
else
  file=$1
fi

filesz=16777216
count=0
reads=0
writes=0
rd_TotIO=0
rd_TotIOPS=0
rd_TotRUNT=0
rd_TotLAT95=0
wr_TotIO=0
wr_TotIOPS=0
wr_TotRUNT=0
wr_TotLAT95=0

# parse terse output 
while read line ; do
#  echo ${line}
  if [[ `echo ${line}|cut -d\; -f6` -ne 0 ]] ; then
    reads=1
    rd_IOPS[$count]=`echo ${line}|cut -d\; -f8`
    rd_TotIOPS=$((rd_TotIOPS + ${rd_IOPS[$count]}))
    rd_LAT95usec=`echo ${line}|cut -d\; -f29|cut -d= -f2`
    rd_LAT95[$count]=$(awk 'BEGIN { print '$rd_LAT95usec'/1000 }')
    rd_TotLAT95=$(awk 'BEGIN { print '$rd_TotLAT95' + '${rd_LAT95[$count]}' }')
  fi
  if [[ `echo ${line}|cut -d\; -f47` -ne 0 ]] ; then
    writes=1
    wr_IOPS[$count]=`echo ${line}|cut -d\; -f49`
    wr_TotIOPS=$((wr_TotIOPS + ${wr_IOPS[$count]}))
    wr_LAT95usec=`echo ${line}|cut -d\; -f70|cut -d= -f2`
    wr_LAT95[$count]=$(awk 'BEGIN { print '$wr_LAT95usec'/1000 }')
    wr_TotLAT95=$(awk 'BEGIN { print '$wr_TotLAT95' + '${wr_LAT95[$count]}' }')
  fi
  count=$((count + 1))
done <<< "$(grep fiofile ${file})"

# calculate stdev and %dev values
if [[ $reads -eq 1 ]] ; then
  rd_avgIOPS=$(awk 'BEGIN { print '$rd_TotIOPS'/'$count' }')
  rd_iopSD=`for n in ${rd_IOPS[*]} ; do echo $n; done | awk '{delta = $1 - avg; avg += delta / NR; mean2 += delta * ($1 - avg); } END { print sqrt(mean2 / NR); }'`
  rd_iopPD=$(awk 'BEGIN { print 100 * '$rd_iopSD'/'$rd_avgIOPS' }')
  rd_avgLAT95=$(awk 'BEGIN { print '$rd_TotLAT95'/'$count' }')
  rd_LAT95SD=`for n in ${rd_LAT95[*]} ; do echo $n; done | awk '{delta = $1 - avg; avg += delta / NR; mean2 += delta * ($1 - avg); } END { print sqrt(mean2 / NR); }'`
  rd_LAT95PD=$(awk 'BEGIN { print 100 * '$rd_LAT95SD'/'$rd_avgLAT95' }')
fi

if [[ $writes -eq 1 ]] ; then
  wr_avgIOPS=$(awk 'BEGIN { print '$wr_TotIOPS'/'$count' }')
  wr_iopSD=`for n in ${wr_IOPS[*]} ; do echo $n; done | awk '{delta = $1 - avg; avg += delta / NR; mean2 += delta * ($1 - avg); } END { print sqrt(mean2 / NR); }'`
  wr_iopPD=$(awk 'BEGIN { print 100 * '$wr_iopSD'/'$wr_avgIOPS' }')
  wr_avgLAT95=$(awk 'BEGIN { print '$wr_TotLAT95'/'$count' }')
  wr_LAT95SD=`for n in ${wr_LAT95[*]} ; do echo $n; done | awk '{delta = $1 - avg; avg += delta / NR; mean2 += delta * ($1 - avg); } END { print sqrt(mean2 / NR); }'`
  wr_LAT95PD=$(awk 'BEGIN { print 100 * '$wr_LAT95SD'/'$wr_avgLAT95' }')
fi

# output calculated results
#echo -e "\tIOPS\t95th%\tRTIME\t%IO\tavg95th"
if [[ $reads -eq 1 ]] ; then
  echo -e "Read \t"$rd_TotIOPS"\t"$rd_avgLAT95
fi
if [[ $writes -eq 1 ]] ; then
  echo -e "Write \t"$wr_TotIOPS"\t"$wr_avgLAT95
fi

