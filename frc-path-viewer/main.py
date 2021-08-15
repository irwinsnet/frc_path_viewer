"""

Dev serve command on Windows
`python -m bokeh serve --dev --show zviewer`
"""
import os.path
import re
import sys

import bokeh.io as io
import bokeh.layouts as layouts
import bokeh.models as models
import bokeh.plotting as plotting
import pandas as pd

app_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, app_path)
import zebra.path
import zebra.data

PLOT_HEIGHT = 500
VIDEO_HEIGHT = 135
VIDEO_WIDTH = 240
INITIAL_START_TIME = 150
INITIAL_SPAN_LENGTH = 15
PLOT_X_RANGE = (-2, 60)
X_SIZE = 25
BASE_TBA_URL = 'https://www.thebluealliance.com/'
BASE_YOUTUBE_URL = 'https://youtube.com'

class ZebraViewer():
    positions = ['blue1', 'blue2', 'blue3', 'red1', 'red2', 'red3']
    path_colors = ['darkblue', 'royalblue', 'deepskyblue',
                   'darkred', 'crimson', 'lightcoral']

    def __init__(self):
        data_path = os.path.abspath(
            os.path.join(app_path, 'data', '2020pnw.jsonl'))
        self.data = zebra.path.Competitions(data_path)
        field_path = os.path.abspath(
            os.path.join(app_path, 'data', 'field2020.json'))
        self.field = zebra.data.read_field(field_path)
        events = pd.read_json(os.path.abspath(
            os.path.join(app_path, 'data', '2020events.json')))
        self.event_data = events[events.key.isin(self.data.events)]
        self.event = self.data.events[0]
        self.level = 'qm'
        self.level_matches = self.get_level_matches()
        self.match = self.level_matches[0][0]
        self.match_data = self.data[self.match]
        self.teams = self.match_data.blue + self.match_data.red
        self.start_time = 0
        self.end_time = INITIAL_START_TIME
        self.span = INITIAL_SPAN_LENGTH
        self.figure = None
        self.title_div = None
        self.video_row = None
        self.team_div = None

        self.initialize_widgets()
        self.datasources = [
            {'path': models.ColumnDataSource(data={'xs': [], 'ys': []}),
             'pos': models.ColumnDataSource(data={'x': [], 'y': []}),
             'color': self.path_colors[idx]}
            for idx in range(6)]
        self.update_datasources()
        self.register_widget_callbacks()

    def get_level_matches(self):
        """Returns ordered list of matches for the current comp. level.
        
        Return value is a list of tuples, i.e.,
        [('1', '2020wasno_qm1'),
         ('2', '2020wasno_qm2'),
         ('3', '2020wasno_qm3'),
         ...]
        """
        # All matches for current event
        matches = self.data.matches(self.event)
        # Extract matches for current level
        ptn = re.compile(f'^[^_]+_{self.level}([^_]+)$')
        matches = [re.search(ptn, mtch_str) for mtch_str in matches]
        matches = list(filter(lambda x: x is not None, matches))
        # Create tuples and sort list
        matches = [(match[0], match[1]) for match in matches]
        if self.level == 'qm':
            matches = sorted(matches, key=lambda x: int(x[1]))
        else:
            matches = sorted(matches, key=lambda x: x[1])
        return matches

    def initialize_widgets(self):
        self.event_selector = models.Select(
            title='Select Competition',
            options=[(evt.key, evt.name + ' | ' + evt.end_date)
                     for evt in self.event_data.itertuples()],
            value=self.event)

        self.level_selector = models.Select(
            title='Select Competition Level',
            options=[
                ('qm', 'Qualification'),
                ('qf', 'Quarterfinals'),
                ('sf', 'Semifinals'),
                ('f', 'Finals')],
            value=self.level
        )

        self.match_selector = models.Select(
            title='Select Match',
            options=self.level_matches,
            value=self.match)

        self.time_select_type = models.CheckboxButtonGroup(
            labels=['All', 'Span', 'Range'],
            active=[0])

        self.time_range_selector = models.RangeSlider(
            start=0, end=160, step=1,
            value=(0, 150),
            title='Select Time Range in Seconds')
        self.time_range_selector.visible = False

        self.time_span_selector = models.Slider(
            start=self.start_time, end=self.end_time, step=1,
            value=15,
            title='Select Time Span End')
        self.time_span_selector.visible = False

        self.span_length_spinner = models.Spinner(
            title='Span Length',
            low=5, high=55, step=10, value=15)
        self.span_length_spinner.visible = False
        

    def update_datasources(self):
        self.match = self.match_selector.value
        self.match_data = self.data[self.match]
        self.teams = self.match_data.blue + self.match_data.red
        start = self.start_time * 10
        end = self.end_time * 10
        for idx in range(6):
            self.datasources[idx]['match'] = self.match_selector.value
            self.datasources[idx]['position'] = self.positions[idx]
            self.datasources[idx]['team'] = self.teams[idx]
            self.datasources[idx]['path'].data = {
                'xs': self.match_data.paths[2*idx][start:end],
                'ys': self.match_data.paths[2*idx+1][start:end]}
            end_idx = -1
            self.datasources[idx]['pos'].data = {
                'x': [self.match_data.paths[2*idx][start:end][end_idx]],
                'y': [self.match_data.paths[2*idx+1][start:end][end_idx]]}
            self.datasources[idx]['path_len'] = self.match_data.paths.shape[1]

    def get_page_title(self):
        evt = self.event_data[self.event_data.key == self.event].iloc[0]
        tba_url = 'https://www.thebluealliance.com/event/' + self.event
        tba_link = f'<a href="{tba_url}" target="_blank">{evt.at["name"]}</a>'
        title = (f'<h2>FRC Robot Paths - {tba_link}</h2>'
                 f'<h3>{evt.city}, {evt.state_prov}, {evt.country}:  '
                 f'{evt.start_date} to {evt.end_date}</h3>')
        return title

    def get_plot_title(self):
        levels = {'qm': 'Qualification',
                  'qf': 'Quarterfinals',
                  'sf': 'Semifinals',
                  'f': 'Finals'}
        label = [option[1] for option in self.match_selector.options
                 if option[0] == self.match_selector.value][0]
        return f'{levels[self.level]} Match {label}'

    def update_plot_annotations(self):
        self.match = self.match_selector.value
        self.match_data = self.data[self.match]
        self.teams = self.match_data.blue + self.match_data.red
        if self.title_div is not None:
            self.title_div.text = self.get_page_title()
        if self.video_row is not None:
            self.update_videos()
        if self.team_div is not None:
            self.team_div.text = self.get_team_links()
        if self.figure is not None:
            # Update plot title
            self.figure.title.text = self.get_plot_title()
            # Update Legend labels with new team numbers
            for idx, item in enumerate(self.figure.legend.items):
                self.figure.legend.items[idx] = models.LegendItem(
                    label=self.teams[idx],
                    renderers = item.renderers,
                    index=idx)

    def _event_selector_callback(self, new):
        self.event = new
        self.level_matches = self.get_level_matches()
        self.match_selector.options = self.level_matches
        self.match_selector.value = self.level_matches[0][0]
        self._match_selector_callback(self.match_selector.value)
        self.update_datasources()

    def _level_selector_callback(self, new):
        self.level = new
        self.level_matches = self.get_level_matches()
        self.match_selector.options = self.level_matches
        self.match_selector.value = self.level_matches[0][0]
        self._match_selector_callback(self.match_selector.value)
        self.update_datasources()

    def _match_selector_callback(self, new):
        self.match = new
        self.match_data = self.data[self.match]
        self.update_plot_annotations()
        self.update_datasources()

    def _time_select_type_callback(self, old, new):
        # Ensure only one option can be selected at at time.
        if len(new) == 0:
            self.time_select_type.active = old
        if len(new) - len(old) == 1:
            self.time_select_type.active = list(set(new) - set(old))

        # Set visibility of time widgets
        self.time_range_selector.visible = (
            self.time_select_type.active[0] == 2)
        span_active = self.time_select_type.active[0] == 1
        self.span_length_spinner.visible = span_active
        self.time_span_selector.visible = span_active

        # Update plot
        if self.time_select_type.active[0] == 0:
            self.start_time = 0
            self.end_time = 160
            self.time_range_selector.value = (0, 160)
            self.update_datasources()
        if self.time_select_type.active[0] == 1:
            self._time_span_selector_callback(self.time_span_selector.value)
        if self.time_select_type.active[0] == 2:
            self._time_range_selector_callback(self.time_range_selector.value)

    def _time_range_selector_callback(self, value):
        self.start_time = value[0]
        self.end_time = value[1]
        self.update_datasources()

    def _time_span_selector_callback(self, value):
        self.end_time = value
        self.start_time = max(0, value - self.span)
        self.update_datasources()

    def _spen_length_spinner_callback(self, value):
        self.span = value
        self.start_time = max(0, self.end_time - self.span)
        self.update_datasources()

    def register_widget_callbacks(self):
        self.event_selector.on_change(
            'value',
            lambda attr, old, new: self._event_selector_callback(new))
        self.level_selector.on_change(
            'value',
            lambda attr, old, new: self._level_selector_callback(new))
        self.match_selector.on_change(
            'value',
            lambda attr, old, new: self._match_selector_callback(new))
        self.time_select_type.on_change(
            'active',
            lambda attr, old, new: self._time_select_type_callback(old, new))
        self.time_range_selector.on_change(
            'value',
            lambda attr, old, new: self._time_range_selector_callback(new)
        )
        self.time_span_selector.on_change(
            'value',
            lambda attr, old, new: self._time_span_selector_callback(new)
        )
        self.span_length_spinner.on_change(
            'value',
            lambda attr, old, new: self._spen_length_spinner_callback(new)
        )

    def draw_paths(self, height=350):
        fig = plotting.figure(title=self.match_selector.value,
                            match_aspect=True,
                            plot_height=height, plot_width=height*2,
                            x_axis_label = 'Feet', y_axis_label = 'Feet',
                            x_range=PLOT_X_RANGE)
        fig.xgrid.grid_line_color = None
        fig.ygrid.grid_line_color = None

        # Draw field
        for line in self.field['lines']:
            color = self.field['colors'][line['class']]
            fig.line(line['x'], line['y'], line_color=color)

        for ds in self.datasources:
            fig.line(x='xs', y='ys', source=ds['path'],
                line_color=ds['color'], legend_label=ds['team'])
            fig.circle_x(x='x', y='y', size=X_SIZE,
                  source=ds['pos'], color=ds['color'], fill_color=None)
        fig.legend.click_policy = 'hide'
        fig.title.text = self.get_plot_title()
        self.figure = fig
        return fig

    def update_videos(self):
        def _create_video_frame(key, height, width):
            frame_text = (
            f'<iframe width="width" height="height" id="key"'
            f'src="{BASE_YOUTUBE_URL}/embed/{key}"></iframe>')
            return models.Div(text=frame_text)

        video_keys = [video['key']
                      for video in self.match_data.score['videos']]
        video_divs = [_create_video_frame(key, VIDEO_HEIGHT, VIDEO_WIDTH)
                      for key in video_keys]
        self.video_row.children = video_divs

    def get_team_links(self):
        urls = [f'{BASE_TBA_URL}/team/{team[3:]}' for team in self.teams]
        links = [f'<a href="{tm[0]}" target="_blank">{tm[1]}</a>'
                 for tm in zip(urls, self.teams)]
        list_items = [f'<li><h3>{link}</h3></li>' for link in links]
        tm_title = '<h2>Additional Team Info:</h2>'
        tm_list = tm_title + '<ul>' + ''.join(list_items) + '</ul>'
        return tm_list


    def build_layout(self, height):
        # Top Row
        self.title_div = models.Div(text=f'{self.get_page_title()}')

        # Middle Row
        match_select_row = layouts.row(self.event_selector,
                                       self.level_selector,
                                       self.match_selector)
        time_select_row = layouts.row(self.time_select_type,
                                      self.time_range_selector,
                                      self.span_length_spinner,
                                      self.time_span_selector)
        plot_layout = layouts.column(self.draw_paths(height),
                                     match_select_row,
                                     time_select_row)
        self.team_div = models.Div(text=self.get_team_links())
        description = """
            <h2>Tips</h2>
            <ul>
            <li>Click on the team numbers in the legend to turn paths on and off.</li>
            <li>Use the tools in the tool bar to pan, zoom, and save image files.</li>
            <li>If there is no position data for a robot, it plots in the lower left corner (i.e., 0, 0).</li>
            <li>Try out the <i>Span</i> and <i>Range</i> options to view a portion of a robot's path.</li>
            </ul>
        """
        description_div = models.Div(text=description)

        middle_row = layouts.row(plot_layout,
                                 layouts.column(self.team_div, description_div))


        # Bottom Row
        about = """
            <h2>About this Page</h2>
            <p>This page displays the paths of FIRST Robotics Competition (FRC)
            robots during two robotics competitions that occurred in the
            Pacific Northwest in early 2020 (immediately before the rest of the
            season was canceled due to the pandemic).</p>
            <p>This visualization tool was built using Python and the
            <a href="https://docs.bokeh.org/" target="_blank">Bokeh package.</a></p>
            <p>The tracking system that made this possible was provided by Zebra.
            <a href="https://www.zebra.com/us/en/blog/posts/2020/enabling-first-robotics-students-to-explore-their-edge.html" target="_blank">
            This blog post</a> provides additional information.</p>
            <a href="https://www.firstinspires.org/" target="_blank"><h3>Learn more about FIRST</h3></a>
        """
        about_div = models.Div(text=about)
        self.video_row = layouts.row()
        self.update_videos()
        video_section = layouts.column(
            models.Div(text='<h3>Match Videos</h3>'),
            self.video_row,
            about_div)

        main_layout = layouts.column(self.title_div,
                                     middle_row,
                                     video_section)
        return main_layout


zview = ZebraViewer()
io.curdoc().add_root(zview.build_layout(PLOT_HEIGHT))
io.curdoc().title = 'FRC Zebra Path Viewer'
