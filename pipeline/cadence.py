#!/usr/bin/env python
"""
Tools to work with cadences.
"""
class Cadence(object):
    """
    A "cadence" is a sequence of "on" and "off" observations. We look at a target several times, which is the "on" observations,
    and in between these times we look at other things. These are the "off" observations. A signal which is in both "on" and "off"
    observations is probably local interference.

    For now, cadences can be either "ABACAD" or "BACADA", where A is the "on" observations and the "off" observations are three
    different targets. This is what Green Bank has been using from 2016-2021 for example.

    A "scan" here can either be a bltargets Scan, or a bldw Observation.
    TODO: move everything to just use bldw

    The id of a cadence is the scan id of the first scan in it.
    """
    def __init__(self, scans):
        assert scans[0].is_cadence(scans)
        self.id = scans[0].id
        self.scans = scans

        # A list of file metadata for each scan. Parallel to self.scans
        self.metas = None

    def is_abacad(self):
        return self.scans[0].target_id == self.scans[2].target_id == self.scans[4].target_id

    def is_bacada(self):
        return self.scans[1].target_id == self.scans[3].target_id == self.scans[5].target_id

    def is_on(self, i):
        """
        Returns True, False, or None if we can't tell.
        """
        if self.is_abacad():
            return i in (0, 2, 4)
        if self.is_bacada():
            return i in (1, 3, 5)
        return None
    
    def show_scan(self, i):
        on = self.is_on(i)
        if on is None:
            prefix = "???"
        elif on:
            prefix = " on"
        else:
            prefix = "off"
        print(f"{prefix}: {self.scans[i]}")        


    def show(self):
        print(f"Cadence {self.id}:")
        for i in range(len(self.scans)):
            self.show_scan(i)
        if self.metas:
            freqs = self.representative_freqs()
            if freqs:
                print("representative frequencies:", ", ".join(map(str, freqs)))
            else:
                print("no representative frequencies")

                
    def populate_metas(self, dw):
        """
        Populates metas given a bldw connection.
        """
        assert self.metas is None, "only populate_metas once"
        ids = [scan.id for scan in self.scans]
        metas = dw.fetch_metadata_for_observation_ids(ids)
        self.metas = []
        for scan in self.scans:
            metas_for_scan = []
            for m in metas:
                if m.observation_id == scan.id:
                    metas_for_scan.append(m)
            self.metas.append(metas_for_scan)
            
    @classmethod
    def find_cadences(cls, scan_list):
        """
        Returns a list of cadences given a list of scans.
        It is assumed that these scans are from the same session.
        """
        answer = []
        sorted_list = sorted(scan_list, key=lambda s: s.timestamp())
        for i in range(len(sorted_list)):
            candidates = sorted_list[i:i+6]
            if candidates[0].is_cadence(candidates):
                answer.append(Cadence(candidates))
        return answer

    def representative_freqs(self):
        """
        Return a list of representative frequencies for all files in the cadence.
        Sort from highest to lowest.
        """
        assert self.metas
        freq_sets = [set(m.representative_freq() for m in meta_list) for meta_list in self.metas]
        intersection = freq_sets[0].intersection(*freq_sets[1:])
        return list(reversed(sorted(intersection)))

    def metas_for_event_stage(self, freq):
        """
        Returns a list of one file per cadence that have .dat files.
        Returns None if we don't have them.
        """
        for metas in self.align_metas(freq):
            if all(m.dat_exists() for m in metas):
                return metas
        return None

    def align_metas(self, freq):
        """
        Returns a list of tuples of six metadata objects for cadence analysis.
        If we aren't confident in a cadence, skip it.
        """
        # First, gather usable files in six groups, one for each observation.
        groups = []
        for metas in self.metas:
            matches = [m for m in metas if m.can_be_aligned() and m.has_freq(freq)]
            matches.sort(key=lambda m: m.location)
            groups.append(matches)

        answer = []
        while True:
            if not all(groups):
                # One of the observations has nothing, we're done
                return answer
            
            # Group up by last dir, greedily. Figure out what the most common last dir is
            counts = {}
            for group in groups:
                last_dirs = set(m.last_dir() for m in group)
                for d in last_dirs:
                    counts[d] = counts.get(d, 0) + 1
            items = [(-count, last_dir) for (last_dir, count) in counts.items()]
            items.sort()
            _, last_dir = items[0]

            # Do the grouping. If we don't have an item for a last dir, just pick the first one we have.
            choices = []
            for group in groups:
                index = None
                for i, meta in enumerate(group):
                    if meta.last_dir() == last_dir:
                        index = i
                        break
                if index is None:
                    index = 0
                choices.append(group.pop(index))
            answer.append(tuple(choices))
            

            
        

    
# TODO: better fix for these busted cadences
BAD_CADENCE_RANGES = [
    (370283, 370331),
    (370343, 370379),
    195002,
    164910,
    164940,
    49327,
    ]

def cadence_is_bad(cadence):
    for r in BAD_CADENCE_RANGES:
        if type(r) == int:
            lo, hi = r, r
        else:
            lo, hi = r
        if lo <= cadence.id <= hi:
            return True
    return False

def good_cadences_for_session(dw, session):
    """
    Iterates through Cadence objects.
    Restricts to ABACAD cadences, skips some broken ones, and populates meta data.
    """
    cadences = dw.fetch_cadences_for_session(session)
    for cadence in cadences:
        if cadence_is_bad(cadence):
            continue
        if not cadence.is_abacad():
            continue
        cadence.populate_metas(dw)
        yield cadence
