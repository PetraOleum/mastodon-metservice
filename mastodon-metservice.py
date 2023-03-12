import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import datetime as dt
from dateutil.tz import gettz
from pprint import pprint
import geopandas
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from collections import Counter
from time import sleep
import argparse
import os
import json
from mastodon import Mastodon


# Non-interactive END


def add_polys(items, shpfile, fname, alpha=1):
    try:
        shp_crs = shpfile.crs
        fig = plt.figure()
        ax  = fig.add_axes((0,0,1,1))
        #fig, ax = plt.subplots()
        #ax.set_aspect('equal')
        shp_plt = shpfile.plot(ax = ax, color = '#FFFFCC',
                               edgecolor=None)
        ax.set_facecolor('#80ccff')
        ax.set_axis_off()
        ax.add_artist(ax.patch)
        ax.patch.set_zorder(-1)
        for pitem in items:
            poly = Polygon([list(reversed(ply.split(",")))
                            for ply in pitem["polygon"]])
            poly_colour = pitem.get("ColourCodeHex")
            poly_colour = (pitem.get('ColourCode') if poly_colour is None else
                           poly_colour)
            poly_colour = "gray" if poly_colour is None else poly_colour
            poly_df = geopandas.GeoDataFrame(crs = "wgs84",
                                             geometry =
                                             [poly],
                                             index=[0])
            poly_df.to_crs(shp_crs, inplace=True)
            weather_plt = poly_df.plot(ax=ax,
                                       color = poly_colour,
                                       edgecolor = None,
                                       aspect=1, alpha=alpha)
        fig.savefig(fname, bbox_inches='tight', pad_inches = 0, dpi=200)
        return(fname)
    except Exception as e:
        print("Polygon error")
        print(e)
        return None


def load_rss(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return ET.fromstring(r.text)
    except Exception as e:
        print("RSS download error")
        print(url)
        print(type(e))
        print(e.args)
        print(e)
        return None


def get_cap(link):
    try:
        r = requests.get(link)
        if r.status_code != 200:
            return None
    except Exception as e:
        print("CAP download error")
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
            "polygon": (area.find('polygon', ns).text.split(" ") if area is not
                        None else None),
            "web": info.find('web', ns).text
        }
        params = [param for param in info.findall('parameter', ns) if param is
                  not None and param.get('valueName', ns) is not None and
                  param.get('value', ns) is not None]
        cap_data.update({param.find('valueName', ns).text:
                         param.find('value', ns).text
                         for param in params})
    except Exception as e:
        print("Parsing error")
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
        print("Parse error")
        print(e)
        return None
    item_structure.update(get_cap(item_structure.get("link")))
    return item_structure


def item_post(pitem, tz, shp_data, time_fmt="%-I:%M %p %a %-d %b",
              linklength=23, instance_len = 500):
    try:
        CW_items = [
            pitem.get('headline'),
            pitem.get('areaDesc'),
            pitem.get('certainty')
        ]
        CW_items = [cwitem for cwitem in CW_items
                    if cwitem is not None]
        CW_text = None if len(CW_items) == 0 else " - ".join(CW_items)
        desc_text = pitem.get('cap_description')
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
        text_len = len(text)
        if text_len > instance_len:
            text = text[:(instance_len - 1)] + "…"
        elif text_len < instance_len - linklength:
            text = text + "\n" + web
        mapfile = add_polys([pitem], shp_data, fname="alert.png")
        return {
            "CW": CW_text,
            "Post": text,
            "Map": mapfile,
            "guid": pitem.get('guid')
        }
    except Exception as e:
        print("Post construction error")
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
        event_text = "Types: " + "; ".join([
            "{} {}".format(value, key)
            for key, value in events_c.items()
        ])
        cert_text = "Certainty: " + "; ".join([
            "{} {}".format(value, key)
            for key, value in certs_c.items()
        ])
        ongoing_text = "{} ongoing".format(sum(ongoing))
        post_text = "\n".join([
            time_text, sev_text, event_text, cert_text, ongoing_text
        ])
        map_fname = add_polys(items, shp_data, fname="all.png", alpha=0.9)
        if map_fname is not None:
            post_text = post_text + "\nMap:"
        return {
            "CW": CW,
            "Post": post_text,
            "Map": map_fname
        }
    except Exception as e:
        print("Summary post construction error")
        print(type(e))
        print(e)
        return None


def make_post(content, mastodon, visibility, threadid=None):
    try:
        map_file = content.get("Map")
        if map_file is not None and os.path.isfile(map_file):
            media_id = mastodon.media_post(map_file, description =
                                           content.get('CW'))
        else:
            media_id = None
        nthreadid = mastodon.status_post(content.get("Post"),
                                         in_reply_to_id=threadid,
                                         media_ids=media_id,
                                         spoiler_text=content.get("CW"),
                                         sensitive=False,
                                         visibility=visibility).get("id")
        return nthreadid
    except Exception as e:
        print("Posting error")
        print(type(e))
        print(e)
        return threadid


def main(config, debug=False):
    if debug:
        print("Debugging: not posting to mastodon")
        mast_usr = None
    else:
        mast_usr = Mastodon(
            access_token = config.get("mastodon_cred"),
            api_base_url = config.get("mastodon_server")
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
    rss_items = rss_root.find('channel').findall('item')
    items_parsed = [parse_item(item) for item in rss_items]
    items_guid = [item.get('guid') for item in items_parsed]
    alert_update = False
    archive_fp = config.get("archive_file")
    if (archive_fp is None or not os.path.isfile(archive_fp)):
        alert_update = True
    else:
        with open(archive_fp, "r") as f:
            archive_dat = json.load(f)
        archive_guid = archive_dat.keys()
        miss_guid = [guid not in archive_guid for guid in items_guid]
        alert_update = False if sum(miss_guid) == 0 else True
    if alert_update:
        sum_p = summary_post(items_parsed, now_time, shp_data=shp_data)
        tid = None
        if debug:
            pprint(sum_p)
        else:
            tid = make_post(sum_p, mast_usr,
                            visibility=config.get('visibility'))
        for item in items_parsed:
            sleep(config.get("wait"))
            item_p = item_post(item, tz=bottz, shp_data=shp_data)
            if debug:
                pprint(item_p)
            else:
                tid = make_post(item_p, mast_usr,
                                visibility=config.get('visibility'),
                                threadid=tid)
        items_dict = {item.get("guid") : item
                      for item in items_parsed
                      if item is not None and
                      item.get("guid") is not None}
        if archive_fp is not None:
            if debug:
                print("Saving to {}".format(archive_fp))
            with open(archive_fp, "w") as f:
                json.dump(items_dict, fp=f)
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
    "visibility": "direct"
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
    args = argparser.parse_args()
    with open(args.config_file, "r") as configfile:
        conf_json = json.load(configfile)
    os.chdir(args.dir)
    main(conf_json, debug=args.debug)

