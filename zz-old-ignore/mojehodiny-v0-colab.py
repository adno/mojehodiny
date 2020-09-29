#!/usr/bin/env python

import sys
import re
import datetime
from itertools import chain, cycle, takewhile, accumulate, repeat, compress

začátek_školního_roku = '2020-09-07' #@param {type:"date"}
předěl_roku = '2021-01-01' #@param {type:"date"}
konec_školního_roku = '2021-06-26' #@param {type:"date"}
hodina_v_po = True #@param {type:"boolean"}
hodina_v_út = False #@param {type:"boolean"}
hodina_v_st = True #@param {type:"boolean"}
hodina_v_čt = False #@param {type:"boolean"}
hodina_v_pá = False #@param {type:"boolean"}
vynechávat = 'svátky a prázdniny (Praha 2)' #@param ["jen svátky", "svátky a prázdniny (Praha 2)"]

YMD_FMT     = '%Y-%m-%d'
DATE_FMT    = '%d. %m. %Y'
WEEK_DAYS   = 7
ONE_DAY     = datetime.timedelta(days=1)
WD_ABBRS    = ('po', 'út', 'st', 'čt', 'pá', 'so', 'ne')
def ymd2date(s):
    return datetime.datetime.strptime(s, YMD_FMT)


start_date          = ymd2date('2020-09-07')
part_date           = ymd2date('2021-01-01')    # rozděl na 20/21
last_date           = ymd2date('2021-06-26')    # sobota

EXC_DATES_STATE = '''2020-01-01	Nový rok
2020-04-10	Velký pátek
2020-04-13	Velikonoční pondělí
2020-05-01	Svátek práce
2020-05-08	Den vítězství
2020-07-05	Den slovanských věrozvěstů Cyrila a Metoděje
2020-07-06	Den upálení mistra Jana Husa
2020-09-28	Den české státnosti
2020-10-28	Den vzniku samostatného československého státu
2020-11-17	Den boje za svobodu a demokracii
2020-12-24	Štědrý den
2020-12-25	1. svátek vánoční
2020-12-26	2. svátek vánoční
2021-01-01	Nový rok
2021-04-02	Velký pátek
2021-04-05	Velikonoční pondělí
2021-05-01	Svátek práce
2021-05-08	Den vítězství
2021-07-05	Den slovanských věrozvěstů Cyrila a Metoděje
2021-07-06	Den upálení mistra Jana Husa
2021-09-28	Den české státnosti
2021-10-28	Den vzniku samostatného československého státu
2021-11-17	Den boje za svobodu a demokracii
2021-12-24	Štědrý den
2021-12-25	1. svátek vánoční
2021-12-26	2. svátek vánoční
'''
EXC_DATES_SCHOOL = '''2020-10-29~2020-10-30	podzimní prázdniny
2020-12-23~2021-01-03	vánoční prázdniny
2021-01-29	pololetní prázdniny
2021-02-22~2021-02-28	jarní prázdniny Praha 1–5
2021-04-01	velikonoční prázdniny
'''

weekdays_mo_fri     = [hodina_v_po, hodina_v_út, hodina_v_st, hodina_v_čt, hodina_v_pá]
weekdays            = list(compress(range(0, 5), weekdays_mo_fri))
start_date          = ymd2date(začátek_školního_roku)
part_date           = ymd2date(předěl_roku)
last_date           = ymd2date(konec_školního_roku)
exc_dates           = EXC_DATES_STATE if vynechávat=='jen svátky' else EXC_DATES_SCHOOL + EXC_DATES_STATE

def weekdays_between_dates(wds, start, last):
    start_wd            = start.weekday()
    start_delta_days    = sorted([(wd-start_wd)%WEEK_DAYS for wd in wds])
    shift_days          = start_delta_days[0]
    base                = start+datetime.timedelta(shift_days)  # first date from start on one of wds
    base_wd             = base.weekday()
    base_delta_days     = [n-shift_days for n in start_delta_days[1:]]
    base_delta_days.append(WEEK_DAYS)                           # cycle: same week day as base
    def acc_deltas():
        prev = 0
        for d in base_delta_days:
            yield datetime.timedelta(days = d-prev)
            prev = d
    return list(takewhile(
        lambda dt: dt<=last,
        accumulate(chain(
            (base,),
            cycle(acc_deltas())
            ))
        ))

def dates_except(dts, exc_dts2desc):
    dates_exc    = [dt                      for dt in dts if dt not in exc_dts2desc]
    exc_desc     = [(dt, exc_dts2desc[dt])  for dt in dts if dt in exc_dts2desc]
    return (dates_exc, exc_desc)


def ical_make_text_safe(s):
    return re.sub(r'[\x00-\x19";:\\,]','-',s)

def get_except_dates2desc():
    ex_dict = {}
    for line in exc_dates.split('\n'):
        line = line.rstrip()
        if line:
            fields = line.split('\t')
            ds = fields[0]
            if '~' not in ds:
                dts = (ymd2date(ds),)
            else:
                d_from,__,d_to = ds.partition('~')
                dt_from = ymd2date(d_from)
                dt_to   = ymd2date(d_to)
                dts = accumulate(chain((dt_from,), repeat(ONE_DAY, (dt_to-dt_from).days)))
            for dt in dts:
                ex_dict[dt] = fields[1] # TODO possibly overwrite a previous exception
    return ex_dict



ex_dts2desc     = get_except_dates2desc()
wd_dts          = weekdays_between_dates(weekdays, start_date, last_date)
dts, exc_desc   = dates_except(wd_dts, ex_dts2desc)
dts1 = list(takewhile(lambda dt: dt<part_date, dts))

n   = len(dts)
n1  = len(dts1)

print('Classes in a school year:    %i'%n)
print('Classes before %s: %i'%(part_date.strftime(DATE_FMT), n1))
print('Classes from %s:   %i'%(part_date.strftime(DATE_FMT), n-n1))
print()
print('NO class days:')
for dt, desc in exc_desc:
    print('* %s %s %s'%(WD_ABBRS[dt.weekday()], dt.strftime(DATE_FMT), desc))
print()
print('Class days:')
for i, dt in enumerate(dts):
    print('%i. %s %s'%(i+1, WD_ABBRS[dt.weekday()], dt.strftime(DATE_FMT)))


