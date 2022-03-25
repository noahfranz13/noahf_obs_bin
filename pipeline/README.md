# Data pipeline stuff

This directory contains code to run the data processing pipeline, on both Green Bank and Berkeley machines.

It starts handling data once the reduce phase produces `.fil` files. It stops handling data when it has indexed `.h5` files
in the bldw database and stored the files in Gluster - `/datag` in the Berkeley datacenter.

# Notes on Python environments

The code in this directory uses a Python3 environment named `pipeline`, defined in `environment.yml`.

Everything is supposed to be run as the `obs` user, using the `pipeline` conda environment, defined in
`environment.yml`. This environment is set up on both Green Bank and Berkeley, although it is not active
by default, so you have to explicitly activate it after logging in.

```
# Activating the environment
su obs
conda activate pipeline
cd ~/bin/pipeline
```

## Setup on new machines

When setting up this environment on new machines, one tricky detail is that the default install for `h5py` on
Ubuntu 16 is broken. You need a pip install flag, which is not supported by conda. So for Ubuntu 16, after you
set up the environment, you also need to reinstall `h5py`:

```
conda env create -f environment.yml
conda activate pipeline
pip uninstall h5py
pip install --no-binary=h5py h5py
```

According to some reports, this is no longer necessary. Your mileage may vary.

You can test an h5 install by using the `inspect_file.py` script, which you should be able to run on any h5 file to show
information about it.

# Advanced usage: Running the pipeline

Don't run the pipeline stuff unless you really know what you're doing.

All commands listed below are assumed to be run from the `pipeline` directory using the `pipeline` environment, run from the head
machines - `blh0` in either Green Bank or Berkeley. The pipeline scripts use Fabric to run jobs remotely on other machines,
so it shouldn't actually take up many resources on the head machines. Typically the scripts named "start-something"
will run `pipeline.py` several times in parallel in screens.

There are several stages to the pipeline managed by the code in this directory.

### Stages that run in Green Bank:

* `move`

Moves `.fil` files from `blc` to `bls` machines. This is because the `blc` machines are used for recording, which is time
sensitive, so it's hard to run regular jobs there.

If you have a session id, like `AGBT21A_996_29`, you can inspect the .fil files for this session left by the reduce, with:

```
./session.py AGBT21A_996_29
```

If you don't know what session to use, you can see a list of currently tracked sessions with:

```
./bldw.py sessions
```

Once you know which session you want to process, you add this session's data into the pipeline by running:

```
start_move.sh AGBT21A_996_29
```

This will create a screen prefixed with "move".

To see the current state of move jobs, run:

```
./tm
```

* `convert`

Converts `.fil` to `.h5`, and tracks the file location in `bldw`.

This stage of the pipeline automatically picks up the output of the "move" stage. To run 10 shards in parallel:

```
./start.sh convert 10
```

To see the current state of convert jobs, run:

```
./tc
```

This stage is sometimes the bottleneck of the pipeline.

* `transfer`

Rsyncs the `.h5` files from Green Bank to Berkeley.

This stage of the pipeline automatically picks up the output of the "convert" stage. To run 10 shards in parallel:

```
./start.sh transfer 10
```

This stage is sometimes the bottleneck of the pipeline.

### Stages that run in Berkeley:

* `archive`

When an rsync is completed, move the files into gluster, and track their location in `bldw`.

To run 1 shard of archive (we don't need more):

```
./start.sh archive 1
```

To see the current state of archive jobs:

```
./ta
```

* `turboseti`

Runs turboseti on gluster files. Currently stores output in `/home/obs/turboseti`, because the outputs are not too large.

To run 10 shards in parallel:

```
./start.sh turboseti 10
```

To see the current state of turboseti jobs:

```
./tt
```

* `events`

Compares data from different observations in a cadence.

To run 1 shard of events (we don't need more):

```
./start.sh events 1
```

### Running the pipeline manually

The `start` scripts will automatically run the pipeline many times in screens. If you want to run it just once, you can
run the `pipeline.py` script directly.

There are several modes that the pipeline can run in.

```
# Doesn't *do* anything, just prints out what the next step would be.
./pipeline.py

# Run one step of the pipeline, appending logs to a log file.
./pipeline.py one 2>&1 | tee -a ~/pipeline.log

# Keep running the pipeline as long as possible.
# It pauses a bit after every step, after printing "step complete".
# So you can cleanly control-C it then.
# Loop mode is useful when you are manually working through a backlog.
./pipeline.py loop 2>&1 | tee -a ~/pipeline.log

# Wake up every once in a while to check if anything needs to be done.
# Watch mode is useful to be run as a daemon when things are generally up to date.
./pipeline.py watch 2>&1 | tee -a ~/pipeline.log
```

The pipeline all runs as the `obs` user. Note that `obs` by default has a different Python environment,
so the ssh orchestration that uses Python must wrap it in a `conda activate`.

### `find_cadences.py` Usage
`find_cadences` allows the user to find the cadences that correspond to a target name and GBT receiver. The primary function is `findCadences(targets, band)`. This function takes in both a list of target names as strings and a band as a string. The Band is the GBT receiver to check for observations at and must be either L, C, S, or X. There is also a command line option that includes the options:
* `targName` -> The name of a single target you want to search for
* `targs` -> a line separated text file with a list of target names to search for
* `band` -> The GBT receiver to search for an observation at. Must be L, C, S, or X.

Note that either a `targName` or `targs` must be provided and the band option is mandatory. Example usage using the targName option is
```
python3 find_cadence.py --targName HIP12345 --band L
```

Example usage with an input file with a list of target names is
```
python3 find_cadence.py --targs list_of_target_names.txt --band S
```
