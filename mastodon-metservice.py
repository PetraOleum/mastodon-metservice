import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import datetime as dt
from pprint import pprint
import geopandas
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
cap_url = "https://alerts.metservice.com/cap/rss"

rss_tree = ET.parse("cap.now.rss")

rss_root = rss_tree.getroot()
rss_items = rss_root.find('channel').findall('item')

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

def item_post(pitem, time_fmt="%-I:%M %p %a %-d %b",
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
                onset.strftime(time_fmt)),
            None if expiry_s is None else "Expires: {}".format(
                expiry.strftime(time_fmt)),
            None if next_update_s is None else "Next update: {}".format(
                next_update.strftime(time_fmt))
            #web
        ]
        text = "\n".join([txt for txt in text_items if txt is not None])
        text_len = len(text)
        if text_len > instance_len:
            text = text[:(instance_len - 1)] + "…"
        elif text_len < instance_len - linklength:
            text = text + "\n" + web
        return {
            "CW": CW_text,
            "Text": text,
        }
    except Exception as e:
        print("Post construction error")
        print(pitem.get('guid'))
        print(e)
        return None


def add_watch_poly(pitem, ax, crs = 2193):
    if pitem.get('polygon') is None:
        return None
    try:
        poly = Polygon([ply.split(",") for ply in pitem["polygon"]])
        #poly = Polygon([list(reversed(ply.split(",")))
        #                for ply in items_parsed[0]["polygon"]])
        poly_colour = pitem.get("ColourCodeHex")
        poly_colour = "#FFFF00" if poly_colour is None else poly_colour
        poly_df = geopandas.GeoDataFrame(crs = "wgs84", geometry = [poly])
        poly_df.to_crs(crs, inplace=True)
        weather_plt = poly_df.plot(ax=ax,
                                   color = poly_colour,
                                   edgecolor = None,
                                   aspect=1)
        print("Done")
        return weather_plt
        #return shp_plt
    except Exception as e:
        print("Polygon error")
        print(pitem.get('guid'))
        print(e)
        return None

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
                                             index=[1])
            poly_df.to_crs(shp_crs, inplace=True)
            weather_plt = poly_df.plot(ax=ax,
                                       color = poly_colour,
                                       edgecolor = None,
                                       aspect=1, alpha=alpha)
            print(pitem.get('guid'))
        fig.savefig(fname, bbox_inches='tight', pad_inches = 0, dpi=200)
        return(fname)
    except Exception as e:
        print("Polygon error")
        print(e)
        return None



items_parsed = [parse_item(item) for item in rss_items]

items_dict = {item.get("guid") : item
              for item in items_parsed
              if item is not None and
              item.get("guid") is not None and
              item.get("status") is not None}
#pprint(items_dict)

#print(parse_item(rss_items[0]))

#items_parsed[0].get("link")
#
#i0_text = get_cap(items_parsed[0].get("link"))
#
#rand_time = '2023-03-07T09:55:21+13:00'
#rand_dt = datetime.fromisoformat(rand_time)

#ip = item_post(items_parsed[0])
#print(ip["CW"])
#print(ip["Text"])
#
#poly = Polygon([ply.split(",") for ply in
#        items_parsed[0]["polygon"]])
#poly = Polygon([list(reversed(ply.split(","))) for ply in
#                items_parsed[0]["polygon"]])
#poly_colour = items_parsed[0].get("ColourCodeHex")
#poly_colour = "#FFFF00" if poly_colour is None else poly_colour

shpf = "lds-nz-coastlines-and-islands-polygons-topo\
-1500k-SHP.zip"

shp_data = geopandas.read_file(shpf)
#shp_crs = shp_data.crs

#poly_df = geopandas.GeoDataFrame(
#    index=[0], crs = "wgs84", geometry = [poly])
#poly_df = poly_df.to_crs(2193)

#fig, ax = plt.subplots()
#
#ax.set_aspect('equal')
#
#shp_plt = shp_data.plot(ax = ax, color = '#FFFFCC', edgecolor=None)
#ax.set_facecolor('#80ccff')
#ax.set_axis_off()
#ax.add_artist(ax.patch)
#ax.patch.set_zorder(-1)

#t_plt = shp_plt

#for item in items_parsed:
#    print(item.get('guid'))
#    t_plt = add_watch_poly(item, t_plt)

#pp = add_watch_poly(items_parsed[0], ax)

#fig.savefig('nz.png')
#plt.savefig('nz.png')


#add_watch_poly(items_parsed[0], shp_plt)

#weather_plt = poly_df.plot(ax=shp_plt, color = poly_colour,
#                           edgecolor = None,
#                           aspect=1)
#shp_plt.set_axis_off()
#weather_plt.set_axis_off()
#weather_plt.add_artist(shp_plt.patch)
#weather_plt.patch.set_zorder(-1)

#t_plt.figure.savefig('nz.png', bbox_inches='tight',
#            pad_inches = 0, dpi=200)

#[item.get('polygon') for item in items_parsed]
add_polys(items_parsed, shp_data, alpha=0.9)

add_polys([items_parsed[2]], shp_data)

items_parsed[3].get('areaDesc') + ".png"

add_polys([items_parsed[3]], shp_data, items_parsed[3].get('areaDesc') +
          ".png")
