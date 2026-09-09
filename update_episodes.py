import urllib.request
import urllib.parse
import json
import re
import time
import xml.etree.ElementTree as ET


# ============================================================
# CONFIGURATION
# ============================================================

PLAYLIST_ID = "PLQgwceUpKnfA"
OUTPUT_FILE = "episodes.json"

PLAYLIST_URL = (
    "https://www.youtube.com/playlist?list="
    + PLAYLIST_ID
)


# ============================================================
# HTTP HELPERS
# ============================================================

def make_request(url, accept="*/*"):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36",

            "Accept": accept,

            "Accept-Language":
                "en-US,en;q=0.9",

            "Cookie":
                "CONSENT=YES+cb"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            return response.read()

    except Exception as error:
        print(
            "[Request] Failed:",
            error
        )

        return None


def request_text(url):
    data = make_request(
        url,
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    )

    if data is None:
        return None

    return data.decode(
        "utf-8",
        errors="ignore"
    )


def request_json(url):
    data = make_request(
        url,
        "application/json,text/plain,*/*"
    )

    if data is None:
        return None

    try:
        return json.loads(
            data.decode(
                "utf-8",
                errors="ignore"
            )
        )

    except Exception as error:
        print(
            "[JSON] Failed to parse response:",
            error
        )

        return None


# ============================================================
# PLAYLIST
# ============================================================

def fetch_playlist():
    print()
    print("[YouTube] Downloading playlist...")

    page = request_text(
        PLAYLIST_URL
    )

    if not page:
        print(
            "[YouTube] Could not download playlist."
        )

        return None

    print(
        f"[YouTube] Downloaded {len(page):,} bytes."
    )

    return page


def extract_video_ids(page):
    if not page:
        return []

    matches = re.findall(
        r'"videoId"\s*:\s*"([A-Za-z0-9_-]{11})"',
        page
    )

    video_ids = []
    seen = set()

    for video_id in matches:

        if video_id in seen:
            continue

        seen.add(
            video_id
        )

        video_ids.append(
            video_id
        )

    print(
        f"[YouTube] Found {len(video_ids)} video(s)."
    )

    return video_ids


# ============================================================
# OEMBED
# ============================================================

def get_oembed(video_id):

    video_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    encoded_url = urllib.parse.quote(
        video_url,
        safe=""
    )

    oembed_url = (
        "https://www.youtube.com/oembed"
        "?url="
        + encoded_url
        + "&format=json"
    )

    print(
        f"[YouTube] Getting oEmbed data for {video_id}..."
    )

    data = request_json(
        oembed_url
    )

    if not data:
        print(
            "[YouTube] oEmbed request failed."
        )

        return None

    title = data.get(
        "title",
        ""
    ).strip()

    thumbnail = data.get(
        "thumbnail_url",
        ""
    ).strip()

    if title:
        print(
            f"[YouTube] oEmbed title: {title}"
        )

    return {
        "title": title,
        "thumbnail": thumbnail
    }


# ============================================================
# RSS DATE LOOKUP
# ============================================================

def get_channel_id(video_id):
    """
    Gets the channel ID associated with a video.

    This is used so we can access the channel RSS feed.
    """

    video_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    print(
        f"[YouTube] Finding channel ID for {video_id}..."
    )

    page = request_text(
        video_url
    )

    if not page:
        return None

    patterns = [

        # Modern YouTube page
        r'"channelId"\s*:\s*"([A-Za-z0-9_-]{24})"',

        # owner profile
        r'"ownerProfileUrl"\s*:\s*"https://www\.youtube\.com/channel/([A-Za-z0-9_-]+)"',

        # channel URL
        r'https://www\.youtube\.com/channel/([A-Za-z0-9_-]{24})'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            page
        )

        if match:
            channel_id = match.group(1)

            print(
                f"[YouTube] Channel ID: {channel_id}"
            )

            return channel_id

    print(
        "[YouTube] Could not find channel ID."
    )

    return None


def get_channel_rss(channel_id):

    rss_url = (
        "https://www.youtube.com/feeds/videos.xml"
        "?channel_id="
        + channel_id
    )

    print(
        "[YouTube] Downloading channel RSS feed..."
    )

    data = make_request(
        rss_url,
        "application/rss+xml,application/xml,text/xml,*/*"
    )

    if not data:
        print(
            "[YouTube] RSS request failed."
        )

        return None

    print(
        f"[YouTube] Downloaded RSS feed "
        f"({len(data):,} bytes)."
    )

    return data


def parse_rss_feed(data):

    if not data:
        return {}

    try:
        root = ET.fromstring(
            data
        )

    except Exception as error:
        print(
            "[RSS] Could not parse RSS feed:",
            error
        )

        return {}

    namespace = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015"
    }

    dates = {}

    entries = root.findall(
        "atom:entry",
        namespace
    )

    print(
        f"[RSS] Found {len(entries)} RSS video(s)."
    )

    for entry in entries:

        video_element = entry.find(
            "yt:videoId",
            namespace
        )

        published_element = entry.find(
            "atom:published",
            namespace
        )

        if (
            video_element is None
            or published_element is None
        ):
            continue

        video_id = (
            video_element.text
            or ""
        ).strip()

        published = (
            published_element.text
            or ""
        ).strip()

        if not video_id or not published:
            continue

        # Convert:
        #
        # 2026-09-08T01:45:57+00:00
        #
        # into:
        #
        # 2026-09-08

        match = re.match(
            r"(20\d{2})-(\d{2})-(\d{2})",
            published
        )

        if not match:
            continue

        date = (
            match.group(1)
            + "-"
            + match.group(2)
            + "-"
            + match.group(3)
        )

        dates[video_id] = date

        print(
            f"[RSS] {video_id} -> {date}"
        )

    return dates


