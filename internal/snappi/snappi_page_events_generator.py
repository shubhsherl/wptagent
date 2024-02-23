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

# Function to check if two rectangles overlap
def rectangle_overlaps(rect1, rect2):
    # Correcting the indices for list elements
    return not (rect1[0] + rect1[2] <= rect2[0] or
                rect1[0] >= rect2[0] + rect2[2] or
                rect1[1] + rect1[3] <= rect2[1] or
                rect1[1] >= rect2[1] + rect2[3])

def generate_page_events(trace_data, rects, navigation_start_event, event_names):
    largest_area = 0
    snappi_lcp = None
    all_content_painted = None
    navigation_start_ts = navigation_start_event["ts"]
    processed_nodes = set()
    IDLE_PERIOD = 2 * 1000  # Multi-second period of idleness in milliseconds
    prev_event_ts_ms = 0

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
    post_load_popups = []

    for rect_data in rects:
        rect = [rect_data["x"], rect_data["y"], rect_data["width"], rect_data["height"]]
        events = rect_data["events"]
        area = rect[2] * rect[3]
        dom_node_id = events[0]["domNodeId"]

        if (area, dom_node_id) not in processed_nodes:
            processed_nodes.add((area, dom_node_id))

            # Detect post load popups based on idleness and overlapping count
            is_post_load_popup = False
            print(f"Timestamps: prev_event_ts_ms={prev_event_ts_ms}, current_event_ts={events[0]['timestamp']}")
            idle_time = events[0]["timestamp"] - prev_event_ts_ms
            if idle_time >= IDLE_PERIOD:
                prev_event_ts_ms = events[0]["timestamp"]
                overlapping_count = sum([
                    True for rect2_data in rects
                    if rectangle_overlaps(rect, [rect2_data["x"], rect2_data["y"], rect2_data["width"], rect2_data["height"]])
                ])
                if overlapping_count >= 3:
                    is_post_load_popup = True
                    post_load_popups.append({
                        "domNodeId": dom_node_id,
                        "timestamp": events[0]["timestamp"],
                        "overlapping_count": overlapping_count
                    })
                    print(f"Post-load popup detected for domNodeId {dom_node_id} with timestamp {events[0]['timestamp']} and overlapping_count {overlapping_count}")
                else:
                    print(f"Possible post-load popup for domNodeId {dom_node_id} with timestamp {events[0]['timestamp']} was not detected due to insufficient overlapping count: {overlapping_count}")
            else:
                print(f"No post-load popup for domNodeId {dom_node_id} with timestamp {events[0]['timestamp']} due to no idle period of {idle_time:.2f}")

            if not is_post_load_popup:  # Only process the event if it's not a post load popup
                result["rects"].append({
                    "rect": {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]},
                    "area": area, "events": events
                })
                if area > largest_area:
                    largest_area = area
                    snappi_lcp = events[0]

                # Check for latest painted event, either "image" or "text"
                if events[0]["type"] in ["image", "text"]:
                    if not all_content_painted or events[0]["timestamp"] > all_content_painted["timestamp"]:
                        all_content_painted = events[0]

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

    if all_content_painted:
        result["page_events"].append({
            "event_name": "snappiAcp",
            "timestamp": round(all_content_painted["timestamp"], 2),
            "data": {
                "elementType": all_content_painted["type"],
                "elementUrl": all_content_painted["imageUrl"] if all_content_painted["type"] == "image" else "",
                "size": all_content_painted["size"]
            }
        })

    result["page_events"] = sorted(result["page_events"],
                                   key=lambda x: x.get("timestamp", 0) if not x.get("message") else float('inf'))

    result["popups_found"] = post_load_popups

    return result

