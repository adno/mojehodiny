#!/usr/bin/env python

import sys
import re
from itertools import chain, cycle, takewhile, accumulate, repeat, compress
from string import Template
from datetime import timedelta, datetime as dt


# Google Colab input:

začátek_školního_roku = '2020-09-07' #@param {type:"date"}
předěl_roku = '2021-01-01' #@param {type:"date"}
konec_školního_roku = '2021-06-26' #@param {type:"date"}
hodina_v_po = True #@param {type:"boolean"}
hodina_v_út = False #@param {type:"boolean"}
hodina_v_st = True #@param {type:"boolean"}
hodina_v_čt = False #@param {type:"boolean"}
hodina_v_pá = False #@param {type:"boolean"}
vynechávat = 'svátky a prázdniny (Praha 2)' #@param ["jen svátky", "svátky a prázdniny (Praha 2)"]

YMD_FMT         = '%Y-%m-%d'
MD_FMT          = '%m-%d'
OUTPUT_FMT      = '%d. %m. %Y'
DMY_FMT         = '%d.%m.%Y'
DM_FMT          = '%d.%m.'
WEEK_DAYS       = 7
ONE_DAY         = timedelta(days=1)
WD_ABBRS        = ('po', 'út', 'st', 'čt', 'pá', 'so', 'ne')
def ymd2date(s):
    return dt.strptime(s, YMD_FMT)
def md2date(s, year):
    date = dt.strptime(s, MD_FMT)
    return dt(year=year, month=date.month, day=date.day)
def dmy2date(s):
    return dt.strptime(s, DMY_FMT)
def dm2date(s, year):
    date = dt.strptime(s, DM_FMT)
    return dt(year=year, month=date.month, day=date.day)

def user_ymd2date(s, year=None):
    try:
        return ymd2date(s)
    except:
        if year:
            try:
                return md2date(s, year)
            except:
                raise ValueError(
                    'Neplatné datum ve formátu YYYY-MM-DD nebo MM-DD: „%s“'%s
                    ) from None
        raise ValueError(
            'Neplatné datum ve formátu YYYY-MM-DD: „%s“'%s) from None

def user_dmy2date(s, year=None):
    # delete any number of SPACE/NBSP after a PERIOD:
    ns = re.sub(r'\.[  ]*', '.', s)
    try:
        return dmy2date(ns)
    except:
        if year:
            try:
                return dm2date(s, year)
            except:
                raise ValueError(
                    'Neplatné datum ve formátu DD.MM.YYYY nebo DD.MM.: „%s“'%s
                    ) from None
        raise ValueError(
            'Neplatné datum ve formátu DD.MM.YYYY: „%s“'%s) from None

def dm_dmy_range2dates(ds):
    d_from, __, d_to = ds.partition('–')
    dm_from   = dt.strptime(d_from, '%d. %m.')
    date_to   = dt.strptime(d_to, '%d. %m. %Y')
    date_from = dt(day=dm_from.day , month=dm_from.month, year=date_to.year)
    return list(accumulate(
        chain((date_from,), repeat(ONE_DAY, (date_to-date_from).days))
        ))

def date_range2dates(dates):
    if len(dates)==1:
        return list(dates)
    assert len(dates)==2
    date_from, date_to = dates
    return list(accumulate(
        chain((date_from,), repeat(ONE_DAY, (date_to-date_from).days))
        ))


