"""Build data/titles.csv: one row per new Netflix release, with week-1 and follow-up views.

Also writes data/list_entry_bar.csv: how many views tenth place took on each weekly list.

Sources (both public, both from Netflix):
- the weekly global Top 10 file, one row per title per week it was listed
- the four half-year "What We Watched" engagement reports, July 2024 to June 2026

Run from the repo root, after get_data.sh:  python src/prep.py
"""

import re
import unicodedata

import numpy as np
import pandas as pd

# Each report covers one half-year. A title is a "new release" in the half it premiered in.
HALF_YEARS = {
    "2024H2": ("2024-07-01", "2024-12-31"),
    "2025H1": ("2025-01-01", "2025-06-30"),
    "2025H2": ("2025-07-01", "2025-12-31"),
    "2026H1": ("2026-01-01", "2026-06-30"),
}
NEXT_HALF_YEAR = {"2024H2": "2025H1", "2025H1": "2025H2", "2025H2": "2026H1"}

# Titles whose name differs between a report and the Top 10 file. Each one was checked by hand:
# same release date, same content type, and no other title it could be confused with.
# The key is the report's match key, the value is the Top 10 file's match key.
RENAMED_TITLES = {
    # Film "Mary" (released 2024-12-06) is listed as "Mary Mother of Jesus" in the Top 10.
    "mary": "mary mother of jesus",
    # "Fake Profile: Killer Match" (2025-01-08) is listed as "Fake Profile: Season 2".
    "fake profile: killer match|1": "fake profile|2",
    # "The Bad Guys: Breaking In: Season 1" (2025-11-06) is listed as
    # "The Bad Guys: The Series: Season 1", and the 2026H1 report uses that name too.
    "the bad guys: breaking in|1": "the bad guys: the series|1",
}

# Netflix writes a star after the runtime of a live program, for example "4:16*".
# Netflix does not document the star. I checked the 283 starred rows by title: all are
# live broadcasts (WWE shows, boxing, award shows, live specials).
STARRED_RUNTIME = re.compile(r"^\d+:\d+\*$")

# Some live rows have no starred runtime, so the star alone would miss them:
# a few weekly WWE episodes, the 2024 NFL Christmas games and one baseball game.
# These patterns name series in which every dated row is a live broadcast.
LIVE_SERIES = re.compile(
    r"^Raw: \w+ \d+, \d{4}$"
    r"|^WWE SmackDown: \w+ \d+, \d{4}$"
    r"|^WWE NXT: "
    r"|^Christmas Gameday: "
    r"|World Baseball Classic"
)

# Live events that the two rules above do not catch, added by hand.
LIVE_BY_HAND = {
    # Live hot-dog eating contest on 2024-09-02. The 2024H2 report gives it a plain runtime.
    "Chestnut vs. Kobayashi: Unfinished Beef",
}

# A runtime that is only "*" means Netflix gives no runtime. For rows without a season this
# is a live sports event (boxing cards, NFL, baseball, Formula 1). The one exception is below.
NO_RUNTIME_BUT_NOT_LIVE = {
    # Scripted series released in three parts. It has no season suffix in the report.
    "Stranger Things 5",
}

# WWE archive shows and recaps, for example "WWE WrestleMania: 1998" or "Royal Rumble: 2006".
# Netflix dates most of them 2025-01-01, the day the WWE library arrived. They are not live
# and they are not new programs, so the notebook reports coverage with and without them.
# The docuseries "WWE: Unreal" is a regular series and does not match.
WWE_LIBRARY = re.compile(r"^(?:WWE [\w ]+|Royal Rumble|Backlash): \d{4}$|^Raw Weekly Recap")

SEASON_SUFFIX = re.compile(r":\s*(?:season\s*(\d+)|limited series|s(\d+)(?::.*)?)\s*$", re.I)
SEASON_WORD = re.compile(r": Season \d+|: Limited Series", re.I)

# Episodes of a staggered season are still being added after week 1.
STAGGERED_RUNTIME_RATIO = 0.9

OUTPUT_COLUMNS = [
    "half",
    "type",
    "title",
    "available_globally",
    "release",
    "weekday",
    "window_end",
    "days_in_window",
    "hours",
    "runtime",
    "report_runtime_hours",
    "views",
    "status",
    "lang",
    "segment",
    "live",
    "wwe_library",
    "wk1_end",
    "days_live_wk1",
    "wk1_rank",
    "wk1_hours",
    "wk1_runtime_hours",
    "wk1_views",
    "wk2_views",
    "runtime_ratio",
    "staggered",
    "first_top10",
    "weeks_in_top10",
    "next_hours",
    "next_views",
]


