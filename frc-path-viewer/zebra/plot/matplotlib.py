"""Matplotlib plotting punction for Zebra path data.
"""
import matplotlib
import matplotlib.pyplot as plt


def plot(zpath, field, figsize=(16, 9)):

    def _add_line(axes, xs, ys, color):
        axes.add_artist(matplotlib.lines.Line2D(xs, ys, color=color))

    fig, ax = plt.subplots(figsize=figsize)
    fig.tight_layout()
    ax.set_axis_off()

    for line in field['lines']:
        color = field['colors'][line['class']]
        _add_line(ax, line['x'], line['y'], color)

    def _plot_path(axes, xs, ys, pcolor, lbl):
        axes.plot(xs, ys, color=pcolor, label=lbl )
        
    path_colors = ['darkblue', 'royalblue', 'deepskyblue',
                   'darkred', 'crimson', 'lightcoral']
    
    labels = zpath.blue + zpath.red
    for idx in range(6):
        _plot_path(ax, zpath.paths[2*idx], zpath.paths[2*idx + 1],
                   path_colors[idx], labels[idx])
        
    ax.set_aspect('equal')
    ax.set_xlim(-1, 55)
    ax.set_ylim(-1, 27)
    title = zpath.match
    ax.legend()
    ax.set_title(title)
