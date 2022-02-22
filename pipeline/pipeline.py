#!/usr/bin/env python

import argparse
import datetime
from fabric import Connection
import getpass
import hashlib
import invoke
import os
import random
import re
import remote
import sys
import time

import bldw
from cadence import good_cadences_for_session
import disk_info
import machines
import priority
from schedule_scraper import Scraper

# Check Python version
if not sys.version_info >= (3, 8):
    raise RuntimeError(f"unsupported Python version: {sys.version_info}")

BLC_HOSTS = [f"blc{x}{y}" for x in range(8) for y in range(8)]

BLPD_MACHINE = "blpd18"

BLPC_HOSTS = [f"blpc{n}" for n in range(3)]

TURBOSETI_OUTPUT = "/home/obs/turboseti"

# Amount of space to leave free on bls machines
BLS_BUFFER_TB = 3

def hash_string(string):
    return abs(int(hashlib.sha256(string.encode("utf8")).hexdigest(), 16))


def match_shard(string, shard):
    """
    Shard should be number/total, like 0/3, 1/3, 2/3.
    String is anything.
    """
    if shard is None:
        # Everything matches when we're not using shards
        return True
    num_str, total_str = shard.split("/")
    num = int(num_str)
    total = int(total_str)
    assert 0 <= num < total
    assert total > 0
    target = hash_string(string + "salt7") % total
    return target == num


def get_session(shard):
    session = os.environ.get("SESSION")
    if not session:
        session = priority.choose_session(condition=lambda s: match_shard(s, shard))
    assert re.fullmatch("AGBT[0-9][0-9][AB]_[0-9]+_[0-9]+", session), f"bad session name: {session}"        
    return session


def find_unmoved(session, host, directory):
    """
    Finds a list of directories that contain .fil files on the given host and directory.
    These are candidates for moving.
    We skip files containing DIAG and also skip certain sessions.
    """
    machines.assert_green_bank_head()

    find_cmd = f"find {directory}/dibas*/{session}/GUPPI/BLP?? -maxdepth 1 -name '*.fil'"
    # print("running", find_cmd, flush=True)
    try:
        filenames = remote.retry_run_one(host, find_cmd)
    except invoke.exceptions.UnexpectedExit as e:
        if "No such file or directory" in str(e):
            return []
        raise
    session_set = set()
    fil_set = set()
    diag_set = set()
    has_blc = set()
    for filename in filenames:
        session_dir, basename = filename.rsplit("/", 1)

        if "DIAG" in filename:
            continue
        if "broken" in filename:
            continue
        if "/mnt_blc18" in filename:
            continue
        
        if basename.startswith("blc"):
            # A directory with no /blc files is one of the ones that has been moved and then accidentally re-processed
            has_blc.add(session_dir)
        
        parts = basename.split(".")
        base_prefix, filetype = parts[0], parts[-1]
        if filetype == "fil":
            fil_set.add((session_dir, base_prefix))
            session_set.add(session_dir)
        else:
            raise ValueError(f"weird filename: {filename}")

    answer = list(session_set.intersection(has_blc) - diag_set)
    answer.sort()
    return answer


def find_unconverted(host=None):
    """
    Finds a list of unconverted fil files.
    """
    machines.assert_green_bank_head()    
    if host is None:
        find_host = "bls*"
        run_host = "bls0"
    else:
        assert host in machines.BLS_MACHINES, f"bad host: {host}"
        find_host = host
        run_host = host
    find_cmd = f"find /mnt_{find_host}/datax*/pipeline/*GBT*/ -name '*.fil' -o -name '*move.done'"
    filenames = remote.retry_run_one(run_host, find_cmd, retry_on_script_failure=True)
    ok_dirs = set(f.rsplit("/", 1)[0] for f in filenames if f.endswith("move.done"))
    fils = [f for f in filenames if f.endswith(".fil") and f.rsplit("/", 1)[0] in ok_dirs]
    fils.sort()
    return fils