def normalize_title(title):
    """Lower-case a title, keep the English part before '//', and unify quotes and spaces."""
    text = str(title).split("//")[0]
    text = unicodedata.normalize("NFKC", text)
    replacements = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def split_show_and_season(title):
    """Return (show name, season number). 'Limited Series' and no suffix both count as 1."""
    text = normalize_title(title)
    match = SEASON_SUFFIX.search(text)
    if match is None:
        return text, 1
    season_number = match.group(1) or match.group(2) or 1
    show_name = text[: match.start()].strip()
    return show_name, int(season_number)


def match_key(content_type, title):
    """Key used to join the two sources: the title for films, 'show|season' for series."""
    if content_type == "Film":
        return normalize_title(title)
    show_name, season_number = split_show_and_season(title)
    return f"{show_name}|{season_number}"


def runtime_to_hours(runtime_text):
    """Turn a report runtime such as '7:10' or '4:16*' into hours. Return NaN if there is none."""
    match = re.match(r"^(\d+):(\d+)\*?$", str(runtime_text).strip())
    if match is None:
        return np.nan
    hours = int(match.group(1))
    minutes = int(match.group(2))
    return hours + minutes / 60


def load_reports(folder):
    """Read the four engagement reports into one table, one row per title per half-year."""
    sheets = []
    for half, (window_start, window_end) in HALF_YEARS.items():
        workbook = pd.ExcelFile(f"{folder}/wwh_{half}.xlsx")
        for sheet_name in workbook.sheet_names:
            sheet = pd.read_excel(workbook, sheet_name, header=5)
            sheet = sheet.dropna(axis=1, how="all")
            # The series sheet is called "TV" in the first report and "Shows" afterwards.
            sheet["type"] = "TV" if sheet_name in ("TV", "Shows") else "Film"
            sheet["half"] = half
            sheet["window_start"] = pd.Timestamp(window_start)
            sheet["window_end"] = pd.Timestamp(window_end)
            sheets.append(sheet)
    reports = pd.concat(sheets, ignore_index=True)
    reports = reports.rename(
        columns={
            "Title": "title",
            "Available Globally?": "available_globally",
            "Release Date": "release",
            "Hours Viewed": "hours",
            "Runtime": "runtime",
            "Views": "views",
        }
    )
    reports["release"] = pd.to_datetime(reports["release"], errors="coerce")
    reports["hours"] = pd.to_numeric(reports["hours"], errors="coerce")
    reports["views"] = pd.to_numeric(reports["views"], errors="coerce")
    # Footnote rows and the "Other Movies" / "Other Shows" totals have no views. Drop them.
    reports = reports.dropna(subset=["title", "views"])
    reports["key"] = [match_key(t, name) for t, name in zip(reports["type"], reports["title"])]
    reports["key"] = reports["key"].replace(RENAMED_TITLES)
    return reports.reset_index(drop=True)


def load_top10(path):
    """Read the weekly global Top 10 file. 'week' is the Sunday that closes a Mon-Sun week."""
    top10 = pd.read_csv(path, sep="\t")
    top10["week"] = pd.to_datetime(top10["week"])
    is_tv = top10["category"].str.startswith("TV")
    is_non_english = top10["category"].str.contains("Non-English")
    top10["type"] = np.where(is_tv, "TV", "Film")
    top10["lang"] = np.where(is_non_english, "Non-English", "English")
    has_season = top10["season_title"].notna() & (top10["season_title"] != "N/A")
    top10["full_title"] = np.where(has_season, top10["season_title"], top10["show_title"])
    return top10


