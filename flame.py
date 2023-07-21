'''
    usage:
    python flame.py {json path} {svg path| optional with default value `SotFlame.svg`}
'''


import json
import sys, os
import argparse
import random


GRAPH_WIDTH = 1200

GRAPH_SIDE_WIDTH = 10
GRAPH_TOP_HEIGHT = 35
GRAPH_BOTTEM_HEIGHT = 30

BOX_HEIGHT = 15
BOX_SPACING = 0.4

TEXT_OFFSET_X = 3
TEXT_OFFSET_Y = 10



def get_color():
    r = random.randint(200, 255)
    g = random.randint(0, 230)
    b = random.randint(1, 55)
    return f"rgb({r},{g},{b})"


class EventNode:
    def __init__(self, json_obj, level=0):
        self.name = json_obj["name"]
        self.start_time = json_obj["start_time"]
        self.end_time = json_obj["end_time"]
        self.lasted = json_obj["lasted"]
        self.level = level

        self.box_y = (BOX_HEIGHT + BOX_SPACING) * level + GRAPH_TOP_HEIGHT
        self.text_y = self.box_y + TEXT_OFFSET_Y
        self.box_height = BOX_HEIGHT
        self.box_fill = get_color()

        self.title = f"{self.name} (time cost: {self.lasted})"

        self.sub_events = []

    @staticmethod
    def create_from(json_obj, level=0):
        event = EventNode(json_obj, level)
        max_deepth = 0
        for x in json_obj["sub_events"]:
            sub_event, deepth = EventNode.create_from(x, level=level+1)
            event.sub_events.append(sub_event)
            max_deepth = max(max_deepth, deepth)
        
        return event, max_deepth+1

    def set_x_axis(self, box_x, width):
        self.box_x = box_x
        self.box_width = width
        self.text_x = box_x + TEXT_OFFSET_X

    def set_up_configs(self):
        for sub_event in self.sub_events:
            scale = self.box_width / self.lasted
            width = sub_event.lasted * scale
            box_x = (sub_event.start_time - self.start_time) * scale + self.box_x
            sub_event.set_x_axis(box_x, width)
            sub_event.set_up_configs()

    def create_box_str(self):
        return '''\
<g class="func_g" onmouseover="s('{title}')" onmouseout="c()" onclick="zoom(this)">
    <title>{title}</title>
    <rect x="{box_x}" y="{box_y}" width="{box_width}" height="{box_height}" fill="{box_fill}" rx="2" ry="2" />
    <text text-anchor="" x="{text_x}" y="{text_y}" font-size="12" font-family="Verdana" fill="rgb(0,0,0)"  ></text>
</g>
        '''.format(
            title=self.title, 
            box_x=self.box_x,
            box_y=self.box_y,
            box_width=self.box_width,
            box_height=self.box_height,
            box_fill=self.box_fill,
            text_x=self.text_x,
            text_y=self.text_y,
        )

    def create_boxes(self, boxes=[]):
        boxes.append(self.create_box_str())
        for sub_event in self.sub_events:
            sub_event.create_boxes(boxes)
        return boxes

    def create_boxes_upside_down(self, max_level, boxes=[]):
        self.level = max_level - self.level
        self.box_y = (BOX_HEIGHT + BOX_SPACING) * self.level + GRAPH_TOP_HEIGHT
        self.text_y = self.box_y + TEXT_OFFSET_Y
        boxes.append(self.create_box_str())
        for sub_event in self.sub_events:
            sub_event.create_boxes_upside_down(max_level, boxes)
        return boxes


def json2svg(json_path, svg_path):
    with open(json_path, "r") as fp:
        json_obj = json.load(fp)
    event_root, max_deepth = EventNode.create_from(json_obj[0])
    if event_root.sub_events:
        event_root.start_time = event_root.sub_events[0].start_time
        event_root.lasted = event_root.end_time - event_root.start_time
    event_root.set_x_axis(GRAPH_SIDE_WIDTH, GRAPH_WIDTH - GRAPH_SIDE_WIDTH * 2)
    event_root.set_up_configs()

    graph_height =  GRAPH_TOP_HEIGHT + GRAPH_BOTTEM_HEIGHT + (BOX_HEIGHT + BOX_SPACING) * max_deepth
    head_str = svg_head(GRAPH_WIDTH, graph_height, GRAPH_SIDE_WIDTH, GRAPH_TOP_HEIGHT, GRAPH_BOTTEM_HEIGHT)
    svg_strs = event_root.create_boxes_upside_down(max_deepth-1, [head_str])
    svg_strs.append(svg_tail())

    with open(svg_path, "w") as fp:
        fp.write("\n".join(svg_strs))




