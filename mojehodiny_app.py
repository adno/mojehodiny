#!/usr/bin/env python

from datetime import datetime as dt
import re
from itertools import chain
from urllib import parse as urllib_parse

import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc

import mojehodiny as mh

def ymd_dt2dt(date_str):
    """
    Convert a Y-M-D date from a Dash component to a datetime.datetime object.
    """
    if not isinstance(date_str, str):
        return date_str
    if 'T' in date_str:
        # sometimes time portion "T..." is returned from the date picker
        date_str = date_str.partition('T')[0]
    return dt.strptime(date_str, '%Y-%m-%d')

CZ_WD_LABELS    = (
    'pondělí', 'úterý', 'středa', 'čtvrtek', 'pátek', 'sobota', 'neděle'
    )
WD_RANGE        = range(0,5)


def markdown_subset_iter(md_str):
    """
    Process a subset of Markdown into (an iterator of) Dash components and
    strings. Like dash_core_components.Markdown, but works as a generator and
    avoids DIV/P around the whole Markdown/block. Handles only `code`,
    *em* and **strong** unless the markup is nested.
    """
    index = 0
    for match in re.finditer(r'(`|\*|\*\*)([^`*]+)\1', md_str):
        outer_start, outer_stop = match.span(0)
        inner_start, inner_stop = match.span(2)
        tag = match.group(1)
        yield md_str[index:outer_start]
        if tag == '`':
            yield html.Code(md_str[inner_start:inner_stop])
        elif tag == '*':
            yield html.Em(md_str[inner_start:inner_stop])
        else:
            assert tag == '**'
            yield html.Strong(md_str[inner_start:inner_stop])
        index = outer_stop
    yield md_str[index:]

def markdown_subset(md_str):
    """
    Process a subset of Markdown into a list of Dash components and strings.
    See `markdown_subset_iter`.
    """
    return list(markdown_subset_iter(md_str))

def markdown_subset_p(md_str):
    """
    Process a subset of Markdown into a list of Dash components and strings
    wrapped in html.P. (Replacement for dash_core_components.Markdown that
    loads instantly.)
    """
    return html.P(markdown_subset(md_str))


def markdown_subset_strip(md_str):
    """
    Strips a subset of Markdown from a string.
    """
    return re.sub(r'(`|\*|\*\*)([^`*]+)\1', r'\2', md_str)


def checklist_enables_inputs(checklist_id, input_ids):
    """
    Set up a callback for a weekday checklist: A weekday's checkbox enables
    time range inputs for the weekday's time range).
    """
    @app.callback(
        [Output(id, 'disabled') for id in input_ids],
        [Input(checklist_id, 'value')]
    )
    def update_inputs_enabled(checklist):
        disabled = not checklist
        return [disabled]*len(input_ids)

def hm_range_ok(start_h, start_m, end_h, end_m):
    """
    Check that a HH:MM-HH:MM time range starts before it ends.
    """
    return start_h*60+start_m < end_h*60+end_m

def time_range_inputs_displays_error(input_ids, error_id):
    """
    Set up a callback for four time range inputs HH:MM-HH:MM.
    Invalid time range displays an error.
    """
    @app.callback(
        Output(error_id, 'children'),
        [Input(id, 'value') for id in input_ids]
    )
    def update_error(start_h, start_m, end_h, end_m):
        if (None in (start_h, start_m, end_h, end_m) or
            hm_range_ok(start_h, start_m, end_h, end_m)):
            return ''
        return '← chybný konec'

def iter_wd_tr_ids():
    """
    Iterate weekday time range input ids.
    """
    for i in WD_RANGE:
        checlist_id = 'wd%i'%i
        yield checlist_id + '_start_h'
        yield checlist_id + '_start_m'
        yield checlist_id + '_end_h'
        yield checlist_id + '_end_m'

def wd_cl_tr_values2dict(args):
    """
    Convert weekday checklist time range input values to a weekday=>time_range
    dictionary.
    """
    wd2time_range = {}
    args = iter(args)
    for i in WD_RANGE:
        wd_checklist    = next(args)
        if wd_checklist:
            wd2time_range[i] = None
    for i in WD_RANGE:
        start_h  = next(args)
        start_m  = next(args)
        end_h    = next(args)
        end_m    = next(args)
        if i in wd2time_range:
            if (None not in (start_h, start_m, end_h, end_m) and
                hm_range_ok(start_h, start_m, end_h, end_m)):
                wd2time_range[i] = ((start_h, start_m), (end_h, end_m))
            # else: assert wd2time_range[i] == None
    return wd2time_range


