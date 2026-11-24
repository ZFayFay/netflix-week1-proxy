"""Build the title-level dataset: week-1 Top 10 views vs. half-year views."""
import re, unicodedata
import numpy as np, pandas as pd

HALVES = {"2024H2": ("2024-07-01", "2024-12-31"), "2025H1": ("2025-01-01", "2025-06-30"),
          "2025H2": ("2025-07-01", "2025-12-31"), "2026H1": ("2026-01-01", "2026-06-30")}

def norm(t):
    """Lower-case title, keep the English part before '//', unify quotes and spaces."""
    t = str(t).split("//")[0]
    t = unicodedata.normalize("NFKC", t)
    for a, b in {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"}.items():
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip().casefold()

SEASON = re.compile(r":\s*(?:season\s*(\d+)|limited series|s(\d+)(?::.*)?)\s*$", re.I)

def split_season(title):
    """'Love Is Blind: Season 7' -> ('love is blind', 7); 'X: Limited Series' -> ('x', 1); no suffix -> (x, 1)."""
    t = norm(title)
    m = SEASON.search(t)
    if not m:
        return t, 1
    n = m.group(1) or m.group(2) or 1
    return t[: m.start()].strip(), int(n)

ALIASES = {"mary": "mary mother of jesus",
           "fake profile: killer match|1": "fake profile|2"}

def load_reports(folder="data"):
    out = []
    for h, (a, b) in HALVES.items():
        x = pd.ExcelFile(f"{folder}/wwh_{h}.xlsx")
        for s in x.sheet_names:
            d = pd.read_excel(x, s, header=5).dropna(axis=1, how="all")
            d["type"] = "TV" if s in ("TV", "Shows") else "Film"
            d["half"], d["h_start"], d["h_end"] = h, pd.Timestamp(a), pd.Timestamp(b)
            out.append(d)
    w = pd.concat(out, ignore_index=True)
    w = w.rename(columns={"Title": "title", "Available Globally?": "global", "Release Date": "release",
                          "Hours Viewed": "hours", "Runtime": "runtime", "Views": "views"})
    w["release"] = pd.to_datetime(w["release"], errors="coerce")
    for c in ("hours", "views"):
        w[c] = pd.to_numeric(w[c], errors="coerce")
    return w

def load_top10(path="data/g.tsv"):
    g = pd.read_csv(path, sep="\t")
    g["week"] = pd.to_datetime(g["week"])            # week = the Sunday that closes a Mon-Sun week
    g["type"] = np.where(g.category.str.startswith("TV"), "TV", "Film")
    g["lang"] = np.where(g.category.str.contains("Non-English"), "Non-English", "English")
    has_season = g.season_title.notna() & (g.season_title != "N/A")
    g["full"] = np.where(has_season, g.season_title, g.show_title)
    return g

def build(folder="data"):
    w, g = load_reports(folder), load_top10(f"{folder}/g.tsv")
    # Keep new releases: premiered inside the report's six months.
    new = w[(w.release >= w.h_start) & (w.release <= w.h_end)].copy()
    new["days_in_window"] = (new.h_end - new.release).dt.days + 1

    # Match keys: films on title; TV on (show name, season number).
    new["k"] = np.where(new.type == "Film", new.title.map(norm),
                        new.title.map(lambda t: "|".join(map(str, split_season(t)))))
    # Two titles were renamed between the report and the Top 10 list (checked by hand).
    new["k"] = new["k"].replace(ALIASES)
    g["k_full"] = np.where(g.type == "Film", g.full.map(norm),
                           g.full.map(lambda t: "|".join(map(str, split_season(t)))))
    g["k_show"] = np.where(g.type == "Film", g.full.map(norm),
                           [f"{norm(s)}|{split_season(f)[1]}" for s, f in zip(g.show_title, g.full)])
    long = pd.concat([g.assign(k=g.k_full), g.assign(k=g.k_show)]).drop_duplicates(["week", "category", "weekly_rank", "k"])

    m = new.merge(long[["k", "type", "week", "lang", "weekly_views", "weekly_hours_viewed", "weekly_rank"]],
                  on=["k", "type"], how="left")
    # Only keep Top 10 weeks after release, within the same report window.
    m = m[m.week.isna() | ((m.week >= m.release) & (m.week <= m.h_end + pd.Timedelta(days=6)))]
    m = m.sort_values("week")

    # Week 1 = the Top 10 week that contains the release date (release <= Sunday < release + 7 days).
    rel_wk = m[(m.week - m.release).dt.days.between(0, 6)]
    wk1 = rel_wk.groupby(["half", "type", "title"]).first()[["week", "lang", "weekly_views", "weekly_rank"]]
    wk1 = wk1.rename(columns={"week": "wk1_end", "weekly_views": "wk1_views", "weekly_rank": "wk1_rank"})
    ever = m.dropna(subset=["week"]).groupby(["half", "type", "title"]).agg(
        first_top10=("week", "min"), weeks_in_top10=("week", "nunique"), lang_any=("lang", "first"))

    df = new.set_index(["half", "type", "title"]).join(wk1).join(ever).reset_index()
    df["lang"] = df["lang"].fillna(df["lang_any"])
    df["wk1_views"] = df["wk1_views"].astype(float)
    df["days_in_window"] = df["days_in_window"].astype(int)
    df["days_live_wk1"] = (df.wk1_end - df.release).dt.days + 1     # 1..7 days the title was out in week 1
    df["status"] = np.select([df.wk1_views.notna(), df.first_top10.notna()],
                             ["Top 10 in week 1", "Entered Top 10 later"], "Never in Top 10")
    # Live sports and WWE episodes: watched almost entirely in week 1, so we keep them as their own group.
    pat = r"^(?:raw|wwe|smackdown)\b|world baseball classic|gameday|\bvs\.\s(?!wild)"
    df["live"] = (df.type == "TV") & df.title.str.contains(pat, case=False, regex=True) & ~df.title.str.contains(": Season")
    df["segment"] = np.where(df.live, "Live sports & WWE", df.type + " / " + df.lang.fillna("Unknown"))
    return df.drop(columns=["lang_any", "k"])

if __name__ == "__main__":
    df = build()
    df.to_csv("data/titles.csv", index=False)
    print(df.status.value_counts())
