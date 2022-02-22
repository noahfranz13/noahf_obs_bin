#!/usr/bin/env python
"""
Tools for plotting. This is intended as a replacement for turboseti's plot_event_pipeline that does not have a
dependency on a particular on-disk file layout.
"""
from h5 import h5py

import io
import math
import os
import pandas

# Plotting packages import
import matplotlib
matplotlib.use('agg')
from matplotlib import pyplot as plt

# Math/Science package imports
import numpy as np
from astropy.time import Time


FONT = {
    "family": "DejaVu Sans",
    "size": 16
}
RED = "#CC0000"


def overlay_line(line_freq, f_start, f_stop, line_drift_rate, t_duration, offset=0, alpha=1, color=RED):
    """
    Creates a dashed red line at the specified frequency and drift rate. It can be offset by
    some amount. Offset is either an amount of Hz or "auto".
    """
    # determines automatic offset and plots offset lines
    if offset == 'auto':
        offset = ((f_start - f_stop) / 10)
        plt.plot((line_freq - offset, line_freq),
                 (10, 10),
                 "o-",
                 c=color,
                 lw=2,
                 alpha=alpha)

    # plots drift overlay line, with offset if desired
    plt.plot((line_freq + offset, line_freq + line_drift_rate/1e6 * t_duration + offset),
             (0, t_duration),
             c=color,
             ls='dashed', lw=2,
             alpha=alpha)


def grab_data(h5data, f_start=None, f_stop=None):
    assert f_start is not None
    assert f_stop is not None
    fch1 = h5data.attrs["fch1"]
    foff = h5data.attrs["foff"]

    # Normalize start and stop so that they are in index space (0 = first channel, 1 = second channel, etc)
    start = round((f_start - fch1) / foff)
    stop = round((f_stop - fch1) / foff)

    first_index = max(0, (min(start, stop)))
    last_index = min(h5data.shape[-1] - 1, max(start, stop))

    dataslice = h5data[:, 0, first_index:last_index+1]
    first_freq = first_index * foff + fch1
    last_freq = last_index * foff + fch1

    return first_freq, last_freq, dataslice

    
def plot_freq_range(h5data, f_start, f_stop):
    """
    Plots a frequency range. f_start and f_stop are approximately the start and end frequencies, but we round to the nearest bucket.
    """
    matplotlib.rc("font", **FONT)
    
    first_freq, last_freq, plot_data = grab_data(h5data, f_start=f_start, f_stop=f_stop)

    # determine extent of the plotting panel for imshow
    extent = (first_freq, last_freq, h5data.attrs["tsamp"] * h5data.shape[0], 0.0)

    # plot and scale intensity (log vs. linear)
    plot_data = 10.0 * np.log10(plot_data)

    # get normalization parameters
    vmin = plot_data.min()
    vmax = plot_data.max()
    normalized_plot_data = (plot_data - vmin) / (vmax - vmin)

    this_plot = plt.imshow(normalized_plot_data,
                           aspect="auto",
                           rasterized=True,
                           interpolation="nearest",
                           extent=extent,
                           cmap="viridis")

    # add plot labels
    plt.xlabel("Frequency [Hz]", fontdict=FONT)
    plt.ylabel("Time [s]", fontdict=FONT)

    # add source name
    ax = plt.gca()
    plt.text(0.03, 0.8, h5data.attrs["source_name"], transform=ax.transAxes, bbox=dict(facecolor='white'))

    return this_plot