WD_CHECKLIST_IDS  = ['wd%i'%i for i in WD_RANGE]
WD_TIME_RANGE_IDS = list(iter_wd_tr_ids())


def week_day_check_time_range_pickers():
    """
    Construct week day checklist with timer range pickers for each day and
    set up the necessary callbacks for enabling inputs and checking validity.
    """
    for i in WD_RANGE:
        label   = CZ_WD_LABELS[i]
        checlist_id = 'wd%i'%i
        start_h_id  = checlist_id + '_start_h'
        start_m_id  = checlist_id + '_start_m'
        end_h_id    = checlist_id + '_end_h'
        end_m_id    = checlist_id + '_end_m'
        error_id    = checlist_id + '_error'
        time_range_input_ids = (start_h_id, start_m_id, end_h_id, end_m_id)
        checklist_enables_inputs(checlist_id, time_range_input_ids)
        time_range_inputs_displays_error(time_range_input_ids, error_id)
        yield dcc.Checklist(
            id=checlist_id,
            options=[{'label': label.capitalize(), 'value': i}]
            )
        yield html.Div([
            html.Div([
                dcc.Input(
                    id=start_h_id, type='number', inputMode='numeric',
                    placeholder='hh', min=0, max=23, step=1
                ),
                html.Span(':'),
                dcc.Input(
                        id=start_m_id, type='number', inputMode='numeric',
                        placeholder='mm', min=0, max=59, step=1
                ),
                html.Span('–'),
                dcc.Input(
                    id=end_h_id, type='number', inputMode='numeric',
                    placeholder='hh', min=0, max=23, step=1
                ),
                html.Span(':'),
                dcc.Input(
                        id=end_m_id, type='number', inputMode='numeric',
                        placeholder='mm', min=0, max=59, step=1
                )]),
            html.Span(id=error_id, className='error'),
            ], className='mh-time-range')

# Setup the app and layout:


APP_PATH = '/mojehodiny'
APP_NAME = 'Moje hodiny'
APP_MD_DESC = (
    'Máte kurz nebo kroužek, který se koná pravidelně určité dny v týdnu mimo '
    'svátků nebo prázdnin a potřebujete zjistit, **na které dny připadne**, '
    '**kdy naopak není kvůli volnu**, a spočítat, **kolik budete mít lekcí**? '
    'Přesně to umí Moje hodiny a navíc vám vytvoří i **kalendář lekcí '
    '(a volna)** do počítače nebo telefonu.'
)
APP_MD_FOOTER = '''Verze 0.1.23 (2020-09-29). 🐨 2020 [Adam Nohejl](http://nohejl.name/). Zdroják je [![GitHub](/assets/GitHub-Mark-32px.png) na GitHubu](https://github.com/adno/mojehodiny).

Napsáno v Pythonu pomocí frameworku [Dash](https://dash.plotly.com/)
bez jediné řádky JavaScriptu a jen s pár řádkami HTML, CSS a Markdownu.

Hlášení chyb, nápady, postřehy a pochvaly prosím na mail
[adam&#x40;nohejl.name](mailto:adam&#x40;nohejl.name).
'''
APP_DESC = markdown_subset_strip(APP_MD_DESC)

app = dash.Dash(
    __name__,
    title=APP_NAME,
    update_title=None,
    meta_tags=[
        {'name': 'description', 'content': APP_DESC},
        {
            'name': 'viewport',
            'content': 'width=device-width, initial-scale=1.0'
            }
        ]
    )

