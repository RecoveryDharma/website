# encoding: utf-8

'''☸️ Recovery Dharma Website Tools: CSV generation.'''

from . import VERSION
import argparse, sys, csv, datetime, re


_export_days = {
    'Mon': 0,
    'Tue': 1,
    'Wed': 2,
    'Thu': 3,
    'Fri': 4,
    'Sat': 5,
    'Sun': 6
}

_languages = {
    'Danish': 'danske',
    'Dutch': 'Nederlandse',
    'English': 'English',
    'English & Thai': 'English & Thai (ภาษาไทย)',
    'German': 'deutsche',
    'Portuguese': 'portuguesa',
    'Swedish': 'svenska',
}

_kinds = {
    'Hybrid (In-Person & Online)': 'hybrid',
    'In-Person': 'in-person',
    'In-person': 'in-person',
    'Online': 'virtual',
    'Online (Soon to be Hybrid)': 'virtual'
}

_duration_parser = re.compile(r'(\d+)')  # Maybe we can do something more sophisticated?


def _aware_now() -> datetime.datetime:
    '''Return the current time UTC in a timezone-aware object.'''
    return datetime.datetime.now(datetime.timezone.utc)


def _clean_up_name(name: str) -> str:
    '''Clean up a meeting name.

    This should do some scrubbing of the names of meetings so we don't get entire swaths of meetings
    that all start with ``RD``. We know they're RD meetings! A lot in the spreadsheet start with
    ``RD`` which can be dropped. Some start with ``RD @ sangha`` which we can change to
    ``sangha RD @``. And there are numerous ``RDO ⦿ name`` which can probably become ``name ⦿ RDO``.

    But we want to just test if the new site can handle many meetings, so for now I'm
    leaving the name alone.  🔮 TODO implement this
    '''
    return name


def _compute_start(start: str, now: datetime.datetime) -> datetime.datetime:
    '''Compute the next date a meeting should start.

    ``start`` contains a string like ``Mon 1:00 AM`` or ``Wed 4:45 PM``. We need to produce the next
    nearest future date past ``now`` that would be that date as a string, such as
    ``2022-07-18 01:00:00`` or ``2022-06-20 04:45:00``.
    '''

    # Parse the ``Wed 4:45 PM`` format
    day_of_week, time_of_day, meridiem = start.split()
    day_of_week = _export_days[day_of_week]

    # Figure out the next nearest day of the week from now that it'll occur
    days_ahead = day_of_week - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    meeting = now + datetime.timedelta(days_ahead)

    # Now set the time
    h, m = time_of_day.split(':')
    h, m = int(h), int(m)
    if meridiem == 'PM': h += 12
    if h == 24: h = 0
    return datetime.datetime(meeting.year, meeting.month, meeting.day, h, m, 0, 0, meeting.tzinfo)


def _compute_end(start: datetime.datetime, description: str) -> datetime.datetime:
    '''Compute the end date/time of a meeting.

    Based on the ``start`` time and some string ``description`` like ``40 minutes`` figure out an
    end time.  Note the ``description`` in the RD spreadsheet is free text and may be unusable
    to figure out a duration. Possible values I've seen include: ``120 minutes``, ``40 min.``,
    ``40 minutes but we can add to it if necessary``, ``60``, etc.
    '''
    match = _duration_parser.match(description)
    if not match: return None
    minutes = int(match.group(1))
    return start + datetime.timedelta(minutes=minutes)


def _convert(input_file, output_file):
    reader, writer, now, count = csv.reader(input_file), csv.writer(output_file), _aware_now(), 0
    for (
        b0, b1, b2, utc, stat, kind, day, tod, tz, b3, name, url, mtgid, pwd, email, st, country, lang, city,
        addr, aff, b4, b5, b6, duration
    ) in reader:
        # Skip header rows
        if b0.startswith('[RDG internal use only]') or b0.startswith('Got it, you want to CHANGE'): continue
        # Skip footer rows
        if not b1 and not b2 and not utc and not stat and not kind: continue
        # Skip blank times
        if not utc: continue

        name  = _clean_up_name(name)
        lang  = _languages.get(lang, lang)
        start = _compute_start(utc, now)
        end   = _compute_end(start, duration)
        kind  = _kinds.get(kind, kind)
        desc  = f'For more information contact <a href="mailto:{email}">{email}</a>. (Note: this information automatically imported.)'

        start_date, start_time = start.date().isoformat(), start.time().isoformat()
        if end:
            end_date, end_time = end.date().isoformat(), end.time().isoformat()
        else:
            end_date = end_time = ''

        writer.writerow((
            name, desc, start_date, start_time, end_date, end_time, 'UTC', '', '', aff, kind,
            url, mtgid, pwd
        ))
        count += 1

    print(f'Wrote {count}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(prog='rd-csv', description='Recovery Dharma Website CSV tool')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    parser.add_argument(
        'input_file', type=argparse.FileType('r'), default=sys.stdin, nargs='?',
        help='Downloaded unsorted CSV file of the meeting spreadsheet to convert'
    )
    parser.add_argument(
        'output_file', type=argparse.FileType('w'), default=sys.stdout, nargs='?',
        help='Plugin-format meeting CSV spreadsheet to generate'
    )
    opts = parser.parse_args()
    _convert(opts.input_file, opts.output_file)
    opts.input_file.close()
    opts.output_file.close()
    sys.exit(0)


if __name__ == '__main__':
    main()


# unsorted export (this is the one I should be using!):
#
# col 0 is mostly blank; col 1 is "add new, add, change, etc"
# col 2 is the timestamp of the update to that row; we can ignore it
# col 3 "day time AM/PM" in UTC
# col 4 "open to public" ("Yes", "Yes - Masks Required", etc.)
# col 5 how = Online, In-[Pp]erson, "Online (Soon to be Hybrid)", "Hybrid (In-Person & Online)"
# col 6 day of week (redundant with col 3), col 7 time of day (redundant with col 3), col 8 tz
# col 9 is entirely blank
# col 10 meeting name
# col 11 is url for online (blank for strictly in person, but values vary widely)
# col 12 is meeting ID (but sometimes is a URL), col 13 is password
# col 14 is contact email
# col 15 is state (region, or "Online" for strictly online mtgs), 16 country, 17 is spoken language
# col 18 is city (or sangha), col 19 is address ("for BRN mapping purposes")
# col 20 is affinity (often blank, and used only for online meetings)
# col 21 is blank or says "Updated Needed.\nLast: M/D/Y" in US-centric date
# col 22 is the date of last update (US-centric)—col 21 dupes this date for some reason
# col 23 is the "Non-public Contact Person (for internal RDG use only)"
# col 24 is "How long does the meeting last" and is basically free text
#
# Plugin import:
# col 0 name
# col 1 description
# col 2 start date
# col 3 start time
# col 4 end date
# col 5 end time
# col 6 time zone
# col 7 venue name
# col 8 organizer
# col 9 category
# col 10 kind (virtual, hybrid, in-person)
# col 11 link
# col 12 meeting id
# col 13 passwd
