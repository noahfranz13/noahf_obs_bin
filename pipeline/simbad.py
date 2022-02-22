import numpy

from astroquery.simbad import Simbad

RA_KEY = 'RA_d_A_ICRS_J2000'
DECL_KEY = 'DEC_d_D_ICRS_J2000'
PM_RA_KEY = 'PMRA'
PM_DECL_KEY = 'PMDEC'

simbad = Simbad()
simbad.add_votable_fields('pm', 'ra(d;A;ICRS;J2000)', 'dec(d;D;ICRS;J2000)')
simbad.remove_votable_fields('coordinates', 'main_id')

def query_object(object_name):
    """
    Wrapper around the simbad client function of the same name.
    """
    result = None
    try:
        result = simbad.query_object(object_name)
    except:
        # The simbad client is not very reliable and sometimes this will resolve an error.
        simbad.add_votable_fields('main_id')
        try:
            result = simbad.query_object(object_name)
        except:
            pass
        simbad.remove_votable_fields('main_id')
    return result