def get_publish_dates(video_ids):

    if not video_ids:
        return {}

    # --------------------------------------------------------
    # First try to find the channel ID from the first video.
    # --------------------------------------------------------

    channel_id = get_channel_id(
        video_ids[0]
    )

    if not channel_id:
        print(
            "[RSS] Unable to determine channel."
        )

        return {}

    # --------------------------------------------------------
    # Download channel RSS feed.
    # --------------------------------------------------------

    rss_data = get_channel_rss(
        channel_id
    )

    if not rss_data:
        return {}

    # --------------------------------------------------------
    # Parse dates.
    # --------------------------------------------------------

    dates = parse_rss_feed(
        rss_data
    )

    # --------------------------------------------------------
    # Only keep dates for videos we actually need.
    # --------------------------------------------------------

    wanted_dates = {}

    for video_id in video_ids:

        if video_id in dates:

            wanted_dates[video_id] = (
                dates[video_id]
            )

    print(
        f"[RSS] Matched "
        f"{len(wanted_dates)}/{len(video_ids)} "
        f"video date(s)."
    )

    return wanted_dates


# ============================================================
# EPISODE NUMBER
# ============================================================

def get_episode_number(title):

    match = re.search(
        r"\b(?:day|episode)\s*#?\s*(\d+)\b",
        title,
        re.IGNORECASE
    )

    if match:

        return int(
            match.group(1)
        )

    return None


# ============================================================
# VIDEO METADATA
# ============================================================

def get_video_metadata(
    video_id,
    playlist_position,
    publish_dates
):

    video_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    # --------------------------------------------------------
    # Get title + thumbnail using oEmbed.
    # --------------------------------------------------------

    oembed = get_oembed(
        video_id
    )

    if oembed:

        title = oembed.get(
            "title",
            ""
        )

        thumbnail = oembed.get(
            "thumbnail",
            ""
        )

    else:

        title = ""
        thumbnail = ""

    # --------------------------------------------------------
    # Fallback title.
    # --------------------------------------------------------

    if not title:

        title = (
            "Daily iiSU News: Day "
            + str(playlist_position)
        )

    # --------------------------------------------------------
    # Fallback thumbnail.
    # --------------------------------------------------------

    if not thumbnail:

        thumbnail = (
            "https://i.ytimg.com/vi/"
            + video_id
            + "/hqdefault.jpg"
        )

    # --------------------------------------------------------
    # Get date from RSS data.
    # --------------------------------------------------------

    date = publish_dates.get(
        video_id,
        ""
    )

    if date:

        print(
            f"[YouTube] Publish date: {date}"
        )

    else:

        print(
            "[YouTube] Publish date not found in RSS."
        )

    # --------------------------------------------------------
    # Get episode number from title.
    # --------------------------------------------------------

    number = get_episode_number(
        title
    )

    if number is None:

        number = playlist_position

    # --------------------------------------------------------
    # Return complete metadata.
    # --------------------------------------------------------

    return {
        "number": number,
        "title": title,
        "date": date,
        "url": video_url,
        "videoId": video_id,
        "thumbnail": thumbnail
    }


# ============================================================
# BUILD DATABASE
# ============================================================

def build_episode_database():

    # --------------------------------------------------------
    # Download playlist.
    # --------------------------------------------------------

    page = fetch_playlist()

    if not page:

        return []

    # --------------------------------------------------------
    # Find videos.
    # --------------------------------------------------------

    video_ids = extract_video_ids(
        page
    )

    if not video_ids:

        print(
            "[YouTube] No videos found."
        )

        return []

    # --------------------------------------------------------
    # Get publication dates in one RSS request.
    # --------------------------------------------------------

    publish_dates = get_publish_dates(
        video_ids
    )

    # --------------------------------------------------------
    # Build episode list.
    # --------------------------------------------------------

    episodes = []

    for position, video_id in enumerate(
        video_ids,
        start=1
    ):

        print()
        print(
            f"[Episode {position}] {video_id}"
        )

        episode = get_video_metadata(
            video_id,
            position,
            publish_dates
        )

        episodes.append(
            episode
        )

        # Small delay to avoid hammering YouTube.
        time.sleep(
            0.5
        )

    # --------------------------------------------------------
    # Sort by episode number.
    # --------------------------------------------------------

    episodes.sort(
        key=lambda episode:
            episode["number"]
    )

    return episodes


# ============================================================
# SAVE DATABASE
# ============================================================

def save_database(episodes):

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            episodes,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print(
        "       DAILY IISU NEWS DATABASE UPDATER"
    )
    print("=" * 60)

    episodes = build_episode_database()

    if not episodes:

        print()
        print(
            "ERROR: No episodes were found."
        )

        print(
            "episodes.json was not changed."
        )

        return

    save_database(
        episodes
    )

    print()
    print(
        f"Saved {len(episodes)} episode(s) "
        f"to {OUTPUT_FILE}"
    )

    print()

    for episode in episodes:

        print(
            f"#{episode['number']} "
            f"{episode['title']} "
            f"— {episode['date']}"
        )

    print()
    print(
        "Done!"
    )

    print()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
