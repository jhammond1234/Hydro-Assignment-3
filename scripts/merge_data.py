"""
Merge meteorological (Daymet), SNOTEL, and streamflow data into one
DataFrame per USGS gage site. SNOTEL stations within each basin are
averaged into a single 'SWE_cm_mean' column.
"""

import os
import warnings
import pandas as pd

warnings.filterwarnings("ignore")


# --- Configuration ---

USGS_GAGE_IDS = [
    "10154200",  # Provo River
    "10128500",  # Weber River
    "10011500",  # Bear River
    "09217900",  # Blacks Fork
    "09266500",  # Ashley Creek
    "09299500",  # Whiterocks River
    "09292000",  # Yellowstone River
    "09289500",  # Lake Fork River
]

SNOTEL_FOLDER = "../data/SNOTEL"
DAYMET_FOLDER = "../data/PyDayMet"
NWIS_FOLDER = "../data/NWIS"
BASIN_INFO_PATH = "../data/basin_info/basin_info_all_sites.csv"
OUTPUT_FOLDER = "../data/merged"


# --- Loading Functions ---

def load_snotel(gage_id: str) -> pd.DataFrame:
    """
    Load all raw SNOTEL CSVs for a given gage, average SWE across
    stations, and return a single daily SWE column.
    """
    snotel_dfs = []

    for filename in os.listdir(SNOTEL_FOLDER):
        # Each file is named df_{site_code}.csv and tagged with gage_id
        # We load all files and filter by gage_id column
        if not filename.endswith(".csv"):
            continue
        filepath = os.path.join(SNOTEL_FOLDER, filename)
        df = pd.read_csv(filepath)


        # Skip files not belonging to this gage
        if "gage_id" in df.columns and not (df["gage_id"].astype(str).str.lstrip('0') == str(gage_id).lstrip('0')).any():
            continue

        # Parse date and set index
        date_col = next((c for c in df.columns if c.lower() in ["date", "datetime"]), None)
        if date_col is None:
            continue
        df[date_col] = pd.to_datetime(df[date_col])
        df.set_index(date_col, inplace=True)
        df.index.name = "Date"

        # Keep only the SWE column, rename to station filename for clarity
        swe_col = next((c for c in df.columns if "wteq" in c.lower() or "swe" in c.lower()), None)
        if swe_col is None:
            continue

        site_name = filename.replace("df_", "").replace(".csv", "")
        df = df[[swe_col]].rename(columns={swe_col: f"{site_name}_SWE_m"})

        # Convert m to cm
        df[f"{site_name}_SWE_m"] = df[f"{site_name}_SWE_m"] * 100
        df.rename(columns={f"{site_name}_SWE_m": f"{site_name}_SWE_cm"}, inplace=True)

        snotel_dfs.append(df)
        print(f"  Loaded SNOTEL: {site_name} ({len(df)} records, "
              f"{df.index.min().date()} to {df.index.max().date()})")

    if not snotel_dfs:
        print(f"  WARNING: No SNOTEL data found for gage {gage_id}")
        return pd.DataFrame()

    # Align on date index and average across all stations
    combined = pd.concat(snotel_dfs, axis=1)
    combined["SWE_cm_mean"] = combined.mean(axis=1)
    print(f"  Averaged {len(snotel_dfs)} SNOTEL station(s) into SWE_cm_mean")

    return combined[["SWE_cm_mean"]]


def load_daymet(gage_id: str) -> pd.DataFrame:
    """Load Daymet met data for a gage."""
    path = os.path.join(DAYMET_FOLDER, f"PyDayMet_{gage_id}.csv")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    # Drop Daymet SWE since we're using observed SNOTEL SWE
    if "swe_cm" in df.columns:
        df.drop(columns=["swe_cm"], inplace=True)
    print(f"  Loaded Daymet ({len(df)} records, "
          f"{df.index.min().date()} to {df.index.max().date()})")
    return df


def load_streamflow(gage_id: str) -> pd.DataFrame:
    """Load NWIS streamflow data for a gage."""
    path = os.path.join(NWIS_FOLDER, f"streamflow_{gage_id}.csv")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    # Drop gage_id column if present, we'll re-add it after merge
    if "gage_id" in df.columns:
        df.drop(columns=["gage_id"], inplace=True)
    print(f"  Loaded streamflow ({len(df)} records, "
          f"{df.index.min().date()} to {df.index.max().date()})")
    return df

def load_basin_attrs() -> pd.DataFrame:
    """Load static basin attributes."""
    df = pd.read_csv(BASIN_INFO_PATH, index_col=0)
    df.index = df.index.astype(str).str.lstrip('0')
    print(f"  Loaded basin attributes for {len(df)} sites")
    return df
# --- Merge Function ---

def merge_site(gage_id: str) -> pd.DataFrame:
    """
    Load, align, and merge all data sources for one gage site.
    Returns a single merged DataFrame.
    """
    print(f"\nMerging data for gage: {gage_id}")

    snotel_df = load_snotel(gage_id)
    daymet_df = load_daymet(gage_id)
    streamflow_df = load_streamflow(gage_id)

    # Load basin attributes and repeat for every row in this site
    basin_attrs = load_basin_attrs()
    lookup_id = str(gage_id).lstrip('0')
    if lookup_id in basin_attrs.index:
        for col in basin_attrs.columns:
            if col != 'gage_id':
                daymet_df[col] = basin_attrs.loc[lookup_id, col]
    else:
        print(f"  WARNING: No basin attributes found for gage {gage_id}")

    # Collect non-empty dataframes for date alignment
    dfs = {name: df for name, df in {
        "SNOTEL": snotel_df,
        "Daymet": daymet_df,
        "Streamflow": streamflow_df
    }.items() if not df.empty}

    # Find overlapping date range across all sources
    begin_date = max(df.index.min() for df in dfs.values())
    end_date = min(df.index.max() for df in dfs.values())
    print(f"  Clipping to overlapping range: {begin_date.date()} to {end_date.date()}")

    # Clip each dataframe to the overlapping range
    clipped = {
        name: df[(df.index >= begin_date) & (df.index <= end_date)]
        for name, df in dfs.items()
    }

    # Merge all on Date index
    merged = pd.concat(clipped.values(), axis=1)

    # Put streamflow last (target variable), gage_id first
    merged["gage_id"] = gage_id
    flow_col = "flow_cms"
    other_cols = [c for c in merged.columns if c not in [flow_col, "gage_id"]]
    merged = merged[["gage_id"] + other_cols + [flow_col]]

    # Fill NaN with 0 (consistent with original notebook)
    merged = merged.fillna(0)

    print(f"  Final shape: {merged.shape}")
    return merged


# --- Main Execution ---

def main():
    all_results = []
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    for gage_id in USGS_GAGE_IDS:
        try:
            site_df = merge_site(gage_id)

            # Save individual site merged file
            out_path = f"{OUTPUT_FOLDER}/merged_{gage_id}.csv"
            site_df.to_csv(out_path)
            print(f"  Saved to {out_path}")

            all_results.append(site_df)

        except Exception as e:
            print(f"  ERROR for gage {gage_id}: {e}")

    if all_results:
        combined = pd.concat(all_results)
        combined_path = f"{OUTPUT_FOLDER}/merged_all_sites.csv"
        combined.to_csv(combined_path)
        print(f"\nDone. All sites saved to {combined_path}")

    return combined


if __name__ == "__main__":
    combined_df = main()
