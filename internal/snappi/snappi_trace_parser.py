import sys
import json
from internal.snappi.snappi_rects_parser import parse_rectangles
from internal.snappi.snappi_page_events_generator import generate_page_events
# from image_plotter import plot_rects

event_names = [
    "DOMContentLoaded", "firstContentfulPaint",
    "firstMeaningfulPaint", "firstPaint", "firstImagePaint",
    "LargestTextPaint::Candidate","Layout", "Paint", "CompositeLayers",
    "ParseHTML", "ParseCSS", "UpdateLayoutTree", "domInteractive",
    "domContentLoadedEventStart", "FrameStartedLoading", "FunctionCall",
    "WebContentsImpl::DidNavigateMainFramePreCommit", "domComplete",
    "loadEventEnd"
]

def filter_trace_events(trace_data, event_names):
    filtered_trace_data = {"traceEvents": []}
    event_names += ["navigationStart", "ImagePaint::Timing"]

    for event in trace_data["traceEvents"]:
        if event.get("name") in event_names:
            filtered_trace_data["traceEvents"].append(event)

    return filtered_trace_data

def extract_navigation_start(trace_data):
    for event in trace_data["traceEvents"]:
        if event.get("name") == "navigationStart" and event["args"]["data"].get("isLoadingMainFrame") is True:
            return event
    return None

def snappi_parse_trace(trace_file_dict):
    # with open(trace_file_path, "r") as file:
    trace_data_json = json.load(trace_file_dict)
    trace_data_filtered = filter_trace_events(trace_data_json, event_names)
    navigation_start_event = extract_navigation_start(trace_data_filtered)
    rects = parse_rectangles(trace_data_filtered, navigation_start_event["ts"])
    result = generate_page_events(trace_data_filtered, rects, navigation_start_event, event_names)
    output = {
        "rects": rects,
        "pageEvents": result["page_events"]
    }
    
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_json_file> [<output_graph_file_path>]")
        sys.exit(1)

    json_file_path = sys.argv[1]
    output_graph_file_path = sys.argv[2] if len(sys.argv) == 3 else None

    with open(json_file_path, "r") as file:
        trace_data_json = json.load(file)
        trace_data_filtered = filter_trace_events(trace_data_json, event_names)
        navigation_start_event = extract_navigation_start(trace_data_filtered)
        rects = parse_rectangles(trace_data_filtered, navigation_start_event["ts"])
        result = generate_page_events(trace_data_filtered, rects, navigation_start_event, event_names)
        output = {
            "rects": rects,
            "pageEvents": result["page_events"]
        }

        if output_graph_file_path is not None:
            plot_rects(rects, output_graph_file_path)

        print(json.dumps(output, indent=2))