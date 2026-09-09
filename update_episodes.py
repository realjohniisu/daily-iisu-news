import urllib.request
import urllib.parse
import json
import re
import html
import time


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
        f"[YouTube] Downloaded {len(page):,} bytes."
    )

    return page


# ============================================================
# EXTRACT ytInitialData
# ============================================================

def extract_initial_data(page):

    if not page:
        return None

    patterns = [

        # Modern YouTube
        r'var\s+ytInitialData\s*=\s*(\{.*?\})\s*;',

        # Alternate form
        r'window\["ytInitialData"\]\s*=\s*(\{.*?\})\s*;',

        # Another form used by YouTube
        r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayerResponse"',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            page,
            re.DOTALL
        )

        if not match:
            continue

        raw_json = match.group(1)

        try:

            data = json.loads(
                raw_json
            )

            print(
                "[YouTube] Successfully extracted ytInitialData."
            )

            return data

        except json.JSONDecodeError:

            # ------------------------------------------------
            # Regex can stop at the wrong closing brace
            # because YouTube's JSON is enormous.
            #
            # Try a balanced-brace extraction instead.
            # ------------------------------------------------

            pass

    # --------------------------------------------------------
    # Balanced JSON extraction.
    # --------------------------------------------------------

    markers = [
        "var ytInitialData = ",
        'window["ytInitialData"] = ',
        "ytInitialData = "
    ]

    for marker in markers:

        start = page.find(
            marker
        )

        if start == -1:
            continue

        start += len(
            marker
        )

        while (
            start < len(page)
            and page[start].isspace()
        ):
            start += 1

        if (
            start >= len(page)
            or page[start] != "{"
        ):
            continue

        depth = 0
        in_string = False
        escaped = False

        for index in range(
            start,
            len(page)
        ):

            character = page[index]

            if in_string:

                if escaped:

                    escaped = False

                elif character == "\\":

                    escaped = True

                elif character == '"':

                    in_string = False

                continue

            if character == '"':

                in_string = True

                continue

            if character == "{":

                depth += 1

            elif character == "}":

                depth -= 1

                if depth == 0:

                    raw_json = page[
                        start:index + 1
                    ]

                    try:

                        data = json.loads(
                            raw_json
                        )

                        print(
                            "[YouTube] Successfully extracted "
                            "ytInitialData."
                        )

                        return data

                    except json.JSONDecodeError as error:

                        print(
                            "[YouTube] ytInitialData JSON "
                            "could not be parsed:",
                            error
                        )

                        return None

    print(
        "[YouTube] ytInitialData was not found."
    )

    return None


# ============================================================
# RECURSIVE VIDEO SEARCH
# ============================================================

def find_video_entries(
    value,
    results=None
):

    if results is None:

        results = {}

    if isinstance(
        value,
        dict
    ):

        # ----------------------------------------------------
        # Look for objects containing a videoId.
        # ----------------------------------------------------

        video_id = value.get(
            "videoId"
        )

        if (
            isinstance(
                video_id,
                str
            )
            and re.fullmatch(
                r"[A-Za-z0-9_-]{11}",
                video_id
            )
        ):

            results.setdefault(
                video_id,
                []
            ).append(
                value
            )

        # ----------------------------------------------------
        # Continue recursively.
        # ----------------------------------------------------

        for child in value.values():

            find_video_entries(
                child,
                results
            )

    elif isinstance(
        value,
        list
    ):

        for child in value:

            find_video_entries(
                child,
                results
            )

    return results


# ============================================================
# DATE PARSING
# ============================================================

def date_from_iso(value):

    if not isinstance(
        value,
        str
    ):
        return ""

    value = html.unescape(
        value
    ).strip()

    match = re.search(
        r"(20\d{2})-(\d{1,2})-(\d{1,2})",
        value
    )

    if not match:
        return ""

    return (
        match.group(1)
        + "-"
        + match.group(2).zfill(2)
        + "-"
        + match.group(3).zfill(2)
    )


def date_from_text(value):

    if not isinstance(
        value,
        str
    ):
        return ""

    value = html.unescape(
        value
    ).strip()

    # --------------------------------------------------------
    # ISO date
    # --------------------------------------------------------

    date = date_from_iso(
        value
    )

    if date:
        return date

    # --------------------------------------------------------
    # Formats such as:
    #
    # Sep 7, 2026
    # September 7, 2026
    # --------------------------------------------------------

    match = re.search(
        r"\b"
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
        r"Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)"
        r"\s+"
        r"(\d{1,2}),"
        r"\s+"
        r"(20\d{2})"
        r"\b",
        value,
        re.IGNORECASE
    )

    if match:

        months = {
            "jan": "01",
            "january": "01",
            "feb": "02",
            "february": "02",
            "mar": "03",
            "march": "03",
            "apr": "04",
            "april": "04",
            "may": "05",
            "jun": "06",
            "june": "06",
            "jul": "07",
            "july": "07",
            "aug": "08",
            "august": "08",
            "sep": "09",
            "september": "09",
            "oct": "10",
            "october": "10",
            "nov": "11",
            "november": "11",
            "dec": "12",
            "december": "12"
        }

        month = months.get(
            match.group(1).lower()
        )

        if month:

            return (
                match.group(3)
                + "-"
                + month
                + "-"
                + match.group(2).zfill(2)
            )

    return ""


