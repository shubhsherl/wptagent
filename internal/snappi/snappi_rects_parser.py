import json
from collections import defaultdict

def is_image_paint_timing_event(event):
    if "args" not in event or "data" not in event["args"]:
        return False

    event_data = event["args"]["data"]
    required_keys = ["visualX", "visualY", "visualWidth", "visualHeight", "visualSize"]

    return (
        event.get("name") == "ImagePaint::Timing" and
        "imageUrl" in event_data and
        all(key in event_data for key in required_keys) and
        event.get("ph") == "R"
    )

def parse_rectangles(trace_data, navigation_start_ts):
    rects_dict = defaultdict(list)
    rects_list = []

    for event in trace_data["traceEvents"]:
        if is_image_paint_timing_event(event):
            event_data = event["args"]["data"]

            rect = {
                "x": event_data["visualX"],
                "y": event_data["visualY"],
                "width": event_data["visualWidth"],
                "height": event_data["visualHeight"]
            }
            rect["area"] = rect["width"] * rect["height"]

            relative_ts = (int(event["ts"]) - navigation_start_ts) / 1000
            event_data.update({"timestamp": round(relative_ts, 2)})

            event_info = {
                "imageUrl": event_data["imageUrl"],
                "timestamp": event_data["timestamp"],
                "size": event_data["visualSize"]
            }

            rect_key = tuple(rect.items())
            rects_dict[rect_key].append(event_info)

    for rect_key, events in rects_dict.items():
        unique_events = []
        for event in events:
            if not any(e["imageUrl"] == event["imageUrl"] and e["size"] == event["size"] for e in unique_events):
                unique_events.append(event)

        min_timestamp = min(event["timestamp"] for event in unique_events)
        rect_obj = {
            **dict(rect_key),
            "min_timestamp": min_timestamp,
            "events": unique_events
        }

        rects_list.append(rect_obj)

    return sorted(rects_list, key=lambda x: x["min_timestamp"])