def plot_event_helper(h5_filenames, source_name, f_start, f_stop, drift_rate, event_freq):
    """
    Plots a single event as it tracks through several h5 files.

    Parameters
    ----------
    h5_filenames : str
        List of h5 files in the cadence.
    source_name : str
        Main target name.
    f_start : float
        Start frequency, in MHz.
    f_stop : float
        Stop frequency, in MHz.
    drift_rate : float
        Drift rate in Hz/s.
    event_freq : float
        Frequency of one point on the event, in MHz.
    """

    matplotlib.rc("font", **FONT)

    # set up the sub-plots
    n_plots = len(h5_filenames)
    fig = plt.subplots(n_plots, sharex=True, sharey=True, figsize=(10, 2*n_plots))

    # Get the start time from the first h5 file
    first_h5file = h5py.File(h5_filenames[0], "r")
    t0 = first_h5file["data"].attrs["tstart"]
    
    subplots = []

    # Fill in each subplot for the full plot
    for i, filename in enumerate(h5_filenames):
        subplot = plt.subplot(n_plots, 1, i + 1)
        subplots.append(subplot)

        h5file = h5py.File(filename, "r")
        h5data = h5file["data"]
        
        this_plot = plot_freq_range(h5data, f_start, f_stop)

        # Calculate parameters for estimated drift line
        t_elapsed = Time(h5data.attrs["tstart"], format="mjd").unix - Time(t0, format="mjd").unix
        t_duration = (h5data.shape[0] - 1) * h5data.attrs["tsamp"]
        f_event = event_freq + drift_rate / 1e6 * t_elapsed

        # Plot a line to show where the candidate event is
        f_span = abs(f_start - f_stop)
        overlay_line(f_event, f_start, f_stop, drift_rate, t_duration, offset=0.1*f_span)
        overlay_line(f_event, f_start, f_stop, drift_rate, t_duration, offset=-0.1*f_span)

        # Title the full plot
        if i == 0:
            plot_title = "%s \n $\\dot{\\nu}$ = %2.3f Hz/s, MJD:%5.5f" % (source_name, drift_rate, t0)
            plt.title(plot_title)
        # Format full plot
        if i < len(h5_filenames) - 1:
            plt.xticks(np.linspace(f_start, f_stop, num=4), ["", "", "", ""])


    # Axis labelling
    factor = 1e6
    units = "Hz"

    mid_f = (f_start + f_stop) / 2
    xloc = np.linspace(f_start, f_stop, 5)
    xticks = [round(loc_freq) for loc_freq in (xloc - mid_f) * factor]
    if np.max(xticks) > 1000:
        xticks = [xt/1000 for xt in xticks]
        units = "kHz"
    plt.xticks(xloc, xticks)
    plt.xlabel("Relative Frequency [%s] from %f MHz" % (units, mid_f), fontdict=FONT)

    # Add colorbar
    # cax = fig[0].add_axes([0.94, 0.11, 0.03, 0.77])
    # fig[0].colorbar(this_plot, cax=cax, label="Normalized Power (Arbitrary Units)")

    plt.subplots_adjust(hspace=0, wspace=0)


def plot_event(event_dir, index):
    """
    Plots a single event. The index describes which entry in the found-events csv to use to define the event.
    """
    events = read_csv(event_dir)
    h5_filenames = get_h5_filenames(event_dir)

    # calculate the length of the total cadence from the headers
    first_h5_data = h5py.File(h5_filenames[0], "r")["data"]
    last_h5_data = h5py.File(h5_filenames[-1], "r")["data"]
    tfirst = first_h5_data.attrs["tstart"]
    tlast = last_h5_data.attrs["tstart"]
    t_elapsed = Time(tlast, format="mjd").unix - Time(tfirst, format="mjd").unix + last_h5_data.shape[0] * last_h5_data.attrs["tsamp"]

    event = events.iloc[index]
    source_name = event["Source"]
    event_freq = event["Freq"]
    event_time = event["MJD"]
    drift_rate = event["DriftRate"]

    # We are given one point of the event. For graphing, we want to find the point that matches the starting time of the cadence.
    diff_seconds = Time(event_time, format="mjd").unix - Time(tfirst, format="mjd").unix
    event_start_freq = event_freq - drift_rate * diff_seconds / 1e6

    # calculate the width of the plot
    bandwidth = 2.4 * abs(drift_rate) / 1e6 * t_elapsed
    bandwidth = np.max((bandwidth, 500. / 1e6))

    # Get start and stop frequencies based on midpoint and bandwidth
    # Note: this doesn't actually guarantee the full drift is visible
    f_start, f_stop = np.sort((event_freq - (bandwidth / 2),  event_freq + (bandwidth / 2)))

    plot_event_helper(h5_filenames,
                      source_name,
                      f_start,
                      f_stop,
                      drift_rate,
                      event_start_freq)    

    
def plot_event_png(event_dir, index):
    """
    Plots a single event and returns the plot as a .png encoded into a BytesIO.
    """
    plot_event(event_dir, index)
    buf = io.BytesIO()
    plt.savefig(buf, dpi=96, format="png")
    return buf
    

def plot_cadence(event_dir):
    """
    Plot all events for a particular cadence of files,  given the csv output of find_event_pipeline and a list of the h5 filenames.
    This is intended to be called from a jupyter notebook.
    """
    events = read_csv(event_dir)
    for i in range(len(events)):
        plot_event(event_dir, i)

        
def get_h5_filenames(event_dir):
    """
    Reconstruct a list of h5 filenames for an event by reading the dat_files.lst left by the find_events pipeline.
    Note that these are temporary softlink names, not useful semi-permanent gluster names.
    TODO: make this retrieve data from bldw instead
    """
    old_dat_list = f"{event_dir}/dat_files.lst"
    slugs = [dat.strip().split("/")[-1].replace(".dat", "") for dat in open(old_dat_list).readlines()]
    h5_filenames = [f"{event_dir}/{slug}.h5" for slug in slugs]
    return h5_filenames


def read_csv(event_dir):
    csv_filename = f"{event_dir}/found_event_table.csv"    
    return pandas.read_csv(csv_filename, comment="#")


