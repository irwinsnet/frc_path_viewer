"""
A Bokeh application for viewing FRC Robot path data.

The data files were created from information downloaded from The Blue
Alliance (TBA).

The app depends on the zebra.path module. The zebra.path module reads
data from disk and converts the data into appropriate data structures.

Created by Stacy Irwin, 16 Aug 2021

Module Contents:
    ZebraViewer:    Class that contains the Bokeh application code.
"""

import json
import os
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

### Module Parameters
# Title of HTML page containing viewer app.
PAGE_TITLE = 'FRC Zebra Path Viewer'
# Name of JSONL data file. Each line is a JSON object, with path and score data
#   downloaded from TBA.
PATH_FILE = '2020pnw.jsonl'
# Name of JSON data file with coordinates for field
#   markings. This data is plotted as lines in the path plot.
FIELD_FILE = 'field2020.json'
# Name of JSON file that contains event data downloaded from TBA.
EVENTS_FILE = '2020events.json'
# Initial setting of right slider in range select slider. In seconds.
INITIAL_END_TIME = 150
# Initial setting of span_length spinner, in seconds.
INITIAL_SPAN_LENGTH = 15
# Height of main plot, in pixels.
PLOT_HEIGHT = 500
# Range of main plot's x-axis.
PLOT_X_RANGE = (-2, 60)
# Size of X-glyph that represents each robot's current position.
X_SIZE = 25
# List of CSS colors names used to draw robot paths. Order of colors is
#   blue1 through blue3, then red1 through red3.
PATH_COLORS = ['darkblue', 'royalblue', 'deepskyblue',
                'darkred', 'crimson', 'lightcoral']
# List of names of the alliance stations. 
STATION_NAMES = ['blue1', 'blue2', 'blue3', 'red1', 'red2', 'red3']
# Height of match video iframes.
BASE_TBA_URL = 'https://www.thebluealliance.com/'
# Width of match video iframes
VIDEO_HEIGHT = 135
# Base URL for Youtube
VIDEO_WIDTH = 240
# Base URL for TBA
BASE_YOUTUBE_URL = 'https://youtube.com'