app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <!-- Global site tag (gtag.js) - Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=UA-179223647-1"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());

          gtag('config', 'UA-179223647-1');
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
''' # adds two SCRIPT elements to HEAD for Google Analytics

# the hidden property does not seem to work for html.Button
# (as opposed to html.Div), so we just use CSS:
SHOW_BUTTON_STYLE_HIDDEN = {'display': 'none'}
SHOW_BUTTON_STYLE_VISIBLE = {'float': 'right'}

default_school_year_2020_2021 = dt.now() <= dt(2021, 6, 30)
school_year_start   = 2020 if default_school_year_2020_2021 else 2021
school_year_end     = school_year_start + 1

app.layout = html.Div([ # container
    dcc.Location(id='url', refresh=False),
    html.H1(APP_NAME),
    markdown_subset_p(APP_MD_DESC),
    html.Hr(),
    html.Button('Uložit…', className='button-primary', id='link_show',
        n_clicks_timestamp=-1, style=SHOW_BUTTON_STYLE_VISIBLE),
    html.Div(
        [
        html.P('Odkaz si zkopírujte nebo dejte do záložek, abyste měli '
            'později přístup k vyplněnému obsahu. (Vaše data se jinak nikam '
            'neukládají.)'),
        html.P(
            html.Code(dcc.Link(id='link', href='')), className='center output',
            style={'whiteSpace': 'pre-wrap', 'wordBreak': 'break-word'}
        ),
        html.Div(
            html.Button('OK', className='button-primary', id='link_hide',
                n_clicks_timestamp=-1),
            style={'textAlign': 'right'}
        )],
        id='link_container',
        className='output row',
        hidden=True
    ),
    html.Div([ # row
        html.Div([
            html.H2('Trvání kurzu'),
            html.Label('Začátek a konec:'),
            dcc.DatePickerRange(
                id='course_range',
                first_day_of_week=1, # Monday
                month_format='M. Y',
                display_format='D. M. Y',
                start_date_placeholder_text='začátek',
                end_date_placeholder_text='konec',
                min_date_allowed=dt(2020, 1, 1),
                max_date_allowed=dt(2022, 12, 31),
                start_date=dt(school_year_start, 9, 1).date(),
                end_date=dt(school_year_end, 6, 30).date()
                ),
            html.Label('Rozdělit kurz na dvě části (kalendářní roky, '
                'semestry, …) datem:'),
            dcc.DatePickerSingle(
                id='part_date',
                placeholder='zač. 2. části',
                first_day_of_week=1, # Monday
                month_format='M. Y',
                display_format='D. M. Y',
                clearable=True,
                ),
            html.Span(id='part_date_warning', className='warning'),
            html.H2('Dny v týdnu'),
            html.Div(html.P('Vyberte dny v týdnu, ve které se kurz koná. '
                'Můžete také zadat časy pro kalendářové události.')),
            *week_day_check_time_range_pickers()
            ], className='six columns'
            ),
        html.Div([
            html.H2('Dny volna'),
            dcc.Checklist(id='holidays', options=[
                {'label': 'Státní svátky 2020–2022', 'value': 'state'},
                {'label': 'Školní prázdniny 2020/21 a 2021/22 (celostátní)',
                    'value': 'school'}
                ]),
            html.H3('Jarní prázdniny 2020/21 a 2021/22'),
            dcc.Dropdown(id='spring_holidays',
                placeholder='Hledat podle místa…',
                options=[{'label': '1. 2.–7. 2. 2021 a 14. 2.–20. 2. 2022: Česká Lípa, Jablonec nad Nisou, Liberec, Semily, Havlíčkův Brod, Jihlava, Pelhřimov, Třebíč, Žďár nad Sázavou, Kladno, Kolín, Kutná Hora, Písek, Náchod, Bruntál', 'value': '1. 2.–7. 2. 2021+14. 2.–20. 2. 2022'}, {'label': '8. 2.–14. 2. 2021 a 21. 2.–27. 2. 2022: Mladá Boleslav, Příbram, Tábor, Prachatice, Strakonice, Ústí nad Labem, Chomutov, Most, Jičín, Rychnov nad Kněžnou, Olomouc, Šumperk, Opava, Jeseník', 'value': '8. 2.–14. 2. 2021+21. 2.–27. 2. 2022'}, {'label': '15. 2.–21. 2. 2021 a 28. 2.–6. 3. 2022: Benešov, Beroun, Rokycany, České Budějovice, Český Krumlov, Klatovy, Trutnov, Pardubice, Chrudim, Svitavy, Ústí nad Orlicí, Ostrava-město, Prostějov', 'value': '15. 2.–21. 2. 2021+28. 2.–6. 3. 2022'}, {'label': '22. 2.–28. 2. 2021 a 7. 3.–13. 3. 2022: Praha 1 až 5, Blansko, Brno-město, Brno-venkov, Břeclav, Hodonín, Vyškov, Znojmo, Domažlice, Tachov, Louny, Karviná', 'value': '22. 2.–28. 2. 2021+7. 3.–13. 3. 2022'}, {'label': '1. 3.–7. 3. 2021 a 14. 3.–20. 3. 2022: Praha 6 až 10, Cheb, Karlovy Vary, Sokolov, Nymburk, Jindřichův Hradec, Litoměřice, Děčín, Přerov, Frýdek-Místek', 'value': '1. 3.–7. 3. 2021+14. 3.–20. 3. 2022'}, {'label': '8. 3.–14. 3. 2021 a 7. 2.–13. 2. 2022: Kroměříž, Uherské Hradiště, Vsetín, Zlín, Praha-východ, Praha-západ, Mělník, Rakovník, Plzeň-město, Plzeň-sever, Plzeň-jih, Hradec Králové, Teplice, Nový Jičín', 'value': '8. 3.–14. 3. 2021+7. 2.–13. 2. 2022'}],
                multi=True, optionHeight=120), # 90 enough on desktop, 120 on iPhone
            html.Div(id='holiday_warning', className='warning'),
            html.H3('Vlastní dny volna'),
            markdown_subset_p(
                'Můžete zadat jeden den nebo vícedenní období volna na řádek. '
                'Za dnem nebo obdobím může následovat název oddělený '
                'středníkem nebo tabulátorem. Období může být např. '
                've formátu `d.m.r-d.m.r`, `d.m.-d.m.r`, `r-m-d~r-m-d` nebo '
                '`r-m-d~r-m`, obdobně se formátuje jednotlivé datum.'),
            dcc.Textarea(
                id='custom_holidays',
                placeholder='d.m.r[-d.m.r]; název volna',
                className='fullwidth',
                style={'height': 100},
            ),
            html.Div(id='confirmed_custom_holidays',
                hidden=True
                ),
            html.Button('Potvrdit', id='custom_holidays_submit', n_clicks=0),
            html.Span(id='custom_holidays_error', className='error'),
            html.Span(id='custom_holidays_warning', className='warning'),
            ], className='six columns'),
        ], className='row'),
    html.Hr(),
    html.Div([
        html.Div([
            html.H2('Výsledné počty a data'),
            html.Div(id='custom_holidays_warning_in_output',
                className='warning'),
            html.Div(id='error_container'),
            html.Div(id='output_container')
            ], className='six columns output rcol'),
        html.Div([
            html.H2('Kalendáře'),
            markdown_subset_p(
                'Můžete si stáhnout kalendářový soubor `.ics` (soubor '
                'iCalendar pro kalendář na vašem počítači nebo telefonu). '
                'V kalendáři volna se vytvoří celodenní události. V kalendáři '
                'kurzu se vytvoří události s časy, pokud je zadáte.'),
            html.H3('Kalendář kurzu'),
            html.Label('Název kalendáře:'),
            dcc.Input(id='calendar_name',
                placeholder='Zorbing II', className='fullwidth'),
            html.Label(markdown_subset(
                'Název události, kde `$n` = číslo hodiny, '
                '`$p` = část roku (1 nebo 2), '
                '`$m` = číslo hodiny v části roku:'
                )),
            dcc.Input(id='event_name', placeholder='Zorbing II #$n ($p/$m)',
                className='fullwidth'),
            html.Div(id='calendar_output_container',
                className='output center'),
            html.H3('Kalendář volna'),
            html.Label('Název kalendáře:'),
            dcc.Input(id='exc_calendar_name',
                placeholder='Volno (zorbing)', className='fullwidth'),
            html.Label(markdown_subset(
                'Název události, kde `$s` je název svátku nebo prázdnin:')),
            dcc.Input(id='exc_event_name',
                placeholder='Dnes nezorbujeme: $s', className='fullwidth'),
            html.Div(id='exc_calendar_output_container',
                className='output center')
            ], className='six columns lcol'),
        ], className='row'),
    html.Hr(),
    dcc.Markdown(APP_MD_FOOTER, className='small-print center', id='mh_footer')
    ], className='container')


# Callbacks:

ALL_FIELD_OUTPUTS = ([
    Output('course_range', 'start_date'), Output('course_range', 'end_date'),
    Output('part_date', 'date'),
    Output('holidays', 'value'), Output('spring_holidays', 'value'),
    Output('custom_holidays', 'value'),
    Output('custom_holidays_submit', 'n_clicks'),
    Output('calendar_name', 'value'), Output('event_name', 'value'),
    Output('exc_calendar_name', 'value'), Output('exc_event_name', 'value')
    ]+
    [Output(id, 'value') for id in WD_CHECKLIST_IDS]+
    [Output(id, 'value') for id in WD_TIME_RANGE_IDS]
    )

LIST_FIELD_IDS = {'holidays', 'spring_holidays', *WD_CHECKLIST_IDS}

@app.callback(
    ALL_FIELD_OUTPUTS+[Output('url', 'pathname')],
    [Input('url', 'search')],
    [State('url', 'pathname')]
    )
def update_url(query, path):
    """
    Fill the form based on Url.
    """
    if not query:
        if path==APP_PATH:
            raise PreventUpdate
        output_values = [dash.no_update]*len(ALL_FIELD_OUTPUTS)
    else:
        assert query.startswith('?')
        qs_param2values = urllib_parse.parse_qs(query[1:])
        output_values = []
        # We use try-blocks for dates and ints, but we do not check for
        # consistency.
        for output in ALL_FIELD_OUTPUTS:
            oid = output.component_id
            if oid == 'custom_holidays_submit':
                output_values.append(
                    1 if 'custom_holidays' in qs_param2values else 0
                    )
                continue
            check_date = False
            if oid == 'course_range':
                param = output.component_property # start_date or end_date
                check_date = True
            else:
                if oid == 'part_date':
                    check_date = True
                param = oid
            value_list = qs_param2values.get(param, None)
            if value_list is None:
                output_values.append([] if (oid in LIST_FIELD_IDS) else None)
            elif oid in LIST_FIELD_IDS:
                if oid in WD_CHECKLIST_IDS:
                    try:
                        value = [int(value_list[-1])]
                    except ValueError:
                        value = []
                    output_values.append(value)
                else:
                    output_values.append(value_list)
            else:
                if oid in WD_TIME_RANGE_IDS:
                    try:
                        value = int(value_list[-1])
                    except ValueError:
                        value = None
                    output_values.append(value)
                else:
                    value = value_list[-1]
                    if check_date:
                        try:
                            value = ymd_dt2dt(value)
                        except ValueError:
                            value = None
                    output_values.append(value)
    # last: Output('url', 'pathname') => force our app path
    output_values.append(dash.no_update if path==APP_PATH else APP_PATH)

    return output_values

@app.callback(
    [Output('part_date', 'min_date_allowed'),
        Output('part_date', 'max_date_allowed'),
        Output('part_date_warning', 'children')
        ],
    [Input('course_range', 'start_date'),
        Input('course_range', 'end_date'),
        Input('part_date', 'date')]
    )
def update_part_date(start_date, end_date, part_date):
    start_date      = ymd_dt2dt(start_date)
    end_date        = ymd_dt2dt(end_date)
    part_date       = ymd_dt2dt(part_date)

    warning         = None
    if start_date and end_date and part_date:
        if not (start_date <= part_date <= end_date):
            warning = '← Datum mimo trvání kurzu nemá vliv.'
        elif start_date == part_date:
            warning = '← Datum začátku kurzu nemá vliv.'

    if start_date and end_date:
        return (start_date, end_date, warning)
    return [None]*3#4

@app.callback(
    Output('holiday_warning', 'children'),
    [Input('holidays', 'value'),
     Input('spring_holidays', 'value')
    ])
def update_holiday_error(holidays, spring_holidays):
    if not holidays:
        if spring_holidays:
            return 'Nejsou vybrány školní prázdniny mimo jarních.'
    elif 'school' in holidays and not spring_holidays:
        return 'Nejsou vybrány žádné jarní prázdniny.'
    return None


@app.callback(
    [Output('custom_holidays_error', 'children'),
        Output('confirmed_custom_holidays', 'children')],
    [Input('custom_holidays_submit', 'n_clicks')],
    [State('custom_holidays', 'value'),
        State('confirmed_custom_holidays', 'children')]
)
def confirm_custom_holidays(n_clicks, value, previously_confirmed):
    if n_clicks > 0 and value:
        try:
            __ = list(mh.parse_date_desc(value)) # throw away the retval
        except ValueError as error:
            return (error.args[0], previously_confirmed)
        return (None, value)
    return (None, None)

@app.callback(
    [Output('custom_holidays_warning', 'children'),
        Output('custom_holidays_warning_in_output', 'children')],
    [Input('custom_holidays', 'value'),
        Input('custom_holidays_error', 'children'),
        Input('error_container', 'children'),
        ]
)
def update_custom_holiday(value, custom_holiday_error, main_error):
    """
    Update the custom holiday edited (not confirmed) warning.
    """
    # The `value` itself is ignored on purpose, we need just `triggered`
    triggered = dash.callback_context.triggered
    changed = triggered and triggered[0]['prop_id'] == 'custom_holidays.value'

    changed_warning = (
        'Nepotvrzené změny.'
        if (changed and not custom_holiday_error)
        else None
        )
    secondary_error = (
        'Pozor: Počty a data nemusí být aktuální. '
        'Vlastní dny volna obsahují nepotvrzené změny.'
        if ((changed or custom_holiday_error) and not main_error) else None
        )
    return (changed_warning, secondary_error)

def download_link(file_name, ics_iter):
    download_url = (
        'data:text/calendar;charset=utf-8,' +
        urllib_parse.quote(''.join(ics_iter))
        )
    return html.Strong([
        'Ke stažení: ',
        html.A('📅 '+file_name,
            href=download_url,
            download=urllib_parse.quote(file_name))
        ])

def urlenc_seq(list_or_something):
    """
    Transforms values to sequences (lists) that can be passed as values to
    urllib_parse.urlencode(..., doseq=True) to create an URL encoding an
    application state.
    """
    if isinstance(list_or_something, list):
        return list_or_something    # a list or an empty list
    if list_or_something is None or list_or_something == '':
        return []                   # None or '' => an empty list
    return [list_or_something]      # else: a single-value list

def url_with_updated_path_query(url, path, query):
    """
    Change the path and query components of the `url` to `path` and `query`.
    """
    parsed = urllib_parse.urlparse(url)
    # We ignore ;params and #fragment
    return f'{parsed.scheme}://{parsed.netloc}{path}?{query}'

@app.callback(
    [Output('link', 'href'),
        Output('link_container', 'hidden'),
        # the 'hidden' property does not work with html.Button => use style:
        Output('link_show', 'style'),
        Output('output_container', 'children'),
        Output('error_container', 'children'),
        Output('calendar_output_container', 'children'),
        Output('exc_calendar_output_container', 'children')
        ],
    [Input('course_range', 'start_date'), Input('course_range', 'end_date'),
        Input('part_date', 'date'),
        Input('holidays', 'value'), Input('spring_holidays', 'value'),
        Input('confirmed_custom_holidays', 'children'),
        Input('calendar_name', 'value'), Input('event_name', 'value'),
        Input('exc_calendar_name', 'value'), Input('exc_event_name', 'value'),
        Input('url','href'),
        Input('link_show', 'n_clicks_timestamp'),
        Input('link_hide', 'n_clicks_timestamp'),
        ]+[Input(id, 'value') for id in WD_CHECKLIST_IDS]+
        [Input(id, 'value') for id in WD_TIME_RANGE_IDS],
     )

def update_app(
    start_date, end_date, part_date,
    holidays, spring_holidays, custom_holidays,
    calendar_name, event_name,
    exc_calendar_name, exc_event_name,
    current_url,
    link_show_timestamp, link_hide_time_stamp,
    *args
    ):
    """
    Update the app's main outputs (including a save/share link) based on all
    the inputs.
    """
    show_link = link_show_timestamp > link_hide_time_stamp
    # show_link is False if both == -1 (neither clicked)
    if show_link:
        app_state_kvs = (
            ('start_date',              urlenc_seq(start_date)),
            ('end_date',                urlenc_seq(end_date)),
            ('part_date',               urlenc_seq(part_date)),
            ('holidays',                urlenc_seq(holidays)),
            ('spring_holidays',         urlenc_seq(spring_holidays)),
            ('custom_holidays',         urlenc_seq(custom_holidays)),
            ('calendar_name',           urlenc_seq(calendar_name)),
            ('event_name',              urlenc_seq(event_name)),
            ('exc_calendar_name',       urlenc_seq(exc_calendar_name)),
            ('exc_event_name',          urlenc_seq(exc_event_name)),
            *(
                (id, urlenc_seq(arg)) for id, arg
                in zip(chain(WD_CHECKLIST_IDS, WD_TIME_RANGE_IDS), args)
                if arg is not None
                # if clause leaves out all the empty WD_TIME_RANGE_IDS' args
            )
            )
        app_state_url = url_with_updated_path_query(
            current_url,
            APP_PATH,
            urllib_parse.urlencode(app_state_kvs, doseq=True)
            )
    else:
        app_state_url = ''
    link_container_button = (
        app_state_url,
        not show_link,  # link container hidden <=> not show link
        SHOW_BUTTON_STYLE_HIDDEN if show_link else SHOW_BUTTON_STYLE_VISIBLE
        # show button hidden <=> show_link
        )

    wd2time_range       = wd_cl_tr_values2dict(args)
    if not (start_date and end_date):
        return (*link_container_button, None,)+(
            html.Span('Není zadáno trvání kurzu.', className='error'),)*3
    start_date = ymd_dt2dt(start_date)
    end_date = ymd_dt2dt(end_date)
    part_date = ymd_dt2dt(part_date)
    if not wd2time_range:
        return (*link_container_button, None, *(
            html.Span('Nejsou vybrány žádné dny v týdnu.', className='error'),
            )*3)
    if holidays:
        exc_dates       = mh.EXC_DATES_STATE if ('state' in holidays) else ''
        if 'school' in holidays:
            exc_dates   += mh.EXC_DATES_SCHOOL
        exc_dates2desc  = mh.except_dates2desc(exc_dates)
    else:
        exc_dates2desc  = {}
    if spring_holidays:
        for ranges_str in spring_holidays:
            range_str_1, __, range_str_2 = ranges_str.partition('+')
            assert range_str_1 and range_str_2, ranges_str
            for range_str in (range_str_1, range_str_2):
                dates   = mh.dm_dmy_range2dates(range_str)
                desc    = 'jarní prázdniny %s'%range_str
                for date in dates:
                    exc_dates2desc[date] = desc
    if custom_holidays:
        for date_range, desc in mh.parse_date_desc(custom_holidays):
            dates = mh.date_range2dates(date_range)
            for date in dates:
                exc_dates2desc[date] = desc

    # Require both calendar and event name to generate a calendar, else ignore:
    if not (calendar_name and event_name):
        calendar_name = None
        event_name = None
    if not (exc_calendar_name and exc_event_name):
        exc_calendar_name = None
        exc_event_name = None

    txt, ical, exc_ical = mh.compute(
        start_date, end_date, part_date,
        exc_dates2desc,
        wd2time_range.keys(), wd2time_range,
        cal_name=calendar_name, event_summary=event_name,
        exc_cal_name=exc_calendar_name, exc_event_summary=exc_event_name,
        )

    return (
        *link_container_button,
        dcc.Markdown(''.join(txt)),
        None,
        download_link(calendar_name+'.ics', ical)
            if calendar_name
            else html.Span(
                'Pro vytvoření kalendáře zadejte názvy kalendáře i události.',
                className='error'),
        download_link(exc_calendar_name+'.ics', exc_ical)
            if exc_calendar_name
            else html.Span(
                'Pro vytvoření kalendáře zadejte názvy kalendáře i události.',
                className='error')
        )


if __name__ == '__main__':
    # host='0.0.0.0' => make available on LAN for testing
    app.run_server(debug=True, host='0.0.0.0')