def find_untransferred():
    """
    Finds a list of directories ready to transfer, with h5 files but no fil files.
    """
    machines.assert_green_bank_head()
    find_host = "bls*"
    run_host = "bls0"
    find_cmd = f"find /mnt_{find_host}/datax*/pipeline/*GBT*/ -name '*.fil' -o -name '*.h5' -o -name '*transfer.done'"
    filenames = remote.retry_run_one(run_host, find_cmd, retry_on_script_failure=True)
    skip_dirs = set()
    h5_dirs = set()
    for filename in filenames:
        if "bls8" in filename:
            # Transfer speeds off bls8 are super-slow right now. Disable until it's fixed.
            continue
        dirname = filename.rsplit("/", 1)[0]
        if filename.endswith(".fil"):
            skip_dirs.add(dirname)
        elif filename.endswith("transfer.done"):
            skip_dirs.add(dirname)
        elif filename.endswith(".h5"):
            h5_dirs.add(dirname)
        else:
            raise RuntimeError(f"logic bug, unexpected filename {filename}")
    answer = [f for f in h5_dirs if f not in skip_dirs]
    answer.sort()
    return answer


def move(source_host, source_dir, target_host, target_disk, run=False):
    print(f'move("{source_host}", "{source_dir}", "{target_host}", "{target_disk}", run={run})')
    machines.assert_green_bank_head()    
    assert getpass.getuser() == "obs"
    assert re.fullmatch("blc[0-8]{2}", source_host), source_host
    assert re.fullmatch("/datax[0-9]?/dibas[0-9.]{0,9}/.GBT[0-9]{2}[AB]_[0-9]{3}_[0-9]{1,3}/GUPPI/BLP[0-9]{2}", source_dir), source_dir
    assert re.fullmatch("bls[0-9]", target_host), target_host
    assert re.fullmatch("/datax[0-9]?", target_disk), target_disk

    session_id = source_dir.split("/")[3]
    blp_dir = source_dir.split("/")[-1].lower()
    assert re.fullmatch("blp[0-9]{2}", blp_dir)
    target_dir = "/".join([target_disk, "pipeline", session_id, f"{source_host}_{blp_dir}"])
    mounted_source_dir = f"/mnt_{source_host}{source_dir}"

    # Check that we haven't already moved something to this directory
    remote.run_one(target_host, f"test ! -f {target_dir}/move.done")
    
    # Check for out-of-range files
    command = f"/home/obs/bin/pipeline/check_frequency.py {mounted_source_dir}"
    lines = remote.run_one(target_host, command, hide=False, python=True)
    if lines[-1] == "INVALID":
        print(f"moved {mounted_source_dir} to the invalid directory")
        return
    assert lines[-1] == "OK"
    
    try:
        if run:
            conn = remote.retry_connect(target_host)
        else:
            conn = None

        remote.maybe_run(target_host, conn, f"mkdir -p {target_dir}")
        remote.maybe_run(target_host, conn, f"rsync --remove-source-files -av --exclude='*DIAG*' --include='*.fil' --exclude='*' {mounted_source_dir}/ {target_dir}/")
        remote.maybe_run(target_host, conn, f"find {target_dir} -name '*.fil' -size -2k -delete")
        remote.maybe_run(target_host, conn, f"touch {target_dir}/move.done")
    finally:
        if conn is not None:
            conn.close()
        

def parse_mounted_filename(mounted_filename):
    """
    Returns host, dirname, basename where the dirname is how you'd refer to it on the local system.
    """
    _, mnt, fname_tail = mounted_filename.split("/", 2)
    fname = "/" + fname_tail
    host = mnt.split("_")[1]
    dirname, basename = fname.rsplit("/", 1)
    return host, dirname, basename


