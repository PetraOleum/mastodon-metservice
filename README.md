# Mastodon Metservice Alerts

Mastodon bot that posts NZ weather alerts from the [metservice.com](https://metservice.com) [Commong Alerting Protocol (CAP) feed](https://www.metservice.com/about/common-alerting-protocol).

# Running

To run this bot yourself you would probably need:

* A mastodon account, e.g. on [botsin.space](https://botsin.space) (if on another server you will need to update `config.json`)
* An app registered for that account (you can do this from the development settings) and the access token associated with that app saved in `nzweather_usercred.secret` or a similar file
* A shapefile of New Zealand (I am using [LINZ's 1:500 coastlines and islands](https://data.linz.govt.nz/layer/51560-nz-coastlines-and-islands-polygons-topo-1500k/) file, exported in [EPSG:2193](https://epsg.io/2193), as it is only 1.2MB, but if you can find a smaller one that's only for the better). The file name needs to be updated in the `config.json` file
* The packages listed in `requirements.txt` installed, ideally in a python3 virtual environment
* You will probably want to change the visibility option in the config from 'direct' to 'public', 'unlisted', or 'private', and adjust the wait time (in seconds)

The bot can be run with `python3 mastodon-metservice.py` with no future arguments, but running in `cron` (dealing with working directories, virtual environments, logging etc) requires a mess like:

```cron
*/5 * * * * /home/petra/mastodon-metservice/venv/bin/python /home/petra/mastodon-metservice/mastodon-metservice.py --config=/home/petra/mastodon-metservice/config.json --dir="/home/petra/mastodon-metservice" >> /home/petra/weatherbot-log.txt 2>&1
```

If run with `--debug` the bot will not connect to Mastodon or post but instead prints to stdout, and therefore does not need valid user credentials. However it still needs the [mastodon.py](https://mastodonpy.readthedocs.io/en/stable/index.html) package to be loaded.

## Configuration

The config file is at `config.json` although another file can be specified with `--config=<path to file>`. The options are, in no particular order:

* `shape_file`: Path to a shape file to use as the outline in the maps
* `tz`: Name of the timezone used to give times and dates
* `wait`: Number of seconds to wait between posts, to avoid completely clogging timelines when large numbers of alerts are being updated
* `full_map`: File name to use to temporarily save the summary map
* `alert_map`: File name to use to temporarily save the individual alert maps between generation and posting
* `rss_url`: URL of the rss CAP feed 
* `website_url`: URL to direct users for more information (currently unused, and instead taken from the feed for each individual alert)
* `archive_file`: JSON file used to save the most recently updated information - currently only used for the list of guids for comparison with most recent rss load
* `mastodon_server`: URL of the mastodon server the account is located on
* `mastodon_cred`: file path to the user secret file for the bot; can also just contain the secret directly (not recommended)
* `visibility`: Post visibility on mastodon, one of 'public', 'unlisted', 'private', or 'direct', for the main (summary) post
* `secondary_visibility`: Post visibility of replies to the main post, i.e. details of individual warnings and watches. Recommended to be unlisted.

# Adapting

This bot can probably be adapted to another CAP feed relatively easily, assuming they use a similar format to metservice, but I don't think it would work out of the box - I may try this myself at a later date. In particular the RSS url is specified in the config file.

