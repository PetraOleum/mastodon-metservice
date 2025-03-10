import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import datetime as dt
from dateutil.tz import gettz
from pprint import pprint
import geopandas
import matplotlib.pyplot as plt
from matplotlib import colors
from shapely.geometry import Polygon, MultiPolygon
from collections import Counter
from time import sleep
import argparse
import os
import json
from mastodon import Mastodon
import contextily as cx
from math import log2, floor, log, pi, cos
import re

def item_colour(item):
    colour = item.get("ColourCodeHex")
    if colour is not None:
        return colour
    colour = item.get('ColourCode')
    if colour is not None:
        return colour
    return "gray"


def poly_from_string(string, centre_180=True):
    points_str = string.split(" ")
    if centre_180:
        pgon = Polygon([
            (float(ply.split(",")[1]) % 360, float(ply.split(",")[0]))
            for ply in points_str
        ])
    else:
        pgon = Polygon([
            (float(ply.split(",")[1]), float(ply.split(",")[0]))
            for ply in points_str
        ])
    return pgon


def add_polys_basemap(items, basemap, fname, alpha=1, edge_alpha=1, title = None):
    try:
        dpi = 120
        pad_inches = 0
        lat_deg_range = 180
        lon_deg_range = 360
        poly_data = [
            {
                "colour": item_colour(pitem),
                "polygons": [
                    poly_from_string(poly_string, centre_180=True)
                    for poly_string in pitem.get("polygons")
                ]
            }
            for pitem in items
        ]
        multy_pgon = MultiPolygon([
            pgon for polyset in poly_data
            for pgon in polyset.get("polygons")
        ])
        lat_centroid = multy_pgon.centroid.y
        lat_distortion = 1/cos(lat_centroid * pi / 180)
        lon_deg_min = multy_pgon.bounds[0]
        lon_deg_max = multy_pgon.bounds[2]
        lat_deg_min = multy_pgon.bounds[1]
        lat_deg_max = multy_pgon.bounds[3]
        lon_deg_diff = (lon_deg_max - lon_deg_min)
        lat_deg_diff = (lat_deg_max - lat_deg_min)
        zoom_level_lon = -log2(lon_deg_diff/lon_deg_range)
        zoom_level_lat = -log2(lat_deg_diff/(lat_deg_range*lat_distortion))
        zoom_level = round((zoom_level_lon + zoom_level_lat)/2) + 1
        lon_pixels = 256 * lon_deg_diff / (lon_deg_range / (2**zoom_level))
        lon_inch = lon_pixels / dpi
        lat_pixels = 256 * lat_deg_diff / (lat_deg_range / ((2**zoom_level) /
                                           lat_distortion))
        lat_inch = lat_pixels / dpi
        fig = plt.figure(figsize = (lon_inch, lat_inch))
        ax = fig.add_axes((0, 0, 1, 1))
        ax.set_axis_off()
        ax.add_artist(ax.patch)
        ax.patch.set_zorder(-1)
        for pgroup in poly_data:
            poly_colour = pgroup.get("colour")
            for poly_P in pgroup.get("polygons"):
                poly_df = geopandas.GeoDataFrame(crs="wgs84",
                                                 geometry=
                                                 [poly_P],
                                                 index=[0])
                poly_df.to_crs(epsg=3857, inplace=True)
                weather_plt = poly_df.plot(ax=ax,
                                           color = (colors.to_rgb(poly_colour)
                                                   +(alpha,)),
                                           edgecolor=(
                                               colors.to_rgb(poly_colour)
                                               +(edge_alpha,)),
                                           aspect=1)
        if title is not None:
            t_text = "{1} ({0})".format(len(items), title.title())
            ax.set_title(" " + t_text, y = 1,
                         pad = -13, loc = 'left')
        else:
            t_text = None
        cx.add_basemap(ax, source=basemap, zoom=zoom_level)
        fig.savefig(fname, bbox_inches='tight', pad_inches=pad_inches, dpi=dpi)
        plt.close(fig)
        return(
            {
                "file": fname,
                "title": t_text
            }
        )
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"Polygon error at {error_time}")
        print(e)
        return None