# ============================================================
# EXTRACT DATES FROM PLAYLIST DATA
# ============================================================

def extract_playlist_dates(
    initial_data,
    video_ids
):

    print()
    print(
        "[YouTube] Searching playlist embedded data for dates..."
    )

    entries = find_video_entries(
        initial_data
    )

    dates = {}

    for video_id in video_ids:

        candidates = entries.get(
            video_id,
            []
        )

        found_date = ""

        for entry in candidates:

            # ------------------------------------------------
            # First check explicit date-like fields.
            # ------------------------------------------------

            date_fields = [
                "publishedAt",
                "publishDate",
                "uploadDate",
                "publishedTime"
            ]

            for field in date_fields:

                if field not in entry:
                    continue

                found_date = date_from_iso(
                    entry[field]
                )

                if found_date:
                    break

            if found_date:
                break

            # ------------------------------------------------
            # Check publishedTimeText.
            # ------------------------------------------------

            published_text = entry.get(
                "publishedTimeText"
            )

            if isinstance(
                published_text,
                dict
            ):

                text = published_text.get(
                    "simpleText",
                    ""
                )

                found_date = date_from_text(
                    text
                )

                if found_date:
                    break

            # ------------------------------------------------
            # Check accessibility label.
            #
            # YouTube sometimes puts the absolute-looking
            # date information into aria-label text.
            # ------------------------------------------------

            accessibility = entry.get(
                "accessibility"
            )

            if isinstance(
                accessibility,
                dict
            ):

                accessibility_data = (
                    accessibility.get(
                        "accessibilityData",
                        {}
                    )
                )

                if isinstance(
                    accessibility_data,
                    dict
                ):

                    label = accessibility_data.get(
                        "label",
                        ""
                    )

                    found_date = date_from_text(
                        label
                    )

                    if found_date:
                        break

            # ------------------------------------------------
            # Check title accessibility information.
            # ------------------------------------------------

            title = entry.get(
                "title"
            )

            if isinstance(
                title,
                dict
            ):

                runs = title.get(
                    "runs",
                    []
                )

                combined = " ".join(
                    run.get(
                        "text",
                        ""
                    )
                    for run in runs
                    if isinstance(
                        run,
                        dict
                    )
                )

                found_date = date_from_text(
                    combined
                )

                if found_date:
                    break

        if found_date:

            dates[video_id] = found_date

            print(
                f"[YouTube] {video_id} -> {found_date}"
            )

        else:

            print(
                f"[YouTube] {video_id} -> "
                "date not found in embedded data"
            )

    print(
        f"[YouTube] Found dates for "
        f"{len(dates)}/{len(video_ids)} video(s)."
    )

    return dates


# ============================================================
# VIDEO IDS
# ============================================================

def extract_video_ids(
    page
):

    initial_data = extract_initial_data(
        page
    )

    if initial_data:

        entries = find_video_entries(
            initial_data
        )

        video_ids = list(
            entries.keys()
        )

        if video_ids:

            print(
                f"[YouTube] Found "
                f"{len(video_ids)} video(s) "
                "from embedded data."
            )

            return video_ids, initial_data

    # --------------------------------------------------------
    # Fallback to the old regex method.
    # --------------------------------------------------------

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
        f"{len(video_ids)} video(s) "
        "using fallback extraction."
    )

    return video_ids, initial_data


# ============================================================
# OEMBED
# ============================================================

def get_oembed(
    video_id
):

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
        f"[YouTube] Getting oEmbed data for "
        f"{video_id}..."
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
    # oEmbed
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
    # Fallback title
    # --------------------------------------------------------

    if not title:

        title = (
            "Daily iiSU News: Day "
            + str(playlist_position)
        )

    # --------------------------------------------------------
    # Fallback thumbnail
    # --------------------------------------------------------

    if not thumbnail:

        thumbnail = (
            "https://i.ytimg.com/vi/"
            + video_id
            + "/hqdefault.jpg"
        )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    date = publish_dates.get(
        video_id,
        ""
    )

    if date:

        print(
            f"[YouTube] Publish date: "
            f"{date}"
        )

    else:

        print(
            "[YouTube] Publish date not found."
        )

    # --------------------------------------------------------
    # Episode number
    # --------------------------------------------------------

    number = get_episode_number(
        title
    )

    if number is None:

        number = playlist_position

    # --------------------------------------------------------
    # Return
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

    page = fetch_playlist()

    if not page:

        return []

    video_ids, initial_data = extract_video_ids(
        page
    )

    if not video_ids:

        print(
            "[YouTube] No videos found."
        )

        return []

    # --------------------------------------------------------
    # Get dates directly from playlist data.
    # --------------------------------------------------------

    if initial_data:

        publish_dates = extract_playlist_dates(
            initial_data,
            video_ids
        )

    else:

        publish_dates = {}

    # --------------------------------------------------------
    # Build episodes.
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
            position,
            publish_dates
        )

        episodes.append(
            episode
        )

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