def parse_date_desc(date_desc_str):
    """
    Parse a user input of dates/date ranges and their descriptions.
    """
    for line in date_desc_str.splitlines():
        line=line.strip()
        if not line:
            continue
        sep = '\t'
        if ';' in line:
            if '\t' in line:
                raise ValueError('Řádek „%s“ obsahuje středník i tabulátor. '
                    'Používejte pro oddělení data a popisu jen jeden z nich.'%
                    line)
            sep = ';'
        date_part, sep, desc = line.partition(sep)
        if sep and sep in desc:
            raise ValueError(
                'Řádek „%s“ obsahuje dva %s. Používejte jen jeden znak pro '
                'oddělení data a popisu.'%
                (line, 'středníky' if (sep==';') else 'tabulátory'))

        desc        = desc.strip()
        d_from      = None
        d_to        = None
        date        = None  # single date (datetime.datetime)
        dt_from     = None  # date range (from)
        dt_to       = None  # date range (to)

        if not desc:
            desc    = 'volno %s'%date_part

        for sep in '~–':    # tilde, en-dash (not hyphen)
            if sep in date_part:
                d_from, __, d_to = date_part.partition(sep)
                if sep in d_to:
                    raise ValueError(
                        'Rozmezí dat „%s“ obsahuje dva znaky ‚%s‘. Použijte '
                        'jen jeden pro oddělení počátečního a koncového data.'%
                        (date_part, sep))
                break
        else:
            if date_part.count('-') == 1:   # hyphen (not en-dash)
                d_from, __, d_to = date_part.partition('-')
            # else consider a single date, e.g. 2020-10-20
            # (or 20.10.2020 – also valid, or 2020-10-20-10-21 – invalid)

        if d_from:
            d_from = d_from.strip()
            d_to = d_to.strip()
            if '-' in d_from:
                dt_from = user_ymd2date(d_from)
                dt_to   = user_ymd2date(d_to, year=dt_from.year)
            else:
                dt_to   = user_dmy2date(d_to)
                dt_from = user_dmy2date(d_from, year=dt_to.year)
            if dt_from > dt_to:
                raise ValueError(
                    'První datum v rozmezí následuje až po druhém: „%s“'%
                    date_part)
        else:
            is_ymd = ('-' in date_part)
            try:
                date = (user_ymd2date(date_part) if is_ymd
                    else user_dmy2date(date_part))
            except:
                raise ValueError(
                    'Neplatné datum „%s“, povolené formáty jsou DD.MM.YYYY '
                    'nebo YYYY-MM-DD.'%date_part) from None

        dates = (date,) if date else (dt_from, dt_to)
        yield (dates, desc)

