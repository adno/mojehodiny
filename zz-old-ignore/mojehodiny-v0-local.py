#!/usr/bin/env python

import sys
import re
import datetime
from itertools import chain, cycle, takewhile, accumulate, repeat

YMD_FMT     = '%Y-%m-%d'
DATE_FMT    = '%d. %m. %Y'
WEEK_DAYS   = 7
ONE_DAY     = datetime.timedelta(days=1)
def ymd2date(s):
    return datetime.datetime.strptime(s, YMD_FMT)

weekdays            = [0,2]    # po, st
time_strs           = [('17:00','17:55'),('17:00','17:55')]
start_date           = ymd2date('2020-09-07')
part_date           = ymd2date('2021-01-01')    # rozděl na 20/21
last_date           = ymd2date('2021-06-26')    # sobota

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
    with open('except_dates.tsv') as fexc:
        for line in fexc:
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


# def write_icalendar(f, dates, weekday2event_time_hms, cal_name, event_summary):
#     f.write((
#         '''BEGIN:VCALENDAR
#         PRODID:-//mojehodiny.nohejl.name//NONSGML mojehodiny 1.0//CS
#         VERSION:2.0
#         X-WR-CALNAME:%s
#         X-WR-TIMEZONE:Europe/Prague
#         X-WR-CALDESC:
#         BEGIN:VTIMEZONE
#         TZID:Europe/Prague
#         BEGIN:DAYLIGHT
#         TZOFFSETFROM:+0100
#         RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
#         DTSTART:19810329T020000
#         TZNAME:GMT+02:00
#         TZOFFSETTO:+0200
#         END:DAYLIGHT
#         BEGIN:STANDARD
#         TZOFFSETFROM:+0200
#         RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
#         DTSTART:19961027T030000
#         TZNAME:GMT+01:00
#         TZOFFSETTO:+0100
#         END:STANDARD
#         END:VTIMEZONE
#         '''%ical_make_text_safe(cal_name)).replace('\n','\r\n')
#         )
#     for date in dates:
#         event_time_hms = weekday2event_time_hms[date.weekday()]
#         f.write("BEGIN:VEVENT\r\n"
#                     "SEQUENCE:0\r\n"
#                     "STATUS:CONFIRMED\r\n"
#                     )
#         f.write("TRANSP:TRANSPARENT\r\n")
#         f.write("SUMMARY:"+ical_make_text_safe(event_summary)+'\r\n')
#         ymd = date.strftime('%Y%m%d')
#         f.write('DTSTART:%sT%s\r\n'%(ymd, event_time_hms[0]))
#         f.write('DTEND:%sT%s\r\n'%(ymd, event_time_hms[1]))
#         f.write('END:VEVENT\r\n')
#     f.write('END:VCALENDAR\r\n')
#
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
print('Except days:')
for dt, desc in exc_desc:
    print('* %s\t%s'%(dt.strftime(DATE_FMT), desc))