def add_polys(items, shpfile, fname, alpha=1, edge_alpha=1, title = None):
    try:
        shp_crs = shpfile.crs
        fig = plt.figure()
        ax = fig.add_axes((0, 0, 1, 1))
        shp_plt = shpfile.plot(ax=ax, color='#FFFFCC',
                               edgecolor=None)
        ax.set_facecolor('#80ccff')
        ax.set_axis_off()
        ax.add_artist(ax.patch)
        ax.patch.set_zorder(-1)
        for pitem in items:
            poly_colour = item_colour(pitem)
            for poly in pitem.get("polygons"):
                poly_P = poly_from_string(poly, centre_180=True)
                poly_df = geopandas.GeoDataFrame(crs="wgs84",
                                                 geometry=
                                                 [poly_P],
                                                 index=[0])
                poly_df.to_crs(shp_crs, inplace=True)
                weather_plt = poly_df.plot(ax=ax,
                                           color = (
                                               colors.to_rgb(poly_colour) +
                                               (alpha,)),
                                           edgecolor=(
                                           colors.to_rgb(poly_colour)
                                           +(edge_alpha,)),
                                           aspect=1)
        if title is not None:
            t_text = "{1} ({0})".format(len(items), title.title())
            ax.set_title(" " + t_text, y = 1,
                         pad = -13, loc = 'left')
        else:
            t_text = None
        fig.savefig(fname, bbox_inches='tight', pad_inches = 0, dpi=200)
        return(
            {
                "file": fname,
                "title": t_text
            }
        )
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"Polygon error at {error_time}")
        print(e)
        return None


def load_rss(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        return ET.fromstring(r.text)
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"RSS download error at {error_time}")
        print(url)
        print(type(e))
        print(e.args)
        print(e)
        return None


def get_cap(link):
    try:
        r = requests.get(link, timeout=10)
        if r.status_code != 200:
            return None
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"CAP download error at {error_time}")
        print(link)
        print(type(e))
        print(e.args)
        print(e)
        return None
    try:
        cap = ET.fromstring(r.text)
        ns = {'': cap.tag[1:].partition("}")[0]} if "}" in cap.tag else None
        info = cap.find('info', ns)
        if info is None:
            return None
        area = info.find('area', ns)
        cap_data = {
            "headline": info.find('headline', ns).text,
            "cap_description": info.find('description', ns).text,
            "identifier": cap.find('identifier', ns).text,
            "sent": cap.find('sent', ns).text,
            "status": cap.find('status', ns).text,
            "msgType": cap.find('msgType', ns).text,
            "event": info.find('event', ns).text,
            "urgency": info.find('urgency', ns).text,
            "severity": info.find('severity', ns).text,
            "certainty": info.find('certainty', ns).text,
            "onset": info.find('onset', ns).text,
            "expires": info.find('expires', ns).text,
            "instruction": info.find('instruction', ns).text,
            "areaDesc": (area.find('areaDesc', ns).text if area
                         is not None else None),
            "polygons": ([poly.text for poly in area.findall('polygon', ns)]
                         if area is not None else None),
            "web": info.find('web', ns).text
        }
        params = [param for param in info.findall('parameter', ns) if param is
                  not None and param.get('valueName', ns) is not None and
                  param.get('value', ns) is not None]
        cap_data.update({param.find('valueName', ns).text:
                         param.find('value', ns).text
                         for param in params})
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"Parsing error at {error_time}")
        print(link)
        print(type(e))
        print(e.args)
        print(e)
        return None
    return(cap_data)