# Generate spring holiday options for the Dash app:
#
# SPRING_HOLIDAYS_1='''1. 2. - 7. 2. 2021
#
# Česká   Lípa, Jablonec nad Nisou, Liberec, Semily, Havlíčkův Brod, Jihlava,   Pelhřimov, Třebíč, Žďár nad Sázavou, Kladno, Kolín, Kutná Hora, Písek,   Náchod, Bruntál
#
# 8. 2. - 14. 2. 2021
#
# Mladá   Boleslav, Příbram, Tábor, Prachatice, Strakonice, Ústí nad Labem, Chomutov,   Most, Jičín, Rychnov nad Kněžnou, Olomouc, Šumperk, Opava, Jeseník
#
# 15. 2. - 21. 2. 2021
#
# Benešov,   Beroun, Rokycany, České Budějovice, Český Krumlov, Klatovy, Trutnov,   Pardubice, Chrudim, Svitavy, Ústí nad Orlicí, Ostrava-město, Prostějov
#
# 22. 2. - 28. 2. 2021
#
# Praha 1 až   5, Blansko, Brno-město, Brno-venkov, Břeclav, Hodonín, Vyškov, Znojmo,   Domažlice, Tachov, Louny, Karviná
#
# 1. 3. - 7. 3. 2021
#
# Praha 6 až   10, Cheb, Karlovy Vary, Sokolov, Nymburk, Jindřichův Hradec, Litoměřice,   Děčín, Přerov, Frýdek-Místek
#
# 8. 3. - 14. 3. 2021
#
# Kroměříž,   Uherské Hradiště, Vsetín, Zlín, Praha-východ, Praha-západ, Mělník, Rakovník,   Plzeň-město, Plzeň-sever, Plzeň-jih, Hradec Králové, Teplice, Nový Jičín
# ''' # z webu https://www.msmt.cz/vzdelavani/skolstvi-v-cr/organizace-skolniho-roku-2020-2021-v-zakladnich-skolach
#
# SPRING_HOLIDAYS_2='''7. 2. - 13. 2. 2022
#
# Kroměříž, Uherské Hradiště, Vsetín, Zlín, Praha-východ, Praha-západ, Mělník, Rakovník, Plzeň-město, Plzeň-sever, Plzeň-jih, Hradec Králové, Teplice, Nový Jičín
#
# 14. 2. - 20. 2. 2022
#
# Česká Lípa, Jablonec nad Nisou, Liberec, Semily, Havlíčkův Brod, Jihlava, Pelhřimov, Třebíč, Žďár nad Sázavou, Kladno, Kolín, Kutná Hora, Písek, Náchod, Bruntál
#
# 21. 2. - 27. 2. 2022
#
# Mladá Boleslav, Příbram, Tábor, Prachatice, Strakonice, Ústí nad Labem, Chomutov, Most, Jičín, Rychnov nad Kněžnou, Olomouc, Šumperk, Opava, Jeseník
#
# 28. 2. – 6. 3. 2022
#
# Benešov, Beroun, Rokycany, České Budějovice, Český Krumlov, Klatovy, Trutnov, Pardubice, Chrudim, Svitavy, Ústí nad Orlicí, Ostrava-město, Prostějov
#
# 7. 3. - 13. 3. 2022
#
# Praha 1 až 5, Blansko, Brno-město, Brno-venkov, Břeclav, Hodonín, Vyškov, Znojmo, Domažlice, Tachov, Louny, Karviná
#
# 14. 3. - 20. 3. 2022
#
# Praha 6 až 10, Cheb, Karlovy Vary, Sokolov, Nymburk, Jindřichův Hradec, Litoměřice, Děčín, Přerov, Frýdek-Místek
# ''' # z webu https://www.msmt.cz/vzdelavani/skolstvi-v-cr/organizace-skolniho-roku-2021-2022-v-zakladnich-skolach
#
# def get_spring_holiday_date_places(sh_str):
#     dates = None
#     for m in re.finditer(
#         r'^(([0-9].*[0-9])|([^0-9\n].*[^0-9\n]))$', sh_str, re.MULTILINE):
#         if m.group(2):  # numeric => dates
#             assert dates is None
#             dates = re.sub(' [-–] ', '–', m.group(2))
#         elif m.group(3):
#             assert dates is not None
#             place = re.sub(' +', ' ', m.group(3))
#             yield (dates, place)
#             dates = None
#     assert dates is None
#
# def get_spring_holiday_checklist_options():
#     sh2 = {
#         place: dates for dates, place in
#         get_spring_holiday_date_places(SPRING_HOLIDAYS_2)
#         }
#     for dates, place in get_spring_holiday_date_places(SPRING_HOLIDAYS_1):
#         dates2 = sh2[place]
#         yield {
#             'label': '%s a %s: %s'%(dates, dates2, place),
#             'value': '%s+%s'%(dates, dates2)
#             }
#
# print(list(get_spring_holiday_checklist_options()))