def convert(mounted_filename, run=False):
    print(f'convert("{mounted_filename}", run={run})')
    machines.assert_green_bank_head()    
    assert getpass.getuser() == "obs"
    assert re.fullmatch("/mnt_bls[0-9]/datax[0-9]?/pipeline/.*fil", mounted_filename), mounted_filename

    # We want to operate on the non-nfs mount
    host, dirname, basename = parse_mounted_filename(mounted_filename)
    fname = dirname + "/" + basename
    h5name = fname[:-4] + ".h5"
    
    try:
        if run:
            conn = remote.retry_connect(host)
        else:
            conn = None

        # chain_fixup overwrites ra/dec information in the file with ra/dec information in the database.
        # this is disabled under suspicion of not being entirely correct. at least if we don't overwrite
        # the header we maintain the ability to debug later.
        # remote.maybe_run(host, conn, f"/home/obs/bin/chain_fixup {fname}", python=True)

        remote.maybe_run(host, conn, f"cd {dirname} && fil2h5 {basename}", python=True)
        remote.maybe_run(host, conn, f"/home/obs/bin/pipeline/check_h5.py {h5name}", python=True)
        remote.maybe_run(host, conn, f"mv {fname} {fname}.x2h")
    finally:
        if conn is not None:
            conn.close()

            
def transfer(directory, run=False):
    print(f'transfer("{directory}", run={run})')
    machines.assert_green_bank_head()    
    assert getpass.getuser() == "obs"
    assert not directory.endswith("/")
    assert re.fullmatch("/mnt_bls[0-9]/datax[0-9]?/pipeline/.*", directory), directory

    # We want to operate on the non-nfs mount
    _, mnt, dirname_tail = directory.split("/", 2)
    dirname = "/" + dirname_tail
    host = mnt.split("_")[1]
    destination = f"rsync://{BLPD_MACHINE}.ssl.berkeley.edu/datax"
    
    # We want to rsync the folder tree starting at "pipeline" and going to {dirname}, so
    # that we don't have rsync collisions.
    root, branch = dirname.split("/pipeline/")
    parts = ["pipeline"] + branch.split("/")
    includes = []
    for n in range(1, len(parts) + 1):
        includes.append("/".join(parts[:n]) + "/")
    includes.append(f"pipeline/{branch}/*.h5")
    includes.append(f"pipeline/{branch}/zmanifest.csv")
    include_args = " ".join(f'--include="{x}"' for x in includes)
    rsync = f'rsync -avW --block-size=16384 --ignore-existing {include_args} --exclude="*" {root}/ {destination}'
    
    try:
        if run:
            conn = remote.retry_connect(host)
        else:
            conn = None

        remote.maybe_run(host, conn, f"/home/obs/bin/pipeline/track.py {dirname} --dir", python=True)
        remote.maybe_run(host, conn, f"/home/obs/bin/pipeline/manifest.py {dirname}", python=True)
        remote.maybe_run(host, conn, rsync)
        remote.maybe_run(host, conn, f"touch {dirname}/transfer.done")
        
    finally:
        if conn is not None:
            conn.close()

            
def archive(directory, run=False):
    """
    Note: this directory is a path local to BLPD_MACHINE. It will be slow if it's an NFS mount.
    """
    print(f'archive("{directory}", run={run})')
    machines.assert_berkeley_head()
    assert getpass.getuser() == "obs"
    assert not directory.endswith("/")
    assert re.fullmatch(".*/incoming/pipeline/.*", directory), directory
    host = BLPD_MACHINE
    incoming_dir, session_dir = directory.split("/pipeline/")
    destination = f"/datag/pipeline/{session_dir}"

    find_cmd = f"find {directory} -maxdepth 1 -name '*.h5'"
    filenames = remote.retry_run_one(host, find_cmd, retry_on_script_failure=True)
    basenames = [os.path.basename(filename) for filename in filenames]
    
    try:
        if run:
            conn = remote.retry_connect(host)
        else:
            conn = None

        remote.maybe_run(host, conn, f"/home/obs/obs_bin/pipeline/validate_manifest.py {directory}", python=True)
        remote.maybe_run(host, conn, f"mkdir -p {destination}")
        for basename in basenames:
            remote.maybe_run(host, conn, f"test ! -f {destination}/{basename}")
            remote.maybe_run(host, conn, f"mv {directory}/{basename} {destination}/")
            remote.maybe_run(host, conn, f"/home/obs/obs_bin/pipeline/track.py {destination}/{basename} --copy", python=True)
        remote.maybe_run(host, conn, f"/home/obs/obs_bin/pipeline/clean_up_incoming.py {directory}", python=True)
            
    finally:
        if conn is not None:
            conn.close()


