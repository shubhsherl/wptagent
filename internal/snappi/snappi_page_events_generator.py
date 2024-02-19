import json

def match_frame_value(event, ns_frame, event_name, found_events):
    event_frame = event["args"].get("frame", None)
    if event_frame is None:
        event_data = event["args"].get("data", {})
        event_frame = event_data.get("frame", None)

    if event_frame == ns_frame or (event_frame is None and event_name not in found_events):
        found_events[event_name] = {
            "event": event,
            "matched": event_frame == ns_frame
        }

def assemble_final_events(found_events):
    final_events = {}
    for event_name, event_info in found_events.items():
        if event_info["matched"]:
            final_events[event_name] = event_info["event"]
        elif event_name not in final_events:
            final_events[event_name] = event_info["event"]

    return final_events

def add_navigation_start_event_info(event, result):
    navigation_start_data = event["args"]["data"]
    result["page_events"].append({
        "event_name": "navigationStart",
        "documentLoaderUrl": navigation_start_data["documentLoaderURL"],
        "isLoadingMainFrame": navigation_start_data["isLoadingMainFrame"],
        "navigationId": navigation_start_data["navigationId"],
        "frame": event["args"]["frame"],
        "timestamp": 0
    })

def add_other_event_info(event_name, event, navigation_start_ts, result):
    event_frame = event["args"].get("frame", None)
    if event_frame is None:
        event_data = event["args"].get("data", {})
        event_frame = event_data.get("frame", None)

    event_data = {
        "event_name": event_name,
        "timestamp": (event["ts"] - navigation_start_ts) / 1000,
        "frame": event_frame
    }
    result["page_events"].append(event_data)

def generate_page_events(trace_data, rects, navigation_start_event, event_names):
    largest_area = 0
    snappi_lcp = None
    longest_event = None
    navigation_start_ts = navigation_start_event["ts"]

    found_events = {}

    for event in trace_data["traceEvents"]:
        event_name = event.get("name")

        if event_name in event_names and event["ts"] > navigation_start_ts:
            ns_frame = navigation_start_event["args"]["frame"]
            match_frame_value(event, ns_frame, event_name, found_events)

    found_events = assemble_final_events(found_events)
    found_events["navigationStart"] = navigation_start_event

    result = {"rects": [], "page_events": []}

    for rect_data in rects:
        rect = [rect_data["x"], rect_data["y"], rect_data["width"], rect_data["height"]]
        events = rect_data["events"]
        area = rect[2] * rect[3]
        result["rects"].append({"rect": {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]},
                                "area": area, "events": events})

        if area > largest_area:
            largest_area = area
            snappi_lcp = events[0]

        if not longest_event or events[0]["timestamp"] > longest_event["timestamp"]:
            longest_event = events[0]

    for event_name, event in found_events.items():
        if event_name == "navigationStart":
            add_navigation_start_event_info(event, result)
        elif "message" in event:
            result["page_events"].append({"event_name": event_name, "message": event["message"]})
        else:
            add_other_event_info(event_name, event, navigation_start_ts, result)

    if snappi_lcp:
        snappi_lcp.update({"area": largest_area})
        result["page_events"].append({"event_name": "snappiLcp", "timestamp": snappi_lcp["timestamp"], "data": snappi_lcp})

    if longest_event:
        result["page_events"].append({"event_name": "allImagesPainted", "timestamp": round(longest_event["timestamp"], 2), "data": {
                                  "imageUrl": longest_event["imageUrl"],
                                  "size": longest_event["size"]}})

    result["page_events"] = sorted(result["page_events"], 
                                   key=lambda x: x.get("timestamp", 0) if not x.get("message") else float('inf'))

    return result