# http://svatky.centrum.cz/svatky/statni-svatky/2020/

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
2022-01-01	Den obnovy samostatného českého státu
2022-01-01	Nový rok
2022-04-15	Velký pátek
2022-04-18	Velikonoční pondělí
2022-05-01	Svátek práce
2022-05-08	Den vítězství
2022-07-05	Den slovanských věrozvěstů Cyrila a Metoděje
2022-07-06	Den upálení mistra Jana Husa
2022-09-28	Den české státnosti
2022-10-28	Den vzniku samostatného československého státu
2022-11-17	Den boje za svobodu a demokracii
2022-12-24	Štědrý den
2022-12-25	1. svátek vánoční
2022-12-26	2. svátek vánoční
'''
EXC_DATES_SCHOOL = '''2020-10-29~2020-10-30	podzimní prázdniny
2020-12-23~2021-01-03	vánoční prázdniny
2021-01-29	pololetní prázdniny
2021-04-01	velikonoční prázdniny
2021-07-01~2021-08-31	hlavní prázdniny
2021-10-27	podzimní prázdniny
2021-10-29	podzimní prázdniny
2021-12-23~2022-01-02	vánoční prázdniny
2022-02-04	pololetní prázdniny
2022-04-14	velikonoční prázdniny
2022-07-01~2022-08-31	hlavní prázdniny
'''
EXC_DATES_SPRING_P1 = '''2021-02-22~2021-02-28	jarní prázdniny Praha 1–5
'''


def weekdays_between_dates(wds, start, last):
    start_wd            = start.weekday()
    start_delta_days    = sorted([(wd-start_wd)%WEEK_DAYS for wd in wds])
    shift_days          = start_delta_days[0]
    base    = start+timedelta(shift_days) # first date from start on one of wds
    base_delta_days     = [n-shift_days for n in start_delta_days[1:]]
    base_delta_days.append(WEEK_DAYS)   # cycle: same week day as base
    def acc_deltas():
        prev = 0
        for d in base_delta_days:
            yield timedelta(days = d-prev)
            prev = d
    return list(takewhile(
        lambda date: date<=last,
        accumulate(chain(
            (base,),
            cycle(acc_deltas())
            ))
        ))

def dates_except(dates, exc_dates2desc):
    dates_exc    = [
        date
        for date in dates if date not in exc_dates2desc
        ]
    exc_desc     = [
        (date, exc_dates2desc[date])
        for date in dates if date in exc_dates2desc
        ]
    return (dates_exc, exc_desc)


def ical_make_text_safe(s):
    r""" Replace or escape characters for an iCalendar text.
    Control chars incl. \n are replaced with a space (to make our lives
    easier), '\\', ';' and ',' are escaped.
    """
    return re.sub(r'[\x00-\x19]', ' ', re.sub(r'([\\;,])', r'\\\1', s))

def except_dates2desc(exc_dates):
    exc_dict = {}
    for line in exc_dates.split('\n'):
        line = line.rstrip()
        if line:
            fields = line.split('\t')
            ds = fields[0]
            if '~' not in ds:
                dates = (ymd2date(ds),)
            else:
                d_from,__,d_to = ds.partition('~')
                date_from = ymd2date(d_from)
                date_to   = ymd2date(d_to)
                dates = accumulate(chain(
                    (date_from,), repeat(ONE_DAY, (date_to-date_from).days)
                    ))
            for date in dates:
                # TODO may overwrite another exception
                exc_dict[date] = fields[1]
    return exc_dict

def iter_icalendar(
    dates_info, weekday2time_range, cal_name, event_summary_fmt, info_fmt_map_f
    ):
    """
    Generate iCalendar file contents as an iterator over strings
    (roughly lines).
    """

    event_summary_template = Template(event_summary_fmt)

    yield ((
        '''BEGIN:VCALENDAR
