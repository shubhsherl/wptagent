from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

COLORS = {
    'image': ['r', 'g'],
    'text': ['b', 'm'],
}

def plot_rects(rects, output_filepath):
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1200)
    ax.set_ylim(0, 1000)
    ax.invert_yaxis()

    for rect_data in rects:
        x, y, width, height = rect_data["x"], rect_data["y"], rect_data["width"], rect_data["height"]
        events = rect_data["events"]

        colors = COLORS[events[0]['type']]

        rect = {"x": x, "y": y, "width": width, "height": height}
        area = rect_data["area"]

        color = colors[0]
        has_multiple_paint_events = False

        if len(events) > 1:
            color = colors[1]
            has_multiple_paint_events = True

        ax.add_patch(Rectangle((rect["x"], rect["y"]), rect["width"], rect["height"], linewidth=1, edgecolor=color, facecolor='none'))

        if color == 'g' and has_multiple_paint_events:
            timestamp_annotations = ", ".join([f"{event['timestamp']:.0f}" for event in events])
            ax.annotate(timestamp_annotations, (rect["x"] + rect["width"] / 2, rect["y"] + rect["height"] / 2), color=color, weight='bold', fontsize=8, ha='center', va='center')
        elif color == 'r':
            ax.annotate(f'{events[0]["timestamp"]:.0f}', (rect["x"] + rect["width"] / 2, rect["y"] + rect["height"] / 2), color=color, weight='bold', fontsize=8, ha='center', va='center')

    plt.savefig(output_filepath)
