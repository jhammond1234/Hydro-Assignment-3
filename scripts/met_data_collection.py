"""
Meteorological data collection for USGS gage basins using NLDI and Daymet.
"""

from pynhd import NLDI, WaterData, NHDPlusHR, GeoConnex
import geopandas as gpd
import pandas as pd
from supporting_scripts import getData, dataprocessing, mapping
from shapely.geometry import box, Polygon
import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
import warnings
import earthaccess # note, you may need to create a .netrc file in you home directory with the following information
from pynhd import NLDI
import pydaymet as daymet
warnings.filterwarnings("ignore")

# Authenticate with NASA (only needed once per session)
earthaccess.login(persist=True)


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

WATER_YEAR = 2019

DAYMET_VARS = ["prcp", "srad", "swe", "vp", "dayl", "tmin", "tmax"]

COLUMN_RENAME = {
    "prcp (mm/day)": "prcp_mm_day",
    "srad (W/m2)": "srad_W_m2",
    "swe (kg/m2)": "swe_cm",
    "vp (Pa)": "vp_Pa",
    "dayl (s)": "dayl_s",
    "tmin (degrees C)": "tmin_C",
    "tmax (degrees C)": "tmax_C",
}


# --- Helper Functions ---

def water_year_to_dates(wy: int) -> tuple[str, str]:
    """Convert a water year integer to a (start, end) date string tuple."""
    return (f"{wy - 1}-10-01", f"{wy}-09-30")


def get_basin_centroid(gage_id: str) -> tuple[float, float]:
    """Fetch the basin geometry for a USGS gage and return its centroid (x, y)."""
    basin = NLDI().get_basins(gage_id)
    centroid = basin.geometry.centroid.iloc[0]
    return (centroid.x, centroid.y)


def fetch_met_data(centroid: tuple[float, float], dates: tuple[str, str], variables: list[str]) -> pd.DataFrame:
    """Fetch Daymet meteorological data for a given centroid and date range."""
    return daymet.get_bycoords(centroid, dates, variables=variables)


def clean_met_data(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, compute derived variables, and clean up the DataFrame."""
    df = df.rename(columns=COLUMN_RENAME)
    df["tmean_C"] = (df["tmax_C"] + df["tmin_C"]) / 2
    df["swe_cm"] = df["swe_cm"] * 0.1  # kg/m2 -> cm
    df.index.name = "Date"
    return df


def process_site(gage_id: str, water_year: int) -> pd.DataFrame:
    """End-to-end pipeline for a single USGS gage site."""
    print(f"Processing gage: {gage_id}")
    dates = water_year_to_dates(water_year)
    centroid = get_basin_centroid(gage_id)
    raw_df = fetch_met_data(centroid, dates, DAYMET_VARS)
    clean_df = clean_met_data(raw_df)
    clean_df["gage_id"] = gage_id  # tag each row so sites are identifiable after combining

    # Save individual site CSV
    output_folder = "../data/PyDayMet"
    os.makedirs(output_folder, exist_ok=True)  # cleaner than checking first
    clean_df.to_csv(f"{output_folder}/PyDayMet_{gage_id}.csv")
    print(f"  Saved to {output_folder}/PyDayMet_{gage_id}.csv")

    return clean_df


# --- Main Execution ---

def main():
    all_results = []

    for gage_id in USGS_GAGE_IDS:
        try:
            site_df = process_site(gage_id, WATER_YEAR)
            all_results.append(site_df)
        except Exception as e:
            print(f"  ERROR for gage {gage_id}: {e}")

    if all_results:
        combined_df = pd.concat(all_results)
        output_path = f"../data/met_data_combined.csv"
        combined_df.to_csv(output_path)
        print(f"\nSaved {len(all_results)} sites to {output_path}")

    return combined_df


if __name__ == "__main__":
    combined_df = main()

  