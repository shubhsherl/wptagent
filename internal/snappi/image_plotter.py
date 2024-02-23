from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

COLORS = {
    'image': ['r', 'g'],
    'text': ['b', 'm'],
}

def plot_rects(rects, output_filepath):
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1366)
    ax.set_ylim(0, 768)
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

        if has_multiple_paint_events:
            domnodeid_annotations = ", ".join([f"{event['domNodeId']}" for event in events])
            ax.annotate(domnodeid_annotations, (rect["x"] + rect["width"] - 3, rect["y"] + 3), color='black', fontsize=6, ha='right', va='bottom')
        else:
            ax.annotate(f"{events[0]['domNodeId']}", (rect["x"] + rect["width"] - 3, rect["y"] + 3), color='black', fontsize=6, ha='right', va='bottom')

    plt.savefig(output_filepath)