def parse_item(item):
    try:
        item_structure = {
            "guid": item.find("guid").text,
            "title": item.find("title").text,
            "pubDate": item.find("pubDate").text,
            "description": item.find("description").text,
            "link": item.find("link").text
        }
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"Parse error at {error_time}")
        print(e)
        return None
    item_structure.update(get_cap(item_structure.get("link")))
    return item_structure


def item_post(pitem, tz, shp_data, time_fmt="%-I:%M %p %a %-d %b",
              linklength=23, instance_len = 500):
    instance_len = 500 if instance_len is None else instance_len
    try:
        CW_items = [
            pitem.get('headline'),
            pitem.get('areaDesc')
            #pitem.get('certainty')
        ]
        CW_items = [cwitem for cwitem in CW_items
                    if cwitem is not None]
        CW_text = None if len(CW_items) == 0 else re.sub(
            r"(,)([A-Za-z])", ", \\2",
            " - ".join(CW_items))
        desc_text = pitem.get('cap_description')
        if desc_text is not None:
            desc_text = re.sub(
            r"(,)([A-Za-z])", ", \\2",
            desc_text)
        onset_s = pitem.get('onset')
        onset = (None if onset_s is None else
                 dt.datetime.fromisoformat(onset_s))
        expiry_s = pitem.get('expires')
        expiry = (None if expiry_s is None else
                 dt.datetime.fromisoformat(expiry_s))
        sent_s = pitem.get('sent')
        sent = (None if sent_s is None else
                 dt.datetime.fromisoformat(sent_s))
        web = pitem.get('web')
        next_update_s = pitem.get('NextUpdate')
        next_update = (None if next_update_s is None else
                 dt.datetime.fromisoformat(next_update_s))
        text_items = [
            desc_text,
            None if onset_s is None else "Onset: {}".format(
                onset.astimezone(tz).strftime(time_fmt)),
            None if expiry_s is None else "Expires: {}".format(
                expiry.astimezone(tz).strftime(time_fmt)),
            None if next_update_s is None else "Next update: {}".format(
                next_update.astimezone(tz).strftime(time_fmt))
            #web
        ]
        text = "\n".join([txt for txt in text_items if txt is not None])
        CW_len = 0 if CW_text is None else len(CW_text)
        text_len = len(text)
        if (CW_len + text_len) > instance_len:
            text = text[:(instance_len - CW_len - 1)] + "…"
        mapfile = add_polys_basemap([pitem], cx.providers.OpenStreetMap.Mapnik,
                                    fname="alert.png", alpha=0.5)
        return {
            "CW": CW_text,
            "Post": text,
            "Map": [mapfile],
            "guid": pitem.get('guid')
        }
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"Post construction error at {error_time}")
        print(pitem.get('guid'))
        print(e)
        return None


