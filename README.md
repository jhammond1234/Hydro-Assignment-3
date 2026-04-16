# Hydro-Assignment-3: LSTM Streamflow Prediction in the Uinta Basin

![alt text](image.png)

This repository contains a data acquisition and machine learning pipeline for predicting daily streamflow across multiple basins in the Uinta Mountains, Utah. The project uses an LSTM (Long Short-Term Memory) neural network trained on meteorological data and observed snow water equivalent (SWE) to predict streamflow. The model is trained on seven seperate catchments in the Uinta mountains, and tested on an eighth withheld catchment. 

---

## Study Sites

Eight USGS stream gages were selected across the Uinta Basin, spanning a range of basin sizes and elevations:

| USGS Gage ID | River / Location       | Basin Area (km²) | Mean Elevation (m) |
|--------------|------------------------|------------------|--------------------|
| 10154200     | Provo River            | 734.3            | 2761               |
| 10128500     | Weber River            | 735.8            | 2756               |
| 10011500     | Bear River             | 797.5            | 2958               |
| 09217900     | Blacks Fork            | 586.3            | 3178               |
| 09266500     | Ashley Creek           | 460.5            | 2879               |
| 09299500     | Whiterocks River       | 529.4            | 3127               |
| 09292000     | Yellowstone River      | 473.3            | 3260               |
| 09289500     | Lake Fork River        | 355.7            | 3280               |

The Provo River (10154200) was withheld as the  test site — the model was trained on the remaining 7 basins and evaluated on the Provo with no prior exposure.

---

## Data Sources

- **Streamflow:** USGS NWIS daily mean discharge (1980–2024) via `dataretrieval`
- **Meteorology:** Daymet daily gridded climate data (1980–2024) via `pydaymet` — precipitation, temperature (min/max/mean), solar radiation, vapor pressure, daylength
- **Snow Water Equivalent:** NRCS SNOTEL station observations via [egagli/snotel_ccss_stations](https://github.com/egagli/snotel_ccss_stations). Multiple stations per basin are averaged into a single daily SWE value. SNOTEL data is preferred over Daymet SWE due to better accuracy in complex mountain terrain.
- **Basin Attributes:** Topographic attributes (area, mean/min/max elevation, slope) derived from 30m DEMs via `py3dep`. Land cover fractions from NLCD 2019 via `pygeohydro`.

---

## Repository Structure

```
Hydro-Assignment-3/
├── data/
│   ├── SNOTEL/              # Raw SNOTEL CSVs per station
│   ├── PyDayMet/            # Daymet meteorological data per gage
│   ├── NWIS/                # USGS streamflow data per gage
│   ├── basin_info/          # Basin topographic and land cover attributes
│   ├── DEM/                 # DEM rasters per basin
│   └── merged/              # Final merged DataFrames per gage + all sites
├── notebooks/
│   └── LSTM_streamflow.ipynb  # LSTM training, evaluation, and visualization
├── scripts/
│   ├── met_data_collection.py    # Collect Daymet meteorological data
│   ├── snotel_collection.py      # Collect and process SNOTEL SWE data
│   ├── streamflow_collection.py  # Collect USGS NWIS streamflow data
│   ├── basin_attributes.py       # Compute basin topographic and NLCD attributes
│   ├── merge_data.py             # Merge all data sources into one DataFrame per site
│   └── supporting_scripts/       # Helper modules (getData, dataprocessing, etc.)
├── HW3env.yml                    # Conda environment file
└── README.md
```

---

## Setup

### 1. Create the conda environment

```bash
conda env create -f HW3env.yml
conda activate HW3env
```

### 2. Run the data acquisition scripts in order

```bash
cd scripts/

python met_data_collection.py       # 1. Daymet meteorological data
python snotel_collection.py         # 2. SNOTEL SWE data
python streamflow_collection.py     # 3. USGS streamflow data
python basin_attributes.py          # 4. Basin topographic attributes
python merge_data.py                # 5. Merge all sources into final DataFrames
```

### 3. Run the LSTM notebook

Open `notebooks/LSTM_streamflow.ipynb` in Jupyter and run all cells. The notebook handles train/validation/spatial test splitting, model training with early stopping, and evaluation.

---

## Model Overview

- **Architecture:** LSTM with 2 layers, 60 hidden units, dropout 0.2
- **Input features:** SWE (SNOTEL mean), precipitation, mean/min/max temperature, solar radiation, vapor pressure, daylength
- **Lookback window:** 30 days
- **Target:** Daily mean streamflow (cms)
- **Train period:** 1980–2016 (7 training sites)
- **Validation period:** 2017–2024 (7 training sites)
- **Spatial test:** Provo River (10154200), all years withheld from training

---

## Results

The model was evaluated on the held-out Provo River basin:

| Metric | Value |
|--------|-------|
| R²     | 0.25  |
| RMSE   | 8.56 cms |
| MAE    | 3.38 cms |

The model captured seasonal streamflow patterns well but systematically underpredicted peak flows. This is attributed to the Provo basin being larger than the training basins — without static catchment attributes like drainage area, the model has no context for flow magnitude at ungauged locations. This finding is consistent with Kratzert et al. (2019), who demonstrated that including catchment attributes significantly improves spatial generalization in LSTM-based streamflow models.

---

## Dependencies

Key packages used in this project:

- `pynhd` — basin delineation via NLDI
- `pydaymet` — Daymet meteorological data
- `dataretrieval` — USGS NWIS streamflow data
- `py3dep` — DEM and topographic data
- `pygeohydro` — NLCD land cover data
- `geopandas`, `xarray`, `xrspatial` — spatial data processing
- `torch` — LSTM model
- `sklearn` — data preprocessing and metrics

See `HW3env.yml` for the full environment specification.

---

## Data Citation

SNOTEL data sourced from:
> Gagliano, E. (2024). snotel_ccss_stations (Version v1.0) [Computer software]. https://github.com/egagli/snotel_ccss_stations
