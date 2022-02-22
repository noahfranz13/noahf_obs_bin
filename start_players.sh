#!/bin/bash

# Ensure that we run as root
if [ $UID -ne 0 ]
then
  exec sudo $0 "${@}"
  # Should "never" get here
  exit 1
fi

SIM=''
TEST=''
VERBOSE='-v'
# Parse options
while getopts 'stv' OPT
do
  case "${OPT}" in
    s) SIM='-s'
      ;;
    t) TEST='-t'
      ;;
    v) VERBOSE='-vv'
      ;;
    ?) exit 1
      ;;
  esac
done
shift $((OPTIND-1))

# sim and test are mutually exclusive
if [ -n "${SIM}" -a -n "${TEST}" ]
then
  echo cannot do both sim and test at the same time
  exit 1
fi

hosts="${@:-$(echo blc{0..0}{0..7})}"
#hosts="${@:-$(echo blc{0..1}{0..7})}"

simtest="${SIM:+simulate}${TEST:+test}"

pidx=0

for host in $hosts
do
  # Ideally this would be determined dynamically instead of hard coded,
  # but for now it's hard coded.
  case ${host} in
    blc[01]?) CORE_LO=7; CORE_HI=11 # 6 cores per CPU
              ;;
    blc[234567]?) CORE_LO=9; CORE_HI=15 # 8 cores per CPU
              ;;
    *) echo skipping unknown host ${host};
       continue
       ;;
  esac

  # In test mode, players are named after host (and BLPx0 players are skipped).
  if [ -n "${TEST}" ]
  then
    # Massage host name to get player name
    player=${host/blc/BLP}
    # If player ends with 0 (or has no length)
    if [ -z "${player##*0}" ]
    then
      echo "not starting player ${player} in test mode"
      continue
    fi
  else
    # In non-test mode, players are named according to order given.
    player=$(printf BLP%02o $pidx)
    pidx=$((pidx+1))
  fi

  # blc22 seems to be fixed, so this special case is commented out
  # until it can be confirmed that it is fixed (and this section deleted).
  ## Special case to skip blc22, which has a flaky link
  #if [ "${host}" == "blc22" ]
  #then
  #  continue
  #fi

  echo "starting player ${player} on $host${simtest:+ in $simtest mode}"
  ssh  -o BatchMode=yes -o ConnectTimeout=1 -n -f $host "sh -c 'taskset -c ${CORE_LO}-${CORE_HI} nohup /home/obs/bin/start_player_local.sh ${VERBOSE} ${SIM} ${player}'" &
done

wait