def turboseti_retry(h5file):
    """
    Retries after remote errors.
    """
    for _ in range(20):
        try:
            turboseti_no_retry(h5file, run=True)
            return
        except invoke.exceptions.UnexpectedExit:
            print("retrying...")
            pass
    raise RuntimeError("too many retries")

        
def turboseti_no_retry(h5file, run=False):
    """
    Run turboseti on the provided h5 file, putting output in its own directory.
    """
    print(f'turboseti("{h5file}", run={run})')
    machines.assert_berkeley_head()
    assert getpass.getuser() == "obs"
    m = re.fullmatch(r"/datag/pipeline/(.*)\.h5", h5file)
    assert m, f"bad h5 filename: {h5file}"
    destination = f"{TURBOSETI_OUTPUT}/{m.group(1)}"

    host, count = remote.choose_underused(BLPC_HOSTS, "turboSETI")
    print(f"using {host} because it is only running {count} turboSETI processes")
    gpu_id, util, free = remote.best_gpu(host)
    print(f"using GPU {gpu_id} because it has {free}MiB free and is {util}% utilized")

    try:
        if run:
            conn = remote.retry_connect(host)
        else:
            conn = None

        remote.maybe_run(host, conn, f"/home/obs/obs_bin/pipeline/turboseti.sh {h5file} {destination} {gpu_id}", python=True)
            
    finally:
        if conn is not None:
            conn.close()


def turboseti(h5file, run=False):
    if run:
        turboseti_retry(h5file)
    else:
        turboseti_no_retry(h5file, run=False)


def events(cadence, freq, run=False):
    host = random.choice(BLPC_HOSTS)
    try:
        if run:
            conn = remote.retry_connect(host)
        else:
            conn = None

        remote.maybe_run(host, conn, f"/home/obs/obs_bin/pipeline/find_events.py {cadence} {freq} /home/obs/events/{cadence}/{freq}",
                         python=True)
            
    finally:
        if conn is not None:
            conn.close()
    

def suggest_events():
    """
    Returns a tuple of (args, summary) for an events command.
    args is None if we have no command to suggest.
    """
    machines.assert_berkeley_head()
    dw = bldw.retry_connection()
    sessions = remote.retry_run_one("blpc0", "ls /datag/pipeline")
    events_dir = "/home/obs/events"
    if not sessions:
        raise ValueError("no sessions found. is /datag inaccessible?")
    summary = [f"we have data for {len(sessions)} sessions."]
    total_completed = 0
    for session in sessions:
        completed = 0
        for cadence in good_cadences_for_session(dw, session):
            for freq in cadence.representative_freqs():
                metas = cadence.metas_for_event_stage(freq)
                if not metas:
                    continue

                cfdir = f"{events_dir}/{cadence.id}/{freq}"
                if os.path.exists(cfdir):
                    # We already processed this cadence-frequency pair
                    completed += 1
                    total_completed += 1
                    continue
                summary.append(f"directory {cfdir} does not exist")
                summary.append(f"we have processed {total_completed} cadence-frequency pairs across all sessions.")
                summary.append(f"we have processed {completed} cadence-frequency pairs from session {session}.")
                summary.append(f"cadence {cadence.id} frequency {freq} is now ready for events processing.")
                return ([cadence.id, freq], summary)
        summary.append(f"we have processed all {completed} cadence-frequency pairs from session {session}.")
    summary.append(f"we have processed {total_completed} cadence-frequency pairs across all sessions.")
    summary.append("events phase is up to date.")
    return (None, summary)
                
        
