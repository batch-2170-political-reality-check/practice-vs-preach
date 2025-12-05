from practicepreach.constants import BUNDESTAG_WAHLPERIODE

def convert_to_wp_start(date, mapping):
    for wp, (start, end) in mapping.items():
        if start <= date <= end:
            return start
    return None
