import urllib.request
import json
import re
import html
import time
from html.parser import HTMLParser

PLAYLIST_ID = "PLQgwceUpKnfA"
OUTPUT_FILE = "episodes.json"

PLAYLIST_URL = (
    "https://www.youtube.com/playlist?list="
    + PLAYLIST_ID
)


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = []
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag.lower() == "meta":
            self.meta.append(attrs)

        elif tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def youtube_request(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36",

            "Accept":
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",

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
            return response.read().decode(
                "utf-8",
                errors="ignore"
            )

    except Exception as error:
        print(
            "[YouTube] Request failed:",
            error
        )

        return None


def fetch_playlist():
    print()
    print("[YouTube] Downloading playlist...")

    page = youtube_request(
        PLAYLIST_URL
    )

    if not page:
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

        seen.add(video_id)
        video_ids.append(video_id)

    print(
        f"[YouTube] Found {len(video_ids)} video(s)."
    )

    return video_ids


def parse_page(page):
    parser = MetaParser()

    parser.feed(page)

    return parser


def get_meta(parser, key, value):
    for meta in parser.meta:
        if (
            meta.get(key, "").lower()
            == value.lower()
        ):
            content = meta.get("content")

            if content:
                return html.unescape(
                    content
                ).strip()

    return ""


def get_video_metadata(video_id):
    video_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    print(
        f"[YouTube] Reading {video_id}..."
    )

    page = youtube_request(
        video_url
    )

    if not page:
        return {
            "number": None,
            "title": "Daily iiSU News",
            "date": "",
            "url": video_url,
            "videoId": video_id,
            "thumbnail":
                f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        }

    parser = parse_page(page)

    title = get_meta(
        parser,
        "property",
        "og:title"
    )

    if not title:
        title = parser.title.strip()

    if not title:
        match = re.search(
            r'"videoDetails"\s*:\s*\{.*?"title"\s*:\s*"([^"]+)"',
            page,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            title = html.unescape(
                match.group(1)
            )

    if not title:
        title = "Daily iiSU News"

    title = re.sub(
        r"\s*-\s*YouTube\s*$",
        "",
        title,
        flags=re.IGNORECASE
    ).strip()

    date = get_meta(
        parser,
        "itemprop",
        "datePublished"
    )

    if not date:
        date = get_meta(
            parser,
            "itemprop",
            "uploadDate"
        )

    if not date:
        match = re.search(
            r'"publishDate"\s*:\s*"([^"]+)"',
            page,
            re.IGNORECASE
        )

        if match:
            date = match.group(1)

    if not date:
        match = re.search(
            r'"uploadDate"\s*:\s*"([^"]+)"',
            page,
            re.IGNORECASE
        )

        if match:
            date = match.group(1)

    date_match = re.search(
        r"(20\d{2})-(\d{1,2})-(\d{1,2})",
        date
    )

    if date_match:
        date = (
            date_match.group(1)
            + "-"
            + date_match.group(2).zfill(2)
            + "-"
            + date_match.group(3).zfill(2)
        )
    else:
        date = ""

    thumbnail = get_meta(
        parser,
        "property",
        "og:image"
    )

    if not thumbnail:
        thumbnail = (
            "https://i.ytimg.com/vi/"
            + video_id
            + "/hqdefault.jpg"
        )

    number = None

    number_match = re.search(
        r"(?:#|episode|day)\s*(\d+)",
        title,
        re.IGNORECASE
    )

    if number_match:
        number = int(
            number_match.group(1)
        )

    return {
        "number": number,
        "title": title,
        "date": date,
        "url": video_url,
        "videoId": video_id,
        "thumbnail": thumbnail
    }


def build_episode_database():
    page = fetch_playlist()

    if not page:
        print(
            "[YouTube] Could not download playlist."
        )

        return []

    video_ids = extract_video_ids(
        page
    )

    if not video_ids:
        print(
            "[YouTube] No videos found."
        )

        return []

    episodes = []

    for index, video_id in enumerate(video_ids):
        episode = get_video_metadata(
            video_id
        )

        if episode["number"] is None:
            episode["number"] = index + 1

        episodes.append(
            episode
        )

        time.sleep(0.15)

    episodes.sort(
        key=lambda episode:
            episode["number"]
    )

    return episodes


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


def main():
    print()
    print("=" * 60)
    print("       DAILY IISU NEWS DATABASE UPDATER")
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


if __name__ == "__main__":
    main()
