"""
Streamflow data collection for multiple USGS gage sites using NWIS.
Retrieves daily mean streamflow, cleans, and saves to CSV.
"""

import os
import warnings
import pandas as pd
from supporting_scripts import getData, dataprocessing

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

START_DATE = "1980-01-01"
END_DATE = "2024-12-31"

OUTPUT_FOLDER = "../data/NWIS"


# --- Helper Functions ---

def fetch_streamflow(gage_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Retrieve raw daily streamflow data for a USGS gage."""
    return getData.get_usgs_streamflow(gage_id, start_date, end_date)


def clean_streamflow(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw NWIS dataframe and set index name to Date."""
    cleaned = dataprocessing.clean_nwis_dataframe(df)
    cleaned.index.name = "Date"
    return cleaned


def save_streamflow(df: pd.DataFrame, gage_id: str) -> None:
    """Save cleaned streamflow data to CSV."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    path = f"{OUTPUT_FOLDER}/streamflow_{gage_id}.csv"
    df.to_csv(path)
    print(f"  Saved to {path}")


def process_site(gage_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """End-to-end pipeline for a single USGS gage site."""
    print(f"\nProcessing gage: {gage_id}")
    raw = fetch_streamflow(gage_id, start_date, end_date)

    if raw is None:
        print(f"  No data returned for gage {gage_id}, skipping.")
        return None

    cleaned = clean_streamflow(raw)
    cleaned["gage_id"] = gage_id  # tag for identification when combined
    save_streamflow(cleaned, gage_id)
    return cleaned


# --- Main Execution ---

def main():
    all_results = []

    for gage_id in USGS_GAGE_IDS:
        try:
            site_df = process_site(gage_id, START_DATE, END_DATE)
            if site_df is not None:
                all_results.append(site_df)
        except Exception as e:
            print(f"  ERROR for gage {gage_id}: {e}")

    if all_results:
        combined_df = pd.concat(all_results)
        combined_path = f"{OUTPUT_FOLDER}/streamflow_all_sites.csv"
        combined_df.to_csv(combined_path)
        print(f"\nDone. Saved {len(all_results)} site(s) to {combined_path}")

    return combined_df


if __name__ == "__main__":
    combined_df = main()
