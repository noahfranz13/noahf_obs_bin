import sys, os
import bldw
import pandas as pd
import numpy as np

def findCadences(targets):

    c = bldw.Connection()

    targetObjs = [c.fetch_targets_by_name(tt)[0] for tt in targets]

    cadences = {}
    for tt in targetObjs:

        observations = c.fetch_observations_by_target(tt.id)
        for obs in observations:

            tags = c.fetch_tags_for_observation_id(obs.id)
            for tag in tags:
                if tag.name.startswith('AGBT'):
                    cads = c.fetch_cadences_for_session(tag.name)
                    for cad in cads.good_cadences_for_session(c, tag.name):
                        print(cad)
                    '''for cad in cads:
                        cad.populate_metas(c)
                        repFreqs = cad.representative_freqs()
                        for f in repFreqs:
                            if f > 1000 and f < 2000:
                                cadences[tt.name] = cads'''

    return cadences


def main():

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--targs', help='File with list of string target names to search for cadences for', default=None)
    args = parser.parse_args()

    targs = np.loadtxt(args.targs, dtype=str, delimiter='\n')

    cadences = findCadences(targs)
    print(cadences)
    #pd.DataFrame(cadences).to_csv(os.path.join(os.getcwd(), 'cadences.csv'))


if __name__ == '__main__':
    sys.exit(main())