def summary_post(items, now_time, shp_data):
    n_items = len(items)
    if n_items == 0:
        return None
    try:
        CW = "{} New and Updated Weather Alert{}".format(n_items, ""
                                                         if n_items == 1
                                                         else "s")
        severities = [item.get('severity') for item in items]
        sev_c = Counter(severities)
        events = [item.get('event') for item in items]
        events_c = Counter(events)
        certainties = [item.get('certainty') for item in items]
        certs_c = Counter(certainties)
        onsets = [item.get('onset') for item in items]
        ongoing = [now_time >= dt.datetime.fromisoformat(onset) for onset in
                   onsets if onset is not None]
        time_text = "As at {}".format(now_time.strftime("%-d %b %Y %H:%M %Z"))
        sev_text = "Severity: " + "; ".join([
            "{} {}".format(value, key)
            for key, value in sev_c.items()
        ])
        events_c = Counter(events)
        event_counts_text = "; ".join([
            "{} {}".format(value, key.title())
            for key, value in events_c.items()
        ])
        event_text = "Types: " + event_counts_text
        cert_text = "Certainty: " + "; ".join([
            "{} {}".format(value, key)
            for key, value in certs_c.items()
        ])
        ongoing_text = "{} ongoing".format(sum(ongoing))
        post_text = "\n".join([
            time_text, sev_text, event_text, cert_text, ongoing_text
        ])
        event_types = [k for k in events_c.keys() if k is not None]
        event_types.sort(key = lambda k: -events_c[k])
        n_event_types = len(event_types)

        if n_event_types > 1:
            CW = "{} ({})".format(CW, event_counts_text)
        elif n_event_types == 1:
            CW = "{} ({})".format(CW, event_types[0].title())

        if n_event_types == 0:
            map_fnames = []
        elif n_event_types == 1:
            map_fnames = [add_polys(items, shp_data, fname="all.png",
                                    alpha=0.9, edge_alpha=0.5,
                                    title=event_types[0])]
        elif n_event_types <= 4:
            map_fnames = [
                add_polys([
                    item for item in items if item.get('event') == value
                ], shp_data, fname="all_{}.png".format(count), alpha = 0.9,
                    edge_alpha=0.5, title = value)
                for count, value in enumerate(event_types)
            ]
        else:
            first_3 = event_types[:3]
            map_fnames = [
                add_polys([
                    item for item in items if item.get('event') == value
                ], shp_data, fname="all_{}.png".format(count), alpha = 0.9,
                    edge_alpha=0.5, title = value)
                for count, value in enumerate(first_3)
            ]
            other_map = [
                add_polys([
                    item for item in items if item.get('event') not in first_3
                ], shp_data, fname="all_other.png", alpha = 0.9,
                    edge_alpha=0.0, title = "Other")
            ]
            map_fnames = map_fnames + other_map
        map_fnames = [fn for fn in map_fnames if fn is not None]
        if len(map_fnames) == 1:
            post_text = post_text + "\nMap:"
        elif len(map_fnames) > 1:
            post_text = post_text + "\nMaps:"
        return {
            "CW": CW,
            "Post": post_text,
            "Map": map_fnames
        }
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"Summary post construction error at {error_time}")
        print(type(e))
        print(e)
        return None


def make_post(content, mastodon, visibility, threadid=None):
    try:
        map_files = content.get("Map")
        media_ids = [
            mastodon.media_post(map_file.get('file'), description =
                                content.get('CW') + (
                                    "" if map_file.get('title') is None else
                                    " - {}".format(map_file.get('title'))
                                ))
            for map_file in map_files if map_file is not None and
            map_file.get('file') is not None and
            os.path.isfile(map_file.get('file'))
        ]
        nthreadid = mastodon.status_post(content.get("Post"),
                                         in_reply_to_id=threadid,
                                         media_ids=media_ids,
                                         spoiler_text=content.get("CW"),
                                         sensitive=False,
                                         visibility=visibility).get("id")
        return nthreadid
    except Exception as e:
        error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
        print(f"Posting error at {error_time}")
        print(type(e))
        print(e)
        print(content)
        cw_c = content.get("CW")
        cw_c = "" if cw_c is None else cw_c
        post_c = content.get("Post")
        print("CW Len: {}; utf8: {}".format(len(cw_c),
                                         len(cw_c.encode("utf-8"))))
        print("Len: {}; utf8: {}".format(len(post_c),
                                         len(post_c.encode("utf-8"))))
        return threadid