class ZebraViewer():
    """Contains most of the functionality of the Bokeh application.

    Attributes:
        get_level_matches(): Returns a tuple of matches for the current
            competition level, i.e., qualification, semi-finals, etc.
        initialize_widgets(): Creates and initializes page controls,
            such as the mach selector, event selector, time ranges, etc.
        update_datasource(): Updates the Bokeh `ColumnDataSource object
            that contains the data that is plotted.
        get_page_title(): Gets a page title containing current event data.
        get_plot_title(): Gets a string describing the selected match.
        update_plot_annotations(): Updates all items on page that are
            not part of the Bokeh plot, including Youtube video
            iframes, page title, team info hyperlinks, etc.
        _{widget_name}_callback(): Callback functions that are
            triggered when the user changes a widget setting.
        register_widget_callbacks(): Links each callback function to
            its respective widget.
        draw_paths(): Draws the path plot using Bokeh drawing functions.
        update_videos(): Updates the iframes containing youtube videos.
        get_team_links(): Gets list of hyperlinks for FRC teams playing
            in the currently selected match.
        build_layout(): Assembles the page layout. This is the only
            method that is called externally.
    """
    def __init__(self):
        """Initializes the ZebraViewer object. Takes no parameters."""
        # Load data from disk
        def _join(*args):
            return  os.path.abspath(os.path.join(*args))

        self.data = zebra.path.Competitions(_join(app_path, PATH_FILE))
        with open(_join(app_path, FIELD_FILE)) as field_file:
            self.field = json.load(field_file)

        # Set attributes
        events = pd.read_json(_join(app_path, EVENTS_FILE))
        self.event_data = events[events.key.isin(self.data.events)]
        self.event = self.data.events[0]
        self.level = 'qm'
        self.level_matches = self.get_level_matches()
        self.match = self.level_matches[0][0]
        self.match_data = self.data[self.match]
        self.teams = self.match_data.blue + self.match_data.red
        self.start_time = 0
        self.end_time = INITIAL_END_TIME
        self.span = INITIAL_SPAN_LENGTH
        self.figure = None
        self.title_div = None
        self.video_row = None
        self.team_div = None

        # Initialize class attributes
        self.initialize_widgets()
        self.datasources = [
            {'path': models.ColumnDataSource(data={'xs': [], 'ys': []}),
             'pos': models.ColumnDataSource(data={'x': [], 'y': []}),
             'color': PATH_COLORS[idx]}
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
        """Initializes Bokeh Widgets used to update the plot.
        
        See the respective _callback functions for additional
        information on each widget.
        """
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
        """Updates plot data when a new match is selected.

        The ZebraViewer.datasources object is a list of six dictionaries.
        The data 'path' and 'pos' keys contain Bokeh ColumnDataSource
        objects that are linked to the plot. The plot is automatically
        updated when the data is the ColumnDataSource objects is
        updated.
        """
        self.match = self.match_selector.value
        self.match_data = self.data[self.match]
        self.teams = self.match_data.blue + self.match_data.red
        start = self.start_time * 10
        end = self.end_time * 10
        for idx in range(6):
            self.datasources[idx]['match'] = self.match_selector.value
            self.datasources[idx]['position'] = STATION_NAMES[idx]
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
        """Generates headers at the top of the HTML page.
        
        The headers contain information about the FRC competition.

        Returns: A string containing the HTML header tags.
        """
        evt = self.event_data[self.event_data.key == self.event].iloc[0]
        tba_url = 'https://www.thebluealliance.com/event/' + self.event
        tba_link = f'<a href="{tba_url}" target="_blank">{evt.at["name"]}</a>'
        title = (f'<h2>FRC Robot Paths - {tba_link}</h2>'
                 f'<h3>{evt.city}, {evt.state_prov}, {evt.country}:  '
                 f'{evt.start_date} to {evt.end_date}</h3>')
        return title

    def get_plot_title(self):
        """Generates plot tile containing a human readable match title.
        
        Returns: A string containing the plot title.
        """
        levels = {'qm': 'Qualification',
                  'qf': 'Quarterfinals',
                  'sf': 'Semifinals',
                  'f': 'Finals'}
        label = [option[1] for option in self.match_selector.options
                 if option[0] == self.match_selector.value][0]
        return f'{levels[self.level]} Match {label}'

    def update_plot_annotations(self):
        """Updates everything that is not part of the main plot.

        Updates main page title, team info links, Youtube video
        iframes, plot tile, and plot legend -- basically everything that
        is not linked to the Bokeh ColumnDataSource object.
        """
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
        """Changes the FRC competition that is selected.

        Causes the plot to be redrawn.

        Args:
            new: The TBA event key, for example, 2020waspo.        
        """
        self.event = new
        self.level_matches = self.get_level_matches()
        self.match_selector.options = self.level_matches
        self.match_selector.value = self.level_matches[0][0]
        self._match_selector_callback(self.match_selector.value)
        self.update_datasources()

    def _level_selector_callback(self, new):
        """Updates the contents of the match selector widget.

        Causes the plot to be redrawn.

        Args:
            new: A string. Either 'qm' for qualification matches, 'qf'
                 for quarterfinals matches, 'sf' for semi-finals
                 matches, or 'f' for finals matches.
        """
        self.level = new
        self.level_matches = self.get_level_matches()
        self.match_selector.options = self.level_matches
        self.match_selector.value = self.level_matches[0][0]
        self._match_selector_callback(self.match_selector.value)
        self.update_datasources()

    def _match_selector_callback(self, new):
        """Updates the plot to display a new match.
        
        Args:
            new: The TBA match key that identifies the match. For
                 example, '2020wasno_qm1' is the first qualification
                 match for the Glacier Peak event.
        """
        self.match = new
        self.match_data = self.data[self.match]
        self.update_plot_annotations()
        self.update_datasources()

    def _time_select_type_callback(self, old, new):
        """Controls with time control widgets are visible.

        Args:
            old: A list containing the active, i.e., pushed-in,
            selector buttons. If 0, the entire robot path for the entire
            match is drawn. If 1, the time span controller is active.
            If 2, the time range controller is active.
        """
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
        """Changes the start and end times of the visible robot path.

        Causes the plot to be redrawn.

        Args:
        Value: a tuple containing the positions of the left and right
            span controls. In seconds elapsed since the beginning of the
            match.
        """
        self.start_time = value[0]
        self.end_time = value[1]
        self.update_datasources()

    def _time_span_selector_callback(self, value):
        """Specifies the end time of the path that is plotted on screen.

        The end time is in seconds elapsed since the start of the match.
        Causes the plot to be redrawn.

        Args:
            value: The updated value of the span control, in seconds.        
        """
        self.end_time = value
        self.start_time = max(0, value - self.span)
        self.update_datasources()

    def _spen_length_spinner_callback(self, value):
        """Sets length of path displayed in plot, in seconds.

        Causes the plot to be redrawn.
        Args:
            The new value of the spinner, in seconds.
        """
        self.span = value
        self.start_time = max(0, self.end_time - self.span)
        self.update_datasources()

    def register_widget_callbacks(self):
        """Links each callback function to its respective widget."""
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
        """Draws the path plot using Bokeh drawing functions.
        Args:
            height: Plot height in pixels. Plot width will be twice the
                    plot height. Default is 350.

        Returns: A Bokeh Figure object.
        """
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
        """Updates the iframes containing youtube videos."""
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
        """Gets list of hyperlinks for teams playing in current match."""
        urls = [f'{BASE_TBA_URL}/team/{team[3:]}' for team in self.teams]
        links = [f'<a href="{tm[0]}" target="_blank">{tm[1]}</a>'
                 for tm in zip(urls, self.teams)]
        list_items = [f'<li><h3>{link}</h3></li>' for link in links]
        tm_title = '<h2>Additional Team Info:</h2>'
        tm_list = tm_title + '<ul>' + ''.join(list_items) + '</ul>'
        return tm_list

    def build_layout(self, height):
        """Builds the layout for the HTML page.

        This is the only method that is called externally.

        Args:
            height: The plot height. The plot width will be set from the
            plot height, with a 1:2 height to width ratio.

        Returns:
            a Bokeh column layout object, which will be added to the HTML
            page's document root.
        """
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
            <a href="https://docs.bokeh.org/" target="_blank">Bokeh package.</a>
            The code for this project is
            <a href="https://github.com/irwinsnet/frc_path_viewer" target = "_blank">
            available on Github</a>.</p>
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
io.curdoc().title = PAGE_TITLE
