"""
SNOTEL data collection for USGS gage basins.
Identifies SNOTEL stations within each basin and pulls SWE data.

Data source: Gagliano, E. (2024).
snotel_ccss_stations (Version v1.0) [Computer software].
https://github.com/egagli/snotel_ccss_stations
"""

import os
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from datetime import datetime
from pynhd import NLDI
from supporting_scripts import dataprocessing

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

STATE_AB = "UT"  # Change to your state abbreviation

OUTPUT_FOLDER = "../data/SNOTEL"
PROCESSED_FOLDER = "../data/SNOTEL_processed"

STATIONS_URL = "https://raw.githubusercontent.com/egagli/snotel_ccss_stations/main/all_stations.geojson"
DATA_BASE_URL = "https://raw.githubusercontent.com/egagli/snotel_ccss_stations/refs/heads/main/data"


# --- Helper Functions ---

def load_all_stations() -> gpd.GeoDataFrame:
    """Load the full SNOTEL/CCSS station GeoDataFrame from GitHub."""
    print("Loading SNOTEL station list...", end="")
    gdf = gpd.read_file(STATIONS_URL).set_index("code")
    gdf = gdf[gdf["csvData"] == True]
    print("done")
    return gdf


def get_basin_geometry(gage_id: str) -> gpd.GeoDataFrame:
    """Fetch upstream basin geometry for a USGS gage."""
    print(f"  Fetching basin for gage {gage_id}...", end="")
    basin = NLDI().get_basins(gage_id)
    print("done")
    return basin


def find_stations_in_basin(basin: gpd.GeoDataFrame, all_stations: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return stations whose geometry falls within the basin polygon."""
    gdf_in_basin = all_stations[all_stations.geometry.within(basin.geometry.iloc[0])].copy()
    gdf_in_basin.reset_index(drop=False, inplace=True)

    # Format dates as strings
    for col in ["beginDate", "endDate"]:
        if col in gdf_in_basin.columns:
            gdf_in_basin[col] = [
                datetime.strftime(gdf_in_basin[col][i], "%Y-%m-%d")
                for i in range(len(gdf_in_basin))
            ]

    return gdf_in_basin


def fetch_snotel_csv(site_code: str, state_ab: str) -> pd.DataFrame:
    """Download raw SNOTEL CSV for a given site code and state."""
    url = f"{DATA_BASE_URL}/{site_code}_{state_ab}_SNTL.csv"
    return pd.read_csv(url)


def save_raw(df: pd.DataFrame, site_code: str, state_ab: str) -> None:
    """Save raw SNOTEL data to the output folder."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    path = f"{OUTPUT_FOLDER}/df_{site_code}.csv"
    df.to_csv(path, index=False)
    print(f"    Raw data saved to {path}")

    


def process_site(gage_id: str, all_stations: gpd.GeoDataFrame, state_ab: str) -> dict:
    """
    Full pipeline for one USGS gage:
    - Find SNOTEL stations in basin
    - Download raw data
    - Process and save
    Returns a dict of {site_code: processed_df}
    """
    print(f"\nProcessing gage: {gage_id}")
    basin = get_basin_geometry(gage_id)
    stations_in_basin = find_stations_in_basin(basin, all_stations)

    if stations_in_basin.empty:
        print(f"  No SNOTEL stations found in basin for gage {gage_id}")
        return {}

    print(f"  Found {len(stations_in_basin)} station(s): {list(stations_in_basin['code'])}")

    site_dict = {}
    for _, row in stations_in_basin.iterrows():
        site_code = row["code"].replace(f"_{state_ab}_SNTL", "")  # extract numeric code
        full_code = f"{site_code}_{state_ab}_SNTL"

        try:
            print(f"  Fetching {full_code}...", end="")
            raw_df = fetch_snotel_csv(site_code, state_ab)
            print("done")
            save_raw(raw_df, site_code, state_ab)

            # Process using your existing dataprocessing module
            os.makedirs(PROCESSED_FOLDER, exist_ok=True)
            site_dict[full_code] = dataprocessing.processSNOTEL(site_code, state_ab)

        except Exception as e:
            print(f"\n    ERROR for {full_code}: {e}")

    return site_dict


# --- Main Execution ---

def main():
    all_stations = load_all_stations()
    all_site_dicts = {}

    for gage_id in USGS_GAGE_IDS:
        try:
            site_dict = process_site(gage_id, all_stations, STATE_AB)
            all_site_dicts.update(site_dict)
        except Exception as e:
            print(f"ERROR for gage {gage_id}: {e}")

    print(f"\nDone. Processed {len(all_site_dicts)} SNOTEL site(s) total.")
    return all_site_dicts


if __name__ == "__main__":
    all_site_dicts = main()