def suggest_turboseti(shard=None):
    """
    Returns a tuple of (args, summary) for a turboseti command.
    args is None if we have no command to suggest.
    """
    machines.assert_berkeley_head()

    summary = []

    c = bldw.Connection()

    # For now, only run turboseti on the non-spliced 0000 files
    for meta in c.iter_metadata_where("location LIKE %s AND location NOT LIKE %s", ("file://pd%0000.h5", "%spliced%")):
        h5file = meta.filename()
        if not match_shard(h5file, shard):
            continue
        
        # Figure out which stdout.log would be created
        stdout = h5file.replace("/datag/pipeline", TURBOSETI_OUTPUT).replace(".h5", "/stdout.log")
        if not os.path.exists(stdout):
            return ([h5file], [f"no stdout file at {stdout}", f"ready for turboseti: {h5file}"])

    return (None, [f"no files are ready for turboseti"])

        
def suggest_archive(host=None, shard=None):
    """
    Returns a tuple of (args, summary) for an archive command.
    args is None if we have no command to suggest.
    """
    if host is not None:
        raise RuntimeError("archive host not implemented yet")
    host = BLPD_MACHINE
    
    machines.assert_berkeley_head()

    avail = disk_info.gluster_tb()
    if avail < 50:
        raise RuntimeError("we are running too low on gluster space")

    summary = [f"gluster has {avail:.1f}T available."]
    incoming = "/datax/incoming/pipeline"
    find_cmd = f"find {incoming} -name '*zmanifest.csv'"
    manifests = remote.retry_run_one(host, find_cmd, retry_on_script_failure=True)
    all_dirs = [manifest.rsplit("/", 1)[0] for manifest in manifests]
    dirs = [d for d in all_dirs if match_shard(d, shard)]

    if shard:
        dirs_noun_phrase = f"directories from shard {shard} (out of {len(all_dirs)} on all shards)"
    else:
        dirs_noun_phrase = "directories"
    if not dirs:
        return (None, summary + [f"no {dirs_noun_phrase} are ready for archiving"])

    dirs.sort(key=file_priority)
    dirs.reverse()
    
    summary.append(f"{len(dirs)} directories are ready for archiving, such as:")
    for dirname in dirs[:10]:
        summary.append(dirname)
    return ([dirs[0]], summary)
        

def suggest_transfer(host=None, shard=None):
    """
    Returns a tuple of (args, summary) for a transfer command.
    args is None if we have no command to suggest.
    """
    if host is not None:
        raise RuntimeError("transfer host not implemented yet")

    machines.assert_green_bank_head()
    summary = []

    # Check if any directories are ready for transferring
    all_untransferred = find_untransferred()
    dirs = [d for d in all_untransferred if match_shard(d, shard)]
    if shard:
        dirs_noun_phrase = f"directories from shard {shard} (out of {len(all_untransferred)} on all shards)"
    else:
        dirs_noun_phrase = "directories"
    if not dirs:
        return (None, [f"no {dirs_noun_phrase} are ready for transferring"])

    dirs.sort(key=file_priority)
    dirs.reverse()
    
    summary.append(f"{len(dirs)} {dirs_noun_phrase} are ready for transferring, such as:")
    for dirname in dirs[:10]:
        summary.append(dirname)
    return ([dirs[0]], summary)


def file_priority(fname):
    """
    We have thundering-herd effects when shards pick files systematically.
    However, stages that need entire directories to be processed are delayed if
    we pick randomly among all files.
    To avoid that, we want to first process newer sessions, but within sessions
    we pick randomly.
    Processing the highest file_priority files first does this.
    Returns (session, tiebreaker).
    """
    session = fname.split("pipeline/")[-1].split("/")[0]
    return (session, random.random())