def main(config, debug=False, ver_checkmode="created"):
    if debug:
        print("Debugging: not posting to mastodon")
        mast_usr = None
    else:
        mast_usr = Mastodon(
            access_token = config.get("mastodon_cred"),
            api_base_url = config.get("mastodon_server"),
            ratelimit_method = 'wait',
            version_check_mode = ver_checkmode
        )
    cap_url = config.get('rss_url')
    shp_data = geopandas.read_file(config.get('shape_file'))
    bottz = gettz(config.get('tz'))
    if bottz is None:
        print("TZ parsing error for {}; setting to UTC".format(
            config.get('tz')))
        bottz = gettz("UTC")
    now_time = dt.datetime.now().astimezone(bottz)
    rss_root = load_rss(cap_url)
    rss_items = [item for item in rss_root.find('channel').findall('item') if
                 item.find('guid') is not None]
    it = rss_root.find('channel').findall('item')
    rss_dict = {item.find('guid').text: {"description":
                                         item.find('description').text, "link":
                                         item.find('link').text, "guid":
                                         item.find('guid').text}
                for item in rss_items}
    alert_update = False
    archive_fp = config.get("archive_file")
    if ((archive_fp is None or not os.path.isfile(archive_fp)) and
        len(rss_items) > 0):
        alert_update = True
        rss_items_new = rss_items
    else:
        try:
            with open(archive_fp, "r") as f:
                archive_dat = json.load(f)
            archive_guid = archive_dat.keys()
            rss_items_new = [item for item in rss_items
                             if item.find('guid').text
                             not in archive_guid]
            alert_update = False if len(rss_items_new) == 0 else True
        except Exception as e:
            error_time = dt.datetime.now().astimezone(None).strftime("%c %Z")
            print(f"Archive error at {error_time}")
            print(e)
            print(type(e))
            rss_items_new = rss_items
            alert_update = True if len(rss_items) > 0 else False
    if alert_update:
        if archive_fp is not None:
            if debug:
                print("Saving to {}".format(archive_fp))
            with open(archive_fp, "w") as f:
                json.dump(rss_dict, fp=f)
            if debug:
                print("Saved")
        items_parsed = [parse_item(item) for item in rss_items_new]
        sum_p = summary_post(items_parsed, now_time, shp_data=shp_data)
        tid = None
        if debug:
            pprint(sum_p)
        else:
            tid = make_post(sum_p, mast_usr,
                            visibility=config.get('visibility'))
        for item in items_parsed:
            sleep(config.get("wait"))
            item_p = item_post(item, tz=bottz,
                               shp_data=shp_data,
                               instance_len=config.get("character_limit"))
            if debug:
                pprint(item_p)
            else:
                tid = make_post(item_p, mast_usr,
                                visibility=config.get('secondary_visibility'),
                                threadid=tid)
        if debug:
            print("Done")
    elif alert_update and len(items_parsed) == 0:
        if debug:
            print("No warnings")
    else:
        if debug:
            print("No change in archive file, skipping")


# Default args for interactive debugging:
conf_default = {
    "shape_file": "lds-nz-coastlines-and-islands-polygons-topo-1500k-SHP.zip",
    "tz": "Pacific/Auckland",
    "wait": 5,
    "full_map": "all.png",
    "alert_map": "alert.png",
    "rss_url": "https://alerts.metservice.com/cap/rss",
    "website_url": "https://metservice.com/warnings/home",
    "archive_file": "archive.json",
    "mastodon_server": "https://botsin.space",
    "mastodon_cred": "nzweather_usercred.secret",
    "character_limit": 500,
    "visibility": "direct",
    "secondary_visibility": "direct"
}

if __name__ == "__main__":
    # Non-interactive mode:
    argparser = argparse.ArgumentParser(description="Weather CAP mastodon bot")
    argparser.add_argument("--config", help="Config filepath (json)",
                           dest="config_file", default="config.json")
    argparser.add_argument("--debug", help="Debug (don't post to mastodon)",
                           dest="debug", action="store_true")
    argparser.add_argument("--dir", default=".", dest="dir",
                        help="Directory to operate in")
    argparser.add_argument("--no-check-api-version",
                           help=("Don't check API version. "
                                 "Useful for other servers like GtS"),
                           dest="no_check_api", action="store_true")
    args = argparser.parse_args()
    with open(args.config_file, "r") as configfile:
        conf_json = json.load(configfile)
    os.chdir(args.dir)
    ver_checkmode = "none" if args.no_check_api else "created"
    main(conf_json, debug=args.debug, ver_checkmode=ver_checkmode)

