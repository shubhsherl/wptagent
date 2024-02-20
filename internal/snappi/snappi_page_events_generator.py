import json

def match_frame_value(event, ns_frame, event_name, found_events):
    event_args = event.get("args", {})
    event_frame = event_args.get("frame", None)

    if event_frame is None:
        event_data = event_args.get("data", {})
        event_frame = event_data.get("frame", None)

    if event_frame is None:
        begin_data = event_args.get("beginData", {})
        event_frame = begin_data.get("frame", None)

    if event_frame is None:
        for key, value in event_args.items():
            if isinstance(value, dict) and "frame" in value:
                event_frame = value.get("frame", None)

                if event_frame is not None:
                    break

    # Check if an event is already in found_events and if it's matched
    event_already_exists = event_name in found_events
    event_already_matched = event_already_exists and found_events[event_name]["matched"]

    # Only store the event if it's the first occurrence of a matching frame
    if event_frame == ns_frame and not event_already_matched:
        found_events[event_name] = {
            "event": event,
            "matched": event_frame == ns_frame,
            "frame": event_frame
        }
    # Store the first non-matching event if it's not already stored
    elif not event_already_exists:
        found_events[event_name] = {
            "event": event,
            "matched": event_frame == ns_frame,
            "frame": event_frame
        }

def assemble_final_events(found_events):
    final_events = {}

    for event_name, event_info in found_events.items():
        if event_info["matched"]:
            final_events[event_name] = event_info["event"]
            final_events[event_name]["frame"] = event_info.get("frame")
        elif event_name not in final_events:
            final_events[event_name] = event_info["event"]
            final_events[event_name]["frame"] = event_info.get("frame")

    return final_events


def add_navigation_start_event_info(event, frame, result):
    navigation_start_data = event["args"]["data"]

    result["page_events"].append({
        "event_name": "navigationStart",
        "documentLoaderUrl": navigation_start_data["documentLoaderURL"],
        "isLoadingMainFrame": navigation_start_data["isLoadingMainFrame"],
        "navigationId": navigation_start_data["navigationId"],
        "frame": frame,
        "timestamp": 0
    })

def generate_page_events(trace_data, rects, navigation_start_event, event_names):
    largest_area = 0
    snappi_lcp = None
    all_images_painted = None
    navigation_start_ts = navigation_start_event["ts"]

    found_events = {}

    for event in trace_data["traceEvents"]:
        event_name = event.get("name")
        if event_name in event_names and event["ts"] > navigation_start_ts:
            ns_frame = navigation_start_event["args"]["frame"]
            match_frame_value(event, ns_frame, event_name, found_events)

    found_events = assemble_final_events(found_events)
    found_events["navigationStart"] = navigation_start_event
    found_events["navigationStart"]["frame"] = ns_frame

    result = {"rects": [], "page_events": []}

    for rect_data in rects:
        rect = [rect_data["x"], rect_data["y"], rect_data["width"], rect_data["height"]]
        events = rect_data["events"]
        area = rect[2] * rect[3]
        result["rects"].append({
            "rect": {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]},
            "area": area, "events": events
        })

        if area > largest_area:
            largest_area = area
            snappi_lcp = events[0]

        if not all_images_painted or events[0]["timestamp"] > all_images_painted["timestamp"]:
            all_images_painted = events[0]

    for event_name, event_info in found_events.items():
        if event_name == "navigationStart":
            add_navigation_start_event_info(event_info, event_info["frame"], result)
        else:
            event_data = {
                "event_name": event_name,
                "timestamp": (event_info["ts"] - navigation_start_ts) / 1000,
            }
            if "frame" in event_info:
                event_data["frame"] = event_info["frame"]

            if event_name == "LargestTextPaint::Candidate":
                root_height = event_info["args"]["data"]["root_height"]
                root_width = event_info["args"]["data"]["root_width"]
                area = root_height * root_width
                event_data["area"] = area

                # check if text paint is larger
                if area > largest_area:
                    largest_area = area
                    snappi_lcp = event_data

            result["page_events"].append(event_data)

    if snappi_lcp:
        snappi_lcp.update({"area": largest_area})
        result["page_events"].append({
            "event_name": "snappiLcp",
            "timestamp": snappi_lcp["timestamp"],
            "data": snappi_lcp,
        })

    if all_images_painted:
        result["page_events"].append({
            "event_name": "allImagesPainted",
            "timestamp": round(all_images_painted["timestamp"], 2),
            "data": {
                "imageUrl": all_images_painted["imageUrl"],
                "size": all_images_painted["size"]
            }
        })

    result["page_events"] = sorted(result["page_events"], 
                                   key=lambda x: x.get("timestamp", 0) if not x.get("message") else float('inf'))

    return result