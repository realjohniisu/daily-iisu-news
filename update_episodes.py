import urllib.request
import urllib.parse
import json
import re
import html
import time

PLAYLIST_ID = "PLQgwceUpKnfA"
OUTPUT_FILE = "episodes.json"

PLAYLIST_URL = (
    "https://www.youtube.com/playlist?list="
    + PLAYLIST_ID
)


def request_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36",
            "Accept":
                "application/json,text/plain,*/*",
            "Accept-Language":
                "en-US,en;q=0.9"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:
            return json.loads(
                response.read().decode(
                    "utf-8",
                    errors="ignore"
                )
            )

    except Exception as error:
        print(
            "[Request] Failed:",
            error
        )

        return None


def request_text(url):
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

    page = request_text(
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
    )

    thumbnail = data.get(
        "thumbnail_url",
        ""
    )

    if title:
        print(
            f"[YouTube] oEmbed title: {title}"
        )

    return {
        "title": title.strip(),
        "thumbnail": thumbnail.strip()
    }


def get_publish_date(video_id):
    video_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    print(
        f"[YouTube] Getting publish date for {video_id}..."
    )

    page = request_text(
        video_url
    )

    if not page:
        return ""

    patterns = [
        r'<meta[^>]+itemprop=["\']datePublished["\'][^>]+content=["\']([^"\']+)["\'][^>]*>',

        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+itemprop=["\']datePublished["\'][^>]*>',

        r'"publishDate"\s*:\s*"([^"]+)"'
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            page,
            re.IGNORECASE
        )

        if not match:
            continue

        date_value = html.unescape(
            match.group(1)
        ).strip()

        date_match = re.search(
            r"(20\d{2})-(\d{1,2})-(\d{1,2})",
            date_value
        )

        if date_match:
            date = (
                date_match.group(1)
                + "-"
                + date_match.group(2).zfill(2)
                + "-"
                + date_match.group(3).zfill(2)
            )

            print(
                f"[YouTube] Publish date: {date}"
            )

            return date

    print(
        "[YouTube] Publish date not found."
    )

    return ""


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


def get_video_metadata(video_id, playlist_position):
    video_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    oembed = get_oembed(
        video_id
    )

    if oembed:
        title = oembed["title"]
        thumbnail = oembed["thumbnail"]
    else:
        title = ""
        thumbnail = ""

    if not title:
        title = (
            "Daily iiSU News: Day "
            + str(playlist_position)
        )

    if not thumbnail:
        thumbnail = (
            "https://i.ytimg.com/vi/"
            + video_id
            + "/hqdefault.jpg"
        )

    date = get_publish_date(
        video_id
    )

    number = get_episode_number(
        title
    )

    if number is None:
        number = playlist_position

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
            position
        )

        episodes.append(
            episode
        )

        time.sleep(
            0.5
        )

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