PRODID:-//mojehodiny.nohejl.name//NONSGML mojehodiny 1.0//CS
VERSION:2.0
X-WR-CALNAME:%s
X-WR-TIMEZONE:Europe/Prague
X-WR-CALDESC:
BEGIN:VTIMEZONE
TZID:Europe/Prague
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
DTSTART:19810329T020000
TZNAME:GMT+02:00
TZOFFSETTO:+0200
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
DTSTART:19961027T030000
TZNAME:GMT+01:00
TZOFFSETTO:+0100
END:STANDARD
END:VTIMEZONE
'''%ical_make_text_safe(cal_name)).replace('\n','\r\n')
        )

    for date, info in dates_info:
        yield ("BEGIN:VEVENT\r\n"
                    "SEQUENCE:0\r\n"
                    "STATUS:CONFIRMED\r\n"
                    )
        yield "TRANSP:TRANSPARENT\r\n"
        yield ("SUMMARY:"+
            ical_make_text_safe(event_summary_template.safe_substitute(
                info_fmt_map_f(info)))+
            '\r\n')
        ymd = date.strftime('%Y%m%d')

        time_range = weekday2time_range and weekday2time_range[date.weekday()]
        if time_range:
            yield 'DTSTART:%sT%02i%02i00\r\n'%(ymd, *time_range[0])
            yield 'DTEND:%sT%02i%02i00\r\n'%(ymd, *time_range[1])
        else:
            yield 'DTSTART:%s\r\n'%ymd
            yield 'DTEND:%s\r\n'%ymd
        yield 'END:VEVENT\r\n'
    yield 'END:VCALENDAR\r\n'

def iter_txt_output(dates, exc_desc, part_date, n, n1):
    """
    Generate text (Markdown) summary output as an iterator over strings
    (roughly lines).
    """
    yield '### Počty hodin:\n\n'
    yield ' * Celý kurz:    %i\n'%n
    if part_date:
        yield ' * Před %s: %i\n'%(part_date.strftime(OUTPUT_FMT), n1)
        yield ' * Od %s:   %i\n'%(part_date.strftime(OUTPUT_FMT), n-n1)
    yield '\n'
    yield '### Data kurzu:\n\n'
    for i, date in enumerate(dates):
        yield ' %i. %s %s\n'%(i+1, WD_ABBRS[date.weekday()],
            date.strftime(OUTPUT_FMT))
    yield '### Data volna\n\n'
    if exc_desc:
        for date, desc in exc_desc:
            yield ' * %s %s %s\n'%(WD_ABBRS[date.weekday()],
                date.strftime(OUTPUT_FMT), desc)
    else:
        yield 'Kurz nevychází na žádné dny volna.\n'
    yield '\n'

def date_nmp_fmt_map(nmp_tuple):
    return {'n': nmp_tuple[0],'m': nmp_tuple[1],'p': nmp_tuple[2]}

def exc_s_fmt_map(s_str):
    return {'s': s_str}

def iter_date_numbering_nmp(total, part1):
    assert part1 <= total
    for n in range(1,total+1):
        is_part1 = n <= part1
        m = n if is_part1 else n-part1
        p = 1 if is_part1 else 2
        yield (n, m, p)

def compute(
    start_date,last_date, part_date, exc_dates2desc, weekdays, wd2time_range,
    cal_name=None, event_summary=None,
    exc_cal_name=None, exc_event_summary=None
    ):
    """
    Do all the calendar computations and return a tuple of iterators with the
    output.
    """
    wd_dates        = weekdays_between_dates(weekdays, start_date, last_date)
    dates, exc_desc = dates_except(wd_dates, exc_dates2desc)

    n   = len(dates)
    if part_date:
        dates1 = list(takewhile(lambda date: date<part_date, dates))
        n1  = len(dates1)
    else:
        n1  = n
    txt     = iter_txt_output(dates, exc_desc, part_date, n, n1)
    if cal_name and event_summary:
        dates_nmp = zip(dates, iter_date_numbering_nmp(n, n1))
        ical = iter_icalendar(
            dates_nmp, wd2time_range, cal_name, event_summary, date_nmp_fmt_map
            )
    else:
        ical = None
    if exc_cal_name and exc_event_summary:
        exc_ical = iter_icalendar(
            exc_desc, None, exc_cal_name, exc_event_summary, exc_s_fmt_map
            )
    else:
        exc_ical = None

    return (txt, ical, exc_ical)

# "main" script for Google Colab (also works for CLI):
if __name__ == '__main__':
    weekdays_mo_fri     = [
        hodina_v_po, hodina_v_út, hodina_v_st, hodina_v_čt, hodina_v_pá
        ]
    weekdays            = list(compress(range(0, 5), weekdays_mo_fri))
    wd2time_range       = {wd: None for wd in weekdays}
    start_date          = ymd2date(začátek_školního_roku)
    part_date           = ymd2date(předěl_roku)
    last_date           = ymd2date(konec_školního_roku)
    exc_dates2desc      = except_dates2desc(
        EXC_DATES_STATE if vynechávat=='jen svátky'
        else EXC_DATES_SCHOOL + EXC_DATES_SPRING_P1 + EXC_DATES_STATE)
    iter_txt, iter_ical, iter_exc_ical = compute(
        start_date,last_date, part_date, exc_dates2desc,
        weekdays, wd2time_range,
        cal_name='mojehodiny', event_summary='mojehodiny $n $m $p',
        exc_cal_name='nehodiny', exc_event_summary='nehodiny $s')
    for t in iter_txt:
        sys.stdout.write(t)
    if iter_ical:
        with open('mojehodiny.ics','w') as f:
            for i in iter_ical:
                f.write(i)
    if iter_exc_ical:
        with open('exc_mojehodiny.ics','w') as f:
            for i in iter_exc_ical:
                f.write(i)
