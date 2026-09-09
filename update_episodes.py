import urllib.request
import urllib.parse
import json
import re
import time
from datetime import date, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

PLAYLIST_ID = "PLQgwceUpKnfA"

OUTPUT_FILE = "episodes.json"

# Daily iiSU News Day 1 date.
# Every episode after Day 1 is exactly one calendar day later.
START_DATE = date(2026, 9, 7)

PLAYLIST_URL = (
    "https://www.youtube.com/playlist?list="
    + PLAYLIST_ID
)


# ============================================================
# HTTP REQUEST
# ============================================================

def make_request(
    url,
    accept="*/*"
):

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
    print(
        "[YouTube] Downloading playlist..."
    )

    page = request_text(
        PLAYLIST_URL
    )

    if not page:

        print(
            "[YouTube] Could not download playlist."
        )

        return None

    print(
        f"[YouTube] Downloaded "
        f"{len(page):,} bytes."
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
        f"[YouTube] Found "
        f"{len(video_ids)} video(s)."
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
        f"[YouTube] Getting oEmbed data "
        f"for {video_id}..."
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
            f"[YouTube] oEmbed title: "
            f"{title}"
        )

    return {
        "title": title,
        "thumbnail": thumbnail
    }


# ============================================================
# EPISODE NUMBER
# ============================================================

def get_episode_number(
    title
):

    # Supports:
    #
    # Daily iiSU News: Day 1
    # Daily iiSU News: Day 25
    # Daily iiSU News: Episode 3
    # Daily iiSU News: Episode #4

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
# SMART DATE CALCULATION
# ============================================================

def get_episode_date(
    episode_number
):

    # Day 1 is START_DATE.
    #
    # Day 2 is START_DATE + 1 day.
    # Day 3 is START_DATE + 2 days.
    #
    # timedelta automatically handles:
    #
    # - month lengths
    # - February
    # - leap years
    # - year changes

    calculated_date = (
        START_DATE
        + timedelta(
            days=episode_number - 1
        )
    )

    return calculated_date.isoformat()


# ============================================================
# VIDEO METADATA
# ============================================================

def get_video_metadata(
    video_id,
    playlist_position
):

    video_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    # --------------------------------------------------------
    # Get title + thumbnail.
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
    # Find episode number.
    # --------------------------------------------------------

    number = get_episode_number(
        title
    )

    if number is None:

        number = playlist_position

        print(
            "[Episode] Could not determine "
            "episode number from title."
        )

        print(
            f"[Episode] Using playlist position "
            f"{number}."
        )

    # --------------------------------------------------------
    # Calculate date.
    # --------------------------------------------------------

    episode_date = get_episode_date(
        number
    )

    print(
        f"[Calendar] Day {number} "
        f"-> {episode_date}"
    )

    # --------------------------------------------------------
    # Return metadata.
    # --------------------------------------------------------

    return {
        "number": number,
        "title": title,
        "date": episode_date,
        "url": video_url,
        "videoId": video_id,
        "thumbnail": thumbnail
    }


# ============================================================
# BUILD EPISODE DATABASE
# ============================================================

def build_episode_database():

    # --------------------------------------------------------
    # Download playlist.
    # --------------------------------------------------------

    page = fetch_playlist()

    if not page:

        return []

    # --------------------------------------------------------
    # Extract videos.
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
    # Build metadata.
    # --------------------------------------------------------

    episodes = []

    for position, video_id in enumerate(
        video_ids,
        start=1
    ):

        print()
        print(
            f"[Episode {position}] "
            f"{video_id}"
        )

        episode = get_video_metadata(
            video_id,
            position
        )

        episodes.append(
            episode
        )

        # Small delay between oEmbed requests.
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

def save_database(
    episodes
):

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
    print(
        "=" * 60
    )

    print(
        "       DAILY IISU NEWS DATABASE UPDATER"
    )

    print(
        "=" * 60
    )

    print()
    print(
        "[Calendar] Series start date:",
        START_DATE.isoformat()
    )

    print(
        "[Calendar] Day 1 =",
        START_DATE.isoformat()
    )

    print()

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

    # --------------------------------------------------------
    # Save.
    # --------------------------------------------------------

    save_database(
        episodes
    )

    # --------------------------------------------------------
    # Summary.
    # --------------------------------------------------------

    print()
    print(
        "=" * 60
    )

    print(
        f"Saved {len(episodes)} episode(s) "
        f"to {OUTPUT_FILE}"
    )

    print(
        "=" * 60
    )

    print()

    for episode in episodes:

        print(
            f"#{episode['number']} "
            f"{episode['date']} "
            f"— {episode['title']}"
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
