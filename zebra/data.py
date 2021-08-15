"""Tools for analyzing Zebra motion capture data from FRC Competitions.
"""
import os.path
import sys

import argparse
import json
import urllib.error

dir_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(dir_path, '..'))
import zebra.tba
import zebra.auth


def download_match(key, file, max_no_path_matches=5):
    """Downloads motion capture data and match scores from TBA."""

    def _event_keys():
        print()
        print('Downloading events for:', key)
        event_keys = zebra.tba.get_events(key, option='keys')
        for event_key in event_keys:
            print('Processing event:', event_key)
            yield event_key

    def _match_path_data():
        for event_key in _event_keys():
            no_path_matches = 0
            has_path_data = False
            match_keys = zebra.tba.get_match_keys(event_key)
            for match_key in match_keys:
                try:
                    zdata = zebra.tba.get_zebra(match_key)
                    score_data = zebra.tba.get_match_scores(match_key)
                    has_path_data = True
                    no_path_matches = 0
                except urllib.error.HTTPError:
                    yield event_key, match_key, None, None,
                    no_path_matches += 1
                    if (no_path_matches > max_no_path_matches and
                            not has_path_data):
                        break
                    else:
                        continue
                yield event_key, match_key, zdata, score_data

    with open(file, 'wt') as zfile:
        for event_key, match_key, zdata, score_data in _match_path_data():
            match_data = {'event': event_key,
                          'match': match_key,
                          'zebra': zdata,
                          'score': score_data}
            zfile.write(json.dumps(match_data) + '\n')


def download_events(key, file):
    events = zebra.tba.get_events(key)
    with open(file, 'wt') as jfile:
        json.dump(events, jfile)


def filter_by_event(event_key, input_file, output_file):
    """Copies all matches from a specified event to a different file."""
    print(f'Scanning {input_file} for data matching {event_key}.')
    with open(input_file) as ifile, open(output_file, 'wt') as ofile:
        output_lines = 0
        for line in ifile:
            line_json = json.loads(line)
            if (line_json['event'] == event_key and
                line_json['zebra'] is not None):
                ofile.write(line)
                output_lines += 1
    print(f'Wrote {output_lines} lines to {output_file}.')


def read_field(field_file):
    with open(field_file) as ffile:
        return json.load(ffile)


def setup_parser():
    """Setup module for command-line use."""
    desc = (
        'Tools for obtaining and analyzing Zebra motion capture data '
        'collected at FIRST Robotic Competition (FRC) events.')
    parser = argparse.ArgumentParser(description=desc)
    subparsers = parser.add_subparsers()

    download_match_subparser = subparsers.add_parser(
        'download-match',
        description='Download match data from TBA')
    download_match_subparser.add_argument(
        'key', help='TBA district key or 4-digit year')
    download_match_subparser.add_argument(
        'file', help='Match data will be saved to this file.')
    download_match_subparser.add_argument('--max-no-path-matches',
        type=int, default=5,
        help=('Minimum number of matches checked for path data '
              'before skipping event'))
    download_match_subparser.set_defaults(func=download_match)

    download_events_subparser = subparsers.add_parser(
        'download-events',
        description='Download event data from TBA')
    download_events_subparser.add_argument(
        'key', help='TBA district key or 4-digit year')
    download_events_subparser.add_argument(
        'file', help='Match data will be saved to this file.')
    download_events_subparser.set_defaults(func=download_events)

    filter_subparser = subparsers.add_parser(
        'filter',
        description='Filter downloaded path data')
    filter_subparser.add_argument(
        'event_key', help='TBA event key')
    filter_subparser.add_argument(
        'input_file', help='Input JSONL file')
    filter_subparser.add_argument(
        'output_file', help='Output JSON file')
    filter_subparser.set_defaults(func=filter_by_event)

    return parser


if __name__ == '__main__':
    parser = setup_parser()
    args = parser.parse_args()
    subcommand = args.func
    del args.func
    subcommand(**vars(args))
