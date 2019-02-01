#!/bin/sh
#

start(){
    python /home/thenextshine/workspace/scripts/main.py match -e /home/thenextshine/match_home/ScorePulse.xlsx -w /home/thenextshine/match_home/sp -o /home/thenextshine/match_home/
}

stop(){
    ps -ef | grep "/home/thenextshine/workspace/scripts/main.py" | grep -v grep | cut -c 9-15 | xargs kill -9
}

status(){
    ps -ef | grep "/home/thenextshine/workspace/scripts/main.py" | grep -v grep
}

case $1 in
    "start")
            start
            ;;
    "stop")
            stop
            ;;
    "status")
            status
            ;;
    "restart")
            stop
            start
            ;;
    *)
            echo "Usage: bash run.sh [start | stop | status]"
            ;;
esac