def suggest_convert(shard=None):
    """
    Returns a tuple of (args, summary) for a convert command.
    args is None if we have no command to suggest.
    """
    machines.assert_green_bank_head()    
    summary = []
    
    # Check if any files are ready for converting.
    all_unconverted = find_unconverted()
    fils = [fil for fil in all_unconverted if match_shard(fil, shard)]
    if shard:
        files_noun_phrase = f"files from shard {shard} (out of {len(all_unconverted)} on all shards)"
    else:
        files_noun_phrase = "files"
    if not fils:
        return (None, [f"no {files_noun_phrase} are ready for converting."])

    fils.sort(key=file_priority)
    fils.reverse()
    
    summary.append(f"{len(fils)} {files_noun_phrase} are ready for converting.")

    # Figure out which host to go for.
    hosts = set()
    with_host = []
    for fil in fils:
        host, _, _ = parse_mounted_filename(fil)
        with_host.append((host, fil))
        hosts.add(host)

    host, count = remote.choose_underused(list(hosts), "fil2h5")
    if host != "bls9" and count >= 6:
        # This is going to overload the machine if we keep piling on.
        # bls9 has 3x the ram so we shouldn't run into trouble there.
        summary.append(f"host {host} is too busy right now. waiting.")
        return (None, summary)

    fils = [fil for (h, fil) in with_host if h == host]
    summary.append(f"{len(fils)} files to process on {host}:")
    for fname in fils[:5]:
        summary.append(fname)
    return ([fils[0]], summary)
    

def enough_disk_space(disks):
    """
    A heuristic to see if we have enough disk space.
    """
    if len(disks) >= 3:
        return True
    if len([d for d in disks if d.avail_tb > 50]) >= 2:
        return True
    return False
    

def suggest_move(host=None, shard=None):
    """
    Returns a tuple of (args, summary) for a move command.
    args is None if we have no command to suggest.
    """
    machines.assert_green_bank_head()    

    scraper = Scraper()
    hours = scraper.free_hours()
    if hours < 3:
        return (None, f"pausing move phase because we have an observation in {hours:.1f} hours")

    summary = []
    session = get_session(shard)
    if shard:
        print(f"session {session} is a good candidate for shard {shard}.")
    
    # Find which bls disks have the most available space.
    if host is None:
        pattern = "bls*"
    else:
        assert host in machines.BLS_MACHINES
        pattern = host

    dont_move_to = ["bls8"]
    bls = [x for x in disk_info.find_available(pattern) if x.host not in dont_move_to]

    # Only allow disks with enough space available, but randomly select within that.
    bls = [disk for disk in bls if disk.avail_tb > BLS_BUFFER_TB]

    if not enough_disk_space(bls):
        summary.append(f"space on {pattern} disks is ({', '.join(str(int(d.avail_tb)) + 'T' for d in bls)}). not enough for a move.")
        return (None, summary)
    
    random.shuffle(bls)
    summary.append(f"{pattern} disks with enough available space:")
    for info in bls[:5]:
        summary.append(str(info))
    summary.append("")
    target = bls[0]

    blc = disk_info.find_available("blc*")
    random.shuffle(blc)
    
    summary.append("searching blc* disks for movable files.")

    for (i, source) in enumerate(blc):
        assert re.fullmatch("blc[0-8]{2}", source.host), source.host
        
        root_dir = "/" + source.mount.split("/")[-1]
        unmoved = find_unmoved(session, source.host, root_dir)
        if not unmoved:
            continue

        summary.append("")
        summary.append(f"The first {i} disks scanned have no movable files. but {source.mount} does.")
        summary.append(f"we recommend moving files from {source.mount} to {target.mount}.")
        summary.append("")
        summary.append(f"there are {len(unmoved)} candidates for moving under {source.mount}, such as:")
        for d in unmoved[:5]:
            summary.append(d)

        return ([source.host, unmoved[0], target.host, target.root_dir], summary)

    summary.append(f"scanned {len(blc)} disks (such as {blc[0]}) but found no movable files.")
    summary.append(f"we are done moving session {session}.")
    priority.remove_session(session)
    return (None, summary)


