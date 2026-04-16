"""
Basin attribute collection for multiple USGS gage sites.
Collects topographic (DEM, slope, elevation) and land cover (NLCD) attributes
for each basin and saves to CSV.
"""

import os
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from pathlib import Path
from pynhd import NLDI
import py3dep
import pygeohydro as gh
import xrspatial

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

DEM_FOLDER     = "../data/DEM"
OUTPUT_FOLDER  = "../data/basin_info"
NLCD_YEAR      = 2019
NLCD_RES       = 100  # meters


# --- NLCD Legend ---

NLCD_LEGEND = {
    11:  "Open_Water",
    12:  "Perennial_Ice_Snow",
    21:  "Developed_Open_Space",
    22:  "Developed_Low_Intensity",
    23:  "Developed_Medium_Intensity",
    24:  "Developed_High_Intensity",
    31:  "Barren_Land",
    41:  "Deciduous_Forest",
    42:  "Evergreen_Forest",
    43:  "Mixed_Forest",
    52:  "Shrub_Scrub",
    71:  "Grassland_Herbaceous",
    90:  "Woody_Wetlands",
    95:  "Emergent_Herbaceous_Wetlands",
    127: "No_Data",
}


# --- Helper Functions ---

def get_basin(gage_id: str):
    """Fetch basin geometry for a USGS gage."""
    print(f"  Fetching basin geometry...", end="")
    basin = NLDI().get_basins(gage_id)
    print("done")
    return basin


def get_topo(geometry, gage_id: str) -> xr.Dataset:
    """Compute DEM and slope for a basin geometry, save DEM raster."""
    print(f"  Fetching DEM and slope...", end="")
    dem = py3dep.get_dem(geometry, 30)
    dem = dem.rio.reproject(5070)
    slope = py3dep.deg2mpm(xrspatial.slope(dem))
    topo = xr.merge([dem, slope])

    # Save DEM raster
    os.makedirs(DEM_FOLDER, exist_ok=True)
    dem.rio.to_raster(Path(DEM_FOLDER, f"dem_{gage_id}.tif"))
    print("done")
    return topo


def get_topo_stats(topo: xr.Dataset, geometry) -> dict:
    """Extract elevation and slope statistics, and compute basin area."""
    # Elevation stats
    ave_elev = float(topo.elevation.mean().values)
    min_elev = float(topo.elevation.min().values)
    max_elev = float(topo.elevation.max().values)
    ave_slope = float(topo.slope.mean().values)

    # Basin area
    gs = gpd.GeoSeries([geometry], crs="EPSG:4326").to_crs(epsg=3857)
    area_km2 = gs.area.iloc[0] / 1_000_000

    return {
        "Average_Elevation_m": ave_elev,
        "Minimum_Elevation_m": min_elev,
        "Maximum_Elevation_m": max_elev,
        "Average_Slope":       ave_slope,
        "Area_km2":            area_km2,
    }


def get_nlcd_stats(basin: gpd.GeoDataFrame, gage_id: str) -> pd.DataFrame:
    """Fetch NLCD land cover fractions for a basin."""
    print(f"  Fetching NLCD land cover...", end="")
    lulc = gh.nlcd_bygeom(
        basin.geometry, NLCD_RES,
        years={"cover": [NLCD_YEAR]}, ssl=False
    )
    cover = lulc[f"USGS-{gage_id}"].cover_2019

    # Summarize pixel counts
    vals, counts = np.unique(cover.values, return_counts=True)
    summary = pd.DataFrame({
        "code":    vals,
        "count":   counts,
        "name":    [NLCD_LEGEND.get(v, "Unknown") for v in vals]
    })

    # Calculate percentages, exclude NoData
    summary = summary[summary["code"] != 127]
    total   = summary["count"].sum()
    summary["percent"] = (summary["count"] / total) * 100

    # Pivot to wide format
    lulc_wide = summary.set_index("name")[["percent"]].T
    lulc_wide.columns = lulc_wide.columns.str.replace(" ", "_")
    lulc_wide.index   = [gage_id]

    print("done")
    return lulc_wide


def process_site(gage_id: str) -> pd.DataFrame:
    """Full pipeline for one USGS gage site."""
    print(f"\nProcessing gage: {gage_id}")

    basin    = get_basin(gage_id)
    geometry = basin.geometry.iloc[0]
    topo     = get_topo(geometry, gage_id)

    # Topo + area stats
    topo_stats = get_topo_stats(topo, geometry)
    topo_stats["gage_id"] = gage_id
    basin_df = pd.DataFrame(topo_stats, index=[gage_id])

    # NLCD land cover
    lulc_df = get_nlcd_stats(basin, gage_id)

    # Combine
    combined = pd.concat([basin_df, lulc_df], axis=1)

    # Save individual site file
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    out_path = f"{OUTPUT_FOLDER}/basin_info_{gage_id}.csv"
    combined.to_csv(out_path)
    print(f"  Saved to {out_path}")

    return combined


# --- Main Execution ---

def main():
    all_results = []

    for gage_id in USGS_GAGE_IDS:
        try:
            site_df = process_site(gage_id)
            all_results.append(site_df)
        except Exception as e:
            print(f"  ERROR for gage {gage_id}: {e}")

    if all_results:
        combined = pd.concat(all_results)
        out_path = f"{OUTPUT_FOLDER}/basin_info_all_sites.csv"
        combined.to_csv(out_path)
        print(f"\nDone. All sites saved to {out_path}")
        return combined


if __name__ == "__main__":
    basin_attrs = main()
