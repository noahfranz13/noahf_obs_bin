#!/usr/bin/env python
"""
Tools for running stuff remotely
"""

import datetime
from fabric import Connection
import invoke
from invoke import Responder
import paramiko
import random
import socket
import sys
import time

import machines

DC, HOST = machines.where_are_we()
if DC == machines.BERKELEY:
    CONDA_SH = "/home/obs/miniconda3/etc/profile.d/conda.sh"
else:
    CONDA_SH = "/opt/conda/etc/profile.d/conda.sh"
PY_ENV = f"source {CONDA_SH} && conda activate pipeline &&"


def maybe_run(host, conn, command, python=False):
    """
    Runs a command if a connection is provided.
    Prints out what it would do either way.
    """
    if python:
        command = PY_ENV + " " + command
    if conn is not None:
        print(f"[{datetime.datetime.now()}] Running on {host}:")
    else:
        print(f"Pretending to run this on {host}:")
    print(command, flush=True)
    if conn is not None:
        try:
            conn.run(command)
        except invoke.exceptions.UnexpectedExit:
            print(f"failure on {host} while running {command}")
            sys.exit(1)

            
def retry_ssh(f, retry_on_script_failure=False):
    """
    Runs f() but retries with ssh failures.
    """
    retries = 10
    for i in range(1, retries + 1):
        try:
            return f()
        except (paramiko.ssh_exception.SSHException, socket.gaierror) as e:
            print(f"ssh failure {i}: {e}")
            if i == retries:
                raise
            time.sleep(10)
        except invoke.exceptions.UnexpectedExit as e:
            if not retry_on_script_failure:
                raise
            print(f"script failure {i}: {e}")
            if i == retries:
                raise
            time.sleep(10)
    raise RuntimeError("control should not reach here")
            

def retry_connect(host):
    return retry_ssh(lambda: Connection(host))


def get_lines(result):
    """
    Helper to get the lines from command output.
    """
    out = result.stdout.strip()
    if not out:
        return []
    return out.split("\n")


def run_one(host, command, hide=True, python=False):
    if python:
        command = PY_ENV + " " + command
    with Connection(host) as c:
        result = c.run(command, hide=hide)
        return get_lines(result)

    
def retry_run_one(host, cmd, hide=True, python=False, retry_on_script_failure=False):
    return retry_ssh(lambda: run_one(host, cmd, hide=hide, python=python), retry_on_script_failure=retry_on_script_failure)


def best_gpu(host):
    """
    Finds the best GPU to use on the given host.
    Our heuristic is, we want at least 1G of free memory, and after that we pick the least
    utilized.
    Returns a (gpu id, utilization, MB memory) tuple.
    Raises IOError if all GPU memory is full.
    """
    candidates = []
    lines = retry_run_one(host, "nvidia-smi --query-gpu=utilization.gpu,memory.free --format=csv,noheader,nounits")
    for gpu_id, line in enumerate(lines):
        util, free = map(int, line.strip().split(", "))
        if free >= 1000:
            candidates.append((util, random.random(), gpu_id, free))
    if not candidates:
        raise IOError("there is no free GPU memory in the cluster")
    candidates.sort()
    util, _, gpu_id, free = candidates[0]
    return (gpu_id, util, free)


def count_processes(host, process_name):
    return int(retry_run_one(host, f"ps aux | grep ^obs.*{process_name} | grep -v grep | wc -l")[0])


def heuristic_usage(host, process_name):
    """
    Returns an integer that doesn't mean anything except it roughly corresponds to usage.
    """
    answer = count_processes(host, process_name)
    if host == "bls9":
        # bls9 has more ram than the other blsx so put more stuff on it
        answer //= 2
    return answer


def choose_underused(machines, process_name):
    """
    Heuristically choose a machine from the given list that has a low number of processes with this name.
    Return (machine, usage)
    """
    copy = list(machines)
    random.shuffle(copy)
    candidates = copy[:2]
    usage = [(heuristic_usage(m, process_name), m) for m in candidates]
    usage.sort()
    count, host = usage[0]
    return (host, count)
