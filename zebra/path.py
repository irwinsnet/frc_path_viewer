"""Tools for analyzing Zebra motion capture data from FRC Competitions.
"""
import argparse
import json
import pickle

import numpy as np
import pandas as pd


class Match():
    """Zebra path data and detailed scores for a single FRC match.

    Constructor Args:
        match_text: A single line of JSON text from the data file
            generated by the `zebra.download_data()` function. The JSON
            text consists of a dictionary with four keys: 'event',
            'match', 'zebra', and 'score'.
    """
    def __init__(self, match_json):
        if isinstance(match_json, str):
            match_json = json.loads(match_json)
        self.event = match_json['event']
        self.match = match_json['match']
        self.blue = [team['team_key']
                     for team in match_json['zebra']['alliances']['blue']]
        self.red = [team['team_key']
                    for team in match_json['zebra']['alliances']['red']]
        paths = []
        for alliance in ['blue', 'red']:
            for team in match_json['zebra']['alliances'][alliance]:
                for axis in ['xs', 'ys']:
                    paths.append(team[axis])
        self.paths = np.array(paths)
        self.times = np.array(match_json['zebra']['times'])
        self.score = match_json['score']
        
        teams_list = self.blue + self.red
        stations = ['blue1', 'blue2', 'blue3', 'red1', 'red2', 'red3']
        self.teams = {}
        for idx, tm in enumerate(teams_list):
            x_path_idx = 2*idx
            y_path_idx = 2*idx + 1
            team_data = self._scan_path(self.paths[x_path_idx],
                                        self.paths[y_path_idx])
            team_data['xs'] = self.paths[x_path_idx]
            team_data['ys'] = self.paths[y_path_idx]
            team_data['station'] = stations[idx]
            self.teams[tm] = team_data

    @staticmethod
    def _scan_path(xs, ys):
        if all([x is None for x in xs]) and all([y is None for y in ys]):
            return {'start': None, 'end': None, 'n': 0, 'missing': None}
        
        missing_coords = []
        for t, coords in enumerate(zip(xs, ys)):
            if coords[0] is None or coords[1] is None:
                missing_coords.append(t)
        
        for t, coords, in enumerate(zip(xs, ys)):
            if coords[0] is not None and coords[1] is not None:
                start = (coords[0], coords[1], t)
                break
        for t, coords, in enumerate(zip(np.flip(xs), np.flip(ys))):
            if coords[0] is not None and coords[1] is not None:
                end = (coords[0], coords[1], len(xs) - t)
                break
                
        return {'start': start,
                'end': end,
                'n': len(xs) - len(missing_coords),
                'missing': missing_coords}
                

class Competitions():
    """Zebra position data and scores for one or more FRC competitions.

    A `zebra.Competitions` object contains `zebra.Match` objects for
    one or more competitions. Use standard Python indexing notation
    (i.e., square brackets) to access individual `zebra.Match` object.
    The index value can be a positive integer or a Blue Alliance match
    key.
    For example:
        ```
        zc = zebra.Competitions('data_file.jsonl')
        zmatch1 = zc['2020wasno_qm1']

        num_matches = len(zc)
        zmatch2 = zc[num_matches - 1]
        ```
    """
    def __init__(self, file):
        """Initializes a zebra.Competitions object.

        The Competitions object is initialized from a JSONL text file
        produced by the `zebra.download()` function. See the
        documentation for `zebra.download()` for additional information
        on the format of the JSONL file.

        Args:
            file: String containing path to zebra position data. The
            file path should be suitable for Python's built-in `open()`
            function.
        """
        self.event_summary = None
        self.zmatches = None
        self._read_file(file)
        self.mindex = {zm.match: idx for idx, zm in enumerate(self.zmatches)}
        self.events = list(set([zmatch.event for zmatch in self.zmatches]))
        
    def __getitem__(self, idx):
        """Retrieves Match object from integer or TBA match key."""
        if isinstance(idx, int):
            return self.zmatches[idx]
        else:
            return self.zmatches[self.mindex[idx]]
    
    def __len__(self):
        """Returns number of matches in Competitions object."""
        return len(self.zmatches)
    
    def _read_file(self, file):
        """Reads data from JSONL source file."""
        # Convert file data to JSON, assumes file not too big for memory.
        with open(file) as jlfile:
            self.paths = [json.loads(line) for line in jlfile]
        
        # Create Event Summary DF, shows all events checked for zebra data
        events = [path['event'] for path in self.paths]
        matches = [path['match'] for path in self.paths]
        zebra = [ 0 if path['zebra'] is None else 1 for path in self.paths]
        self.event_summary = (
            pd.DataFrame({'event': events, 'match': matches, 'path': zebra})
            .groupby('event')
            .agg(path_matches=('path', 'sum'))
        )
        
        # Remove matches with no Zebra path data
        self.zmatches = [Match(path) for path in self.paths
                        if path['zebra'] is not None]

    def write_file(self, file_path):
        with open(file_path, 'wb') as pfile:
            pickle.dump(self, pfile)


    def matches(self, event):
        return [zmatch.match for zmatch in self.zmatches
                if zmatch.event == event]


def setup_parser():
    """setup module for command line use."""
    desc = (
        'Converts an FRC data JSONL file that was downloaded by '
        'zebra/data.py to a zebra.paths.Competitions object and '
        'saves it in a pickle file.'
    )
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('INPUT_FILE', help='JSONL formated FRC data file.')
    parser.add_argument('OUTPUT_FILE', help='Ouput pickle file.')
    return parser


if __name__ == '__main__':
    parser = setup_parser()
    args = parser.parse_args()
    zcomp = Competitions(args.INPUT_FILE)
    zcomp.write_file(args.OUTPUT_FILE)