def top10_with_match_keys(top10):
    """Give each Top 10 row two keys: from the season title, and from show name plus season.

    The second key catches seasons with a subtitle, such as 'Love Is Blind: S7: Washington D.C.',
    where the report only says 'Love Is Blind: Season 7'.
    """
    by_full_title = top10.copy()
    by_full_title["key"] = [
        match_key(t, name) for t, name in zip(top10["type"], top10["full_title"])
    ]
    by_show_name = top10.copy()
    show_keys = []
    for content_type, show_title, full_title in zip(
        top10["type"], top10["show_title"], top10["full_title"]
    ):
        if content_type == "Film":
            show_keys.append(normalize_title(full_title))
        else:
            season_number = split_show_and_season(full_title)[1]
            show_keys.append(f"{normalize_title(show_title)}|{season_number}")
    by_show_name["key"] = show_keys
    both = pd.concat([by_full_title, by_show_name])
    return both.drop_duplicates(["week", "category", "weekly_rank", "key"])


def select_new_releases(reports):
    """Keep titles that premiered inside their report's half-year."""
    premiered_in_window = (reports["release"] >= reports["window_start"]) & (
        reports["release"] <= reports["window_end"]
    )
    titles = reports[premiered_in_window].copy().reset_index(drop=True)
    titles["title_id"] = titles.index
    titles["days_in_window"] = (titles["window_end"] - titles["release"]).dt.days + 1
    titles["weekday"] = titles["release"].dt.day_name()
    titles["report_runtime_hours"] = titles["runtime"].map(runtime_to_hours)
    # When Netflix gives no runtime, use the one its own views imply: hours / views.
    implied_runtime = titles["hours"] / titles["views"]
    titles["report_runtime_hours"] = titles["report_runtime_hours"].fillna(implied_runtime)
    return titles


def match_top10_weeks(titles, top10):
    """Return one row per (title, Top 10 week) for weeks on or after release, inside the window."""
    keyed_top10 = top10_with_match_keys(top10)
    top10_columns = [
        "key",
        "type",
        "week",
        "lang",
        "weekly_rank",
        "weekly_views",
        "weekly_hours_viewed",
        "runtime",
    ]
    title_columns = ["title_id", "key", "type", "release", "window_end"]
    weeks = titles[title_columns].merge(
        keyed_top10[top10_columns], on=["key", "type"], suffixes=("", "_top10")
    )
    # A week that ends up to six days after the window still starts inside it.
    last_week_allowed = weeks["window_end"] + pd.Timedelta(days=6)
    in_window = (weeks["week"] >= weeks["release"]) & (weeks["week"] <= last_week_allowed)
    weeks = weeks[in_window].copy()
    weeks["days_after_release"] = (weeks["week"] - weeks["release"]).dt.days
    return weeks.sort_values(["title_id", "week"])


def add_top10_history(titles, weeks):
    """Add week-1 and week-2 figures and the first week each title was listed."""
    # Week 1 is the Mon-Sun week that contains the release day: its Sunday is 0-6 days later.
    week1 = weeks[weeks["days_after_release"].between(0, 6)]
    week1 = week1.groupby("title_id").first()
    week1 = week1.rename(
        columns={
            "week": "wk1_end",
            "weekly_rank": "wk1_rank",
            "weekly_views": "wk1_views",
            "weekly_hours_viewed": "wk1_hours",
            "runtime": "wk1_runtime_hours",
        }
    )
    week1_columns = ["wk1_end", "lang", "wk1_rank", "wk1_views", "wk1_hours", "wk1_runtime_hours"]

    week2 = weeks[weeks["days_after_release"].between(7, 13)]
    week2 = week2.groupby("title_id")["weekly_views"].first().rename("wk2_views")

    ever_listed = weeks.groupby("title_id").agg(
        first_top10=("week", "min"),
        weeks_in_top10=("week", "nunique"),
        lang_any_week=("lang", "first"),
    )

    titles = titles.join(week1[week1_columns], on="title_id")
    titles = titles.join(week2, on="title_id")
    titles = titles.join(ever_listed, on="title_id")
    titles["lang"] = titles["lang"].fillna(titles["lang_any_week"])
    titles["days_live_wk1"] = (titles["wk1_end"] - titles["release"]).dt.days + 1
    titles["status"] = "Never in Top 10"
    titles.loc[titles["first_top10"].notna(), "status"] = "Entered Top 10 later"
    titles.loc[titles["wk1_views"].notna(), "status"] = "Top 10 in week 1"
    return titles


def add_staggered_flag(titles):
    """Flag series whose week-1 views use a shorter runtime than their report views.

    The Top 10 divides week-1 hours by the runtime released so far. The report divides by the
    full season. When episodes arrive in batches the two runtimes differ, so the two view
    counts are not on the same scale.
    """
    # The Top 10 file lists a runtime of 0 for a few weekly series. Use the implied one.
    listed_runtime = titles["wk1_runtime_hours"]
    implied_runtime = titles["wk1_hours"] / titles["wk1_views"]
    runtime_missing = listed_runtime.isna() | (listed_runtime <= 0)
    titles["wk1_runtime_hours"] = listed_runtime.where(~runtime_missing, implied_runtime)
    titles["runtime_ratio"] = titles["wk1_runtime_hours"] / titles["report_runtime_hours"]
    is_series = titles["type"] == "TV"
    shorter_runtime = titles["runtime_ratio"] < STAGGERED_RUNTIME_RATIO
    titles["staggered"] = is_series & ~titles["live"] & shorter_runtime
    return titles


def add_live_flags(titles):
    """Flag live events and WWE library rows. Each rule is explained next to its constant."""
    runtime_text = titles["runtime"].astype(str).str.strip()
    is_series_sheet = titles["type"] == "TV"
    has_season = titles["title"].str.contains(SEASON_WORD)

    starred_runtime = runtime_text.str.match(STARRED_RUNTIME)
    live_series = titles["title"].str.contains(LIVE_SERIES)
    listed_by_hand = titles["title"].isin(LIVE_BY_HAND)
    no_runtime = runtime_text == "*"
    not_live_exception = titles["title"].isin(NO_RUNTIME_BUT_NOT_LIVE)
    event_without_runtime = no_runtime & ~has_season & ~not_live_exception

    any_live_rule = starred_runtime | live_series | listed_by_hand | event_without_runtime
    titles["live"] = is_series_sheet & any_live_rule
    titles["wwe_library"] = (
        is_series_sheet & ~titles["live"] & titles["title"].str.contains(WWE_LIBRARY)
    )
    return titles


def add_segment(titles):
    """Label each title: live events are one group, the rest are content type and language."""
    language = titles["lang"].fillna("Unknown")
    titles["segment"] = titles["type"] + " / " + language
    titles.loc[titles["live"], "segment"] = "Live events"
    return titles


def add_next_report_views(titles, reports):
    """Add the same title's hours and views in the following half-year report, if listed."""
    next_rows = reports[["half", "type", "key", "release", "hours", "views"]]
    next_rows = next_rows.dropna(subset=["release"])
    next_rows = next_rows.rename(
        columns={"half": "next_half", "hours": "next_hours", "views": "next_views"}
    )
    # Same key and same release date, so a different title with the same name never matches.
    next_rows = next_rows.drop_duplicates(["next_half", "type", "key", "release"])
    titles["next_half"] = titles["half"].map(NEXT_HALF_YEAR)
    titles = titles.merge(
        next_rows, on=["next_half", "type", "key", "release"], how="left", validate="m:1"
    )
    return titles


def list_entry_bar(top10):
    """Median views of the tenth-ranked title on each weekly list, July 2024 to June 2026."""
    in_period = (top10["week"] >= "2024-07-07") & (top10["week"] <= "2026-07-05")
    tenth_place = top10[in_period & (top10["weekly_rank"] == 10)]
    entry_bar = tenth_place.groupby("category").agg(
        weeks=("week", "nunique"),
        median_views_of_rank_10=("weekly_views", "median"),
    )
    return entry_bar.reset_index()


def build(folder="data"):
    """Return the title table. One row per new release."""
    reports = load_reports(folder)
    top10 = load_top10(f"{folder}/all-weeks-global.tsv")
    titles = select_new_releases(reports)
    weeks = match_top10_weeks(titles, top10)
    titles = add_top10_history(titles, weeks)
    titles = add_live_flags(titles)
    titles = add_staggered_flag(titles)
    titles = add_segment(titles)
    titles = add_next_report_views(titles, reports)
    return titles[OUTPUT_COLUMNS]


if __name__ == "__main__":
    title_table = build()
    title_table.to_csv("data/titles.csv", index=False)
    print(f"{len(title_table)} new releases written to data/titles.csv")
    print(title_table["status"].value_counts().to_string())
    weekly_top10 = load_top10("data/all-weeks-global.tsv")
    list_entry_bar(weekly_top10).to_csv("data/list_entry_bar.csv", index=False)
    print("entry bar of the four weekly lists written to data/list_entry_bar.csv")
