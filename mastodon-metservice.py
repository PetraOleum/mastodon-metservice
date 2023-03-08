import xml.etree.ElementTree as ET
import requests
from pprint import pprint
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
        print(params)
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

def item_post(pitem):
    try:
        CW_items = [
            pitem.get('headline'),
            pitem.get('areaDesc')
        ]
        [cwitem for cwitem in CW_items if cwitem is not None]
        CW_text = None if len(cwitem) == 0 else " - ".join(CW_items)
        sev_text = pitem.get('severity')
        desc_text = pitem.get('cap_description')
        cert_text = pitem.get('certainty')
        onset = pitem.get('onset')
    except Exception as e:
        print("Post construction error")
        print(pitem.get('guid'))
        print(e)
        return None

items_parsed = [parse_item(item) for item in rss_items]

items_dict = {item.get("guid") : item
              for item in items_parsed
              if item is not None and
              item.get("guid") is not None and
              item.get("status") is not None}
pprint(items_dict)

print(parse_item(rss_items[0]))

items_parsed[0].get("link")

i0_text = get_cap(items_parsed[0].get("link"))