def suggest(host=None, stage=None, shard=None):
    """
    Returns a tuple of (args, summary) for what to do.
    args is None iff there is nothing to do.
    """
    if stage is None:
        raise RuntimeError("no stage has been specified")

    if stage == "move":
        return suggest_move(host=host, shard=shard)

    if stage == "convert":
        assert host is None
        return suggest_convert(shard=shard)

    if stage == "transfer":
        return suggest_transfer(host=host, shard=shard)

    if stage == "turboseti":
        if host:
            raise RuntimeError("turboseti stage cannot handle host yet")
        return suggest_turboseti(shard=shard)

    if stage == "archive":
        return suggest_archive(host=host, shard=shard)

    if stage == "events":
        if host:
            raise RuntimeError("events stage cannot handle a host")
        if shard and shard != "0/1":
            raise RuntimeError(f"events stage cannot handle sharding config '{shard}' yet")
        return suggest_events()
        
    raise RuntimeError(f"unknown stage: {stage}")
        

def stopfile_exists(name):
    filename = os.path.expanduser(f"~/{name}.stop")
    if os.path.exists(filename):
        print(f"{filename} detected. stopping.", flush=True)
        return True
    return False


def do_one_step(host=None, stage=None, shard=None, run=False):
    """
    Returns whether it successfully ran.
    """
    if stopfile_exists("pipeline") or stopfile_exists(stage):
        sys.exit(0)
    args, summary = suggest(host=host, stage=stage, shard=shard)
    for line in summary:
        print(line)
    if args is None:
        print()
        print("there is nothing to be done.", flush=True)
        return False

    # TODO: have a more consistent way of allowing one-off pipeline stages
    if stage in ["move", "convert", "transfer", "archive"]:
        print()
        print(f"suggested {stage} command:")
        print(f"./{stage}.py {' '.join(args)} --run")

    if run:
        print(f"[{time.ctime()}] running {stage}({', '.join(map(repr, args))}, run=True)")
        if stage == "move":
            move(*args, run=True)
        elif stage == "convert":
            convert(*args, run=True)
        elif stage == "transfer":
            transfer(*args, run=True)
        elif stage == "archive":
            archive(*args, run=True)
        elif stage == "turboseti":
            turboseti(*args, run=True)
        elif stage == "events":
            events(*args, run=True)
        else:
            raise ValueError(f"unknown stage: {stage}")
        print()
    return True

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the data pipeline.")
    parser.add_argument("mode", nargs="?", default=None)
    parser.add_argument("--stage", default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--shard", default=None)
    args = parser.parse_args()

    if args.shard == "auto":
        if args.stage:
            raise RuntimeError("with --shard=auto, --stage should not be set, because it autodetects from screen name.")

        # Detect stage and shard from the environment
        try:
            sty = os.environ["STY"]
        except:
            raise RuntimeError("--shard=auto should only be used from within a screen")
        m = re.fullmatch(r"[0-9]+\.([a-z]+)([0-9]+)of([0-9]+)", sty)
        args.stage = m.group(1)
        args.shard = m.group(2) + "/" + m.group(3)

    print("args:", args, flush=True)

    if args.mode == "watch":
        while True:
            print(f"[{time.ctime()}] checking for jobs to do...", flush=True)
            print()
            while do_one_step(host=args.host, stage=args.stage, shard=args.shard, run=True):
                pass
            print(f"[{time.ctime()}] sleeping...", flush=True)
            time.sleep(60)
    if args.mode == "loop":
        while True:
            print("analyzing pipeline status...", flush=True)
            print()
            if not do_one_step(host=args.host, stage=args.stage, shard=args.shard, run=True):
                break
            print("step complete.", flush=True)
            time.sleep(5)
    elif args.mode == "one":
        do_one_step(host=args.host, stage=args.stage, shard=args.shard, run=True)
    elif args.mode is None:
        do_one_step(host=args.host, stage=args.stage, shard=args.shard, run=False)
    else:
        raise RuntimeError(f"bad mode: {args.mode}")