def svg_head(graph_width, graph_height, graph_side_width, graph_top_height, graph_bottem_height):
    head = '''\
<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" width="{width}" height="{height}" onload="init(evt)" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">\n'''.format(
    width= graph_width,
    height=graph_height
) + '''\
<!-- Flame graph stack visualization. See https://github.com/brendangregg/FlameGraph for latest version, and http://www.brendangregg.com/flamegraphs.html for examples. -->
<defs >
    <linearGradient id="background" y1="0" y2="1" x1="0" x2="0" >
        <stop stop-color="#eeeeee" offset="5%" />
        <stop stop-color="#eeeeb0" offset="95%" />
    </linearGradient>
</defs>
<style type="text/css">
    .func_g:hover { stroke:black; stroke-width:0.5; cursor:pointer; }
</style>
<script type="text/ecmascript">
<![CDATA[
    var details, svg;
    function init(evt) { 
        details = document.getElementById("details").firstChild; 
        searchbtn = document.getElementById("search");
        matchedtxt = document.getElementById("matched");
        svg = document.getElementsByTagName("svg")[0];
        searching = 0;
    }

    // mouse-over for info
    function s(info) { details.nodeValue = "Function: " + info; }
    function c() { details.nodeValue = ' '; }

    // ctrl-F for search
    window.addEventListener("keydown",function (e) {
        if (e.keyCode === 114 || (e.ctrlKey && e.keyCode === 70)) { 
            e.preventDefault();
            search_prompt();
        }
    })

    // functions
    function find_child(parent, name, attr) {
        var children = parent.childNodes;
        for (var i=0; i<children.length;i++) {
            if (children[i].tagName == name)
                return (attr != undefined) ? children[i].attributes[attr].value : children[i];
        }
        return;
    }
    function orig_save(e, attr, val) {
        if (e.attributes["_orig_"+attr] != undefined) return;
        if (e.attributes[attr] == undefined) return;
        if (val == undefined) val = e.attributes[attr].value;
        e.setAttribute("_orig_"+attr, val);
    }
    function orig_load(e, attr) {
        if (e.attributes["_orig_"+attr] == undefined) return;
        e.attributes[attr].value = e.attributes["_orig_"+attr].value;
        e.removeAttribute("_orig_"+attr);
    }
    function g_to_text(e) {
        var text = find_child(e, "title").firstChild.nodeValue;
        return (text)
    }
    function g_to_func(e) {
        var func = g_to_text(e);
        if (func != null)
            func = func.replace(/ .*/, "");
        return (func);
    }
    function update_text(e) {
        var r = find_child(e, "rect");
        var t = find_child(e, "text");
        var w = parseFloat(r.attributes["width"].value) -3;
        var txt = find_child(e, "title").textContent.replace(/\([^(]*\)/,"");
        t.attributes["x"].value = parseFloat(r.attributes["x"].value) +3;
        
        // Smaller than this size won't fit anything
        if (w < 2*12*0.59) {
            t.textContent = "";
            return;
        }
        
        t.textContent = txt;
        // Fit in full text width
        if (/^ *$/.test(txt) || t.getSubStringLength(0, txt.length) < w)
            return;
        
        for (var x=txt.length-2; x>0; x--) {
            if (t.getSubStringLength(0, x+2) <= w) { 
                t.textContent = txt.substring(0,x) + "..";
                return;
            }
        }
        t.textContent = "";
    }

    // zoom
    function zoom_reset(e) {
        if (e.attributes != undefined) {
            orig_load(e, "x");
            orig_load(e, "width");
        }
        if (e.childNodes == undefined) return;
        for(var i=0, c=e.childNodes; i<c.length; i++) {
            zoom_reset(c[i]);
        }
    }
    function zoom_child(e, x, ratio) {
        if (e.attributes != undefined) {
            if (e.attributes["x"] != undefined) {
                orig_save(e, "x");
                e.attributes["x"].value = (parseFloat(e.attributes["x"].value) - x - 10) * ratio + 10;
                if(e.tagName == "text") e.attributes["x"].value = find_child(e.parentNode, "rect", "x") + 3;
            }
            if (e.attributes["width"] != undefined) {
                orig_save(e, "width");
                e.attributes["width"].value = parseFloat(e.attributes["width"].value) * ratio;
            }
        }
        
        if (e.childNodes == undefined) return;
        for(var i=0, c=e.childNodes; i<c.length; i++) {
            zoom_child(c[i], x-10, ratio);
        }
    }
    function zoom_parent(e) {
        if (e.attributes) {
            if (e.attributes["x"] != undefined) {
                orig_save(e, "x");
                e.attributes["x"].value = 10;
            }
            if (e.attributes["width"] != undefined) {
                orig_save(e, "width");
                e.attributes["width"].value = parseInt(svg.width.baseVal.value) - (10*2);
            }
        }
        if (e.childNodes == undefined) return;
        for(var i=0, c=e.childNodes; i<c.length; i++) {
            zoom_parent(c[i]);
        }
    }
    function zoom(node) { 
        var attr = find_child(node, "rect").attributes;
        var width = parseFloat(attr["width"].value);
        var xmin = parseFloat(attr["x"].value);
        var xmax = parseFloat(xmin + width);
        var ymin = parseFloat(attr["y"].value);
        var ratio = (svg.width.baseVal.value - 2*10) / width;
        
        // XXX: Workaround for JavaScript float issues (fix me)
        var fudge = 0.0001;
        
        var unzoombtn = document.getElementById("unzoom");
        unzoombtn.style["opacity"] = "1.0";
        
        var el = document.getElementsByTagName("g");
        for(var i=0;i<el.length;i++){
            var e = el[i];
            var a = find_child(e, "rect").attributes;
            var ex = parseFloat(a["x"].value);
            var ew = parseFloat(a["width"].value);
            // Is it an ancestor
            if (0 == 0) {
                var upstack = parseFloat(a["y"].value) > ymin;
            } else {
                var upstack = parseFloat(a["y"].value) < ymin;
            }
            if (upstack) {
                // Direct ancestor
                if (ex <= xmin && (ex+ew+fudge) >= xmax) {
                    e.style["opacity"] = "0.5";
                    zoom_parent(e);
                    e.onclick = function(e){unzoom(); zoom(this);};
                    update_text(e);
                }
                // not in current path
                else
                    e.style["display"] = "none";
            }
            // Children maybe
            else {
                // no common path
                if (ex < xmin || ex + fudge >= xmax) {
                    e.style["display"] = "none";
                }
                else {
                    zoom_child(e, xmin, ratio);
                    e.onclick = function(e){zoom(this);};
                    update_text(e);
                }
            }
        }
    }
    function unzoom() {
        var unzoombtn = document.getElementById("unzoom");
        unzoombtn.style["opacity"] = "0.0";
        
        var el = document.getElementsByTagName("g");
        for(i=0;i<el.length;i++) {
            el[i].style["display"] = "block";
            el[i].style["opacity"] = "1";
            zoom_reset(el[i]);
            update_text(el[i]);
        }
    }	

    // search
    function reset_search() {
        var el = document.getElementsByTagName("rect");
        for (var i=0; i < el.length; i++){
            orig_load(el[i], "fill")
        }
    }
    function search_prompt() {
        if (!searching) {
            var term = prompt("Enter a search term (regexp " +
                "allowed, eg: ^ext4_)", "");
            if (term != null) {
                search(term)
            }
        } else {
            reset_search();
            searching = 0;
            searchbtn.style["opacity"] = "0.1";
            searchbtn.firstChild.nodeValue = "Search"
            matchedtxt.style["opacity"] = "0.0";
            matchedtxt.firstChild.nodeValue = ""
        }
    }
    function search(term) {
        var re = new RegExp(term);
        var el = document.getElementsByTagName("g");
        var matches = new Object();
        var maxwidth = 0;
        for (var i = 0; i < el.length; i++) {
            var e = el[i];
            if (e.attributes["class"].value != "func_g")
                continue;
            var func = g_to_func(e);
            var rect = find_child(e, "rect");
            if (rect == null) {
                // the rect might be wrapped in an anchor
                // if nameattr href is being used
                if (rect = find_child(e, "a")) {
                    rect = find_child(r, "rect");
                }
            }
            if (func == null || rect == null)
                continue;

            // Save max width. Only works as we have a root frame
            var w = parseFloat(rect.attributes["width"].value);
            if (w > maxwidth)
                maxwidth = w;

            if (func.match(re)) {
                // highlight
                var x = parseFloat(rect.attributes["x"].value);
                orig_save(rect, "fill");
                rect.attributes["fill"].value =
                    "rgb(230,0,230)";

                // remember matches
                if (matches[x] == undefined) {
                    matches[x] = w;
                } else {
                    if (w > matches[x]) {
                        // overwrite with parent
                        matches[x] = w;
                    }
                }
                searching = 1;
            }
        }
        if (!searching)
            return;

        searchbtn.style["opacity"] = "1.0";
        searchbtn.firstChild.nodeValue = "Reset Search"

        // calculate percent matched, excluding vertical overlap
        var count = 0;
        var lastx = -1;
        var lastw = 0;
        var keys = Array();
        for (k in matches) {
            if (matches.hasOwnProperty(k))
                keys.push(k);
        }
        // sort the matched frames by their x location
        // ascending, then width descending
        keys.sort(function(a, b){
                return a - b;
            if (a < b || a > b)
                return a - b;
            return matches[b] - matches[a];
        });
        // Step through frames saving only the biggest bottom-up frames
        // thanks to the sort order. This relies on the tree property
        // where children are always smaller than their parents.
        for (var k in keys) {
            var x = parseFloat(keys[k]);
            var w = matches[keys[k]];
            if (x >= lastx + lastw) {
                count += w;
                lastx = x;
                lastw = w;
            }
        }
        // display matched percent
        matchedtxt.style["opacity"] = "1.0";
        pct = 100 * count / maxwidth;
        if (pct == 100)
            pct = "100"
        else
            pct = pct.toFixed(1)
        matchedtxt.firstChild.nodeValue = "Matched: " + pct + "%";
    }
    function searchover(e) {
        searchbtn.style["opacity"] = "1.0";
    }
    function searchout(e) {
        if (searching) {
            searchbtn.style["opacity"] = "1.0";
        } else {
            searchbtn.style["opacity"] = "0.1";
        }
    }
]]>
</script>\n''' + '''\
<rect x="0.0" y="0" width="{width}" height="{height}" fill="url(#background)"  />
<text text-anchor="middle" x="{half_width}" y="24" font-size="17" font-family="Verdana" fill="rgb(0,0,0)"  >Flame Graph</text>
<text text-anchor="" x="{left_pos}" y="{bottom_pos}" font-size="12" font-family="Verdana" fill="rgb(0,0,0)" id="details" > </text>
<text text-anchor="" x="{left_pos}" y="{top_pos}" font-size="12" font-family="Verdana" fill="rgb(0,0,0)" id="unzoom" onclick="unzoom()" style="opacity:0.0;cursor:pointer" >Reset Zoom</text>
<text text-anchor="" x="{right_pos}" y="{top_pos}" font-size="12" font-family="Verdana" fill="rgb(0,0,0)" id="search" onmouseover="searchover()" onmouseout="searchout()" onclick="search_prompt()" style="opacity:0.1;cursor:pointer" >Search</text>
<text text-anchor="" x="{right_pos}" y="{bottom_pos}" font-size="12" font-family="Verdana" fill="rgb(0,0,0)" id="matched" > </text>
'''.format(
        width=graph_width,
        height=graph_height,
        half_width=graph_width * 0.5,
        left_pos = graph_side_width,
        right_pos = graph_width - graph_side_width - 100,
        top_pos = graph_top_height - 10,
        bottom_pos = graph_height - graph_bottem_height + 15,
    )

    return head

def svg_tail():
    tail = '''\
</svg>
    '''
    return tail


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=str, help="path of json file")
    parser.add_argument("--svg_path", type=str, help="path of output svg file", default=sys.path[0] + "/SotFlame.svg")
    args = parser.parse_args()

    json2svg(args.json_path, args.svg_path)

