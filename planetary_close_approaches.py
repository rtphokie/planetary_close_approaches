'''
Created on Jun 18, 2018

@author: trice
'''
import unittest
import pandas as pd
from skyfield.api import load
from scipy.signal import argrelextrema
import numpy as np
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
import math

millnames = ['',' Thousand',' Million',' Billion',' Trillion']

def millify(n):
    ''' convert to convenient units for easier communication '''
    n = float(n)
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    return '{:.1f}{}'.format(n / 10**(3 * millidx), millnames[millidx])


def distance_extrema(t, body, observer='earth'):
    ''' given a body and a time series and the observers body (defaults to Earth),
        returns a series of SkyField distance objects, 
        and the indexes of local minimums and maximums 
    '''
    astrometric = observer.at(t).observe(body)
    _, _, distance = astrometric.radec()
    return distance, argrelextrema(distance.km, np.less)[0], argrelextrema(distance.km, np.greater)[0]


def build_dataframe(years, body, obs, year, planets, df):
    print body, years
    ts = load.timescale()
    if year is None:
        year = int(ts.now()._utc_year())  # default this year
    try:
        _ = planets[body]
    except:
        body += ' BARYCENTER'
    
    # find obs-body distance extrema with day precision, within +/- years of the current year
    t = ts.utc(year - years, 1, range(1, 365 * years * 2))
    _, min_distance_day, max_distance_day = distance_extrema(t, planets[body], observer=planets[obs])
    for s in min_distance_day, max_distance_day: # loop through mins and maxes
        for i in s: # find extrema with minute precision
            day_precision = t[i].utc
            t2 = ts.utc(day_precision[0], day_precision[1], day_precision[2], 0, range(60 * -24, 60 * 24))
            distance_minute, distance_minimums_index, distance_maximums_index = distance_extrema(t2, planets[body], 
                observer=planets[obs])
            # are we calculating min or max extremes?
            # make sure a single high and single low were found at minute precision
            if s is min_distance_day:
                extrema = 'closest'
                assert len(distance_minimums_index) == 1
                s2 = distance_minimums_index[0] # there should be only
            elif s is max_distance_day:
                assert len(distance_maximums_index) == 1
                extrema = 'furthest'
                s2 = distance_maximums_index[0]
            else:
                raise NotImplementedError, ('unexpected extrema series')
            df = df.append({'date':t2[s2].utc_iso(), 
                    'au':distance_minute.au[s2], 
                    'km':distance_minute.km[s2], 
                    'observer':obs, 
                    'target':body.replace(' BARYCENTER', '').lower(), 
                    'extrema':extrema}, 
                ignore_index=True)
    
    df['mi'] = df.km * 0.621371
    df['mi eng'] = df.apply(lambda row:millify(row['mi']), axis=1)
    return df


def main(years=100, bodies=['MARS BARYCENTER', 'Sun'], obs='earth', year=None):
    planets = load('de431t.bsp')  # most complete, latest JPL emphemeris

    df = pd.DataFrame()

    for body in bodies:
        df = build_dataframe(years, body, obs, year, planets, df)
    filename = '%s_distance_extrema.xlsx' % obs.lower()
    writer = pd.ExcelWriter(filename, index=False)
    for body in df['target'].unique():
        df_this_planet = df[df['target'] == body]
        columns_implied_by_tab = ['extrema','observer','target']
        df_this_planet[df_this_planet['extrema'] == 'closest'].sort_values(by=['au'], ascending=True).drop(columns_implied_by_tab, axis=1).to_excel(writer, '%s closest' % body, index=False)
        df_this_planet[df_this_planet['extrema'] == 'furthest'].sort_values(by=['au'], ascending=False).drop(columns_implied_by_tab, axis=1).to_excel(writer, '%s furthest' % body, index=False)
    writer.save()    
    return df, filename


class Test(unittest.TestCase):
    def test_Mars_2018_small(self):
        df, _ = main(years=1, year=2018, bodies=['Mars'])
        self.assertEqual(df.shape[0], 2)
        self.assertEqual(df['date'][0], '2018-07-31T07:45:00Z')
        self.assertEqual(df['au'][0], 0.38496648860253246)
        self.assertEqual(df['date'][1], '2017-08-05T10:39:00Z')
        self.assertEqual(df['au'][1], 2.6581612780087269)

    def test_Mars_1500_medium(self):
        df, _ = main(years=25, year=1500, bodies=['Mars'])
        self.assertEqual(df.shape[0], 47)
        self.assertEqual(df['date'][0], '1476-03-08T00:16:00Z')
        self.assertEqual(df['date'][1], '1478-04-18T13:38:00Z')

    def test_Mars_1500_large(self):
        df, _ = main(years=250, year=2050, bodies=['Mars'])
        self.assertEqual(df.shape[0], 468)
        self.assertEqual(df['date'][0], '1800-10-31T20:16:00Z')
        self.assertEqual(df['date'][1], '1802-12-19T14:36:00Z')
        

    def test_Jupiter_2018_small(self):
        df, _ = main(years=1, year=2018, bodies=['Jupiter BARYCENTER', 'Mars'], obs='earth')
        self.assertEqual(df.shape[0], 6)
        self.assertEqual(set(df['target'].unique()), set(['jupiter', 'mars']))
        self.assertEqual(df['date'][0], '2017-04-08T21:23:00Z')
        self.assertEqual(df['au'][0], 4.4549007392287674)
        self.assertEqual(df['date'][1], '2018-05-10T11:53:00Z')
        self.assertEqual(df['au'][1], 4.3998288623090307)


if __name__ == "__main__":
    main(bodies=['Mars', 'Sun'])