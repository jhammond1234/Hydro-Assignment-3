import os
import sys
import pytz
import urllib3
import datetime
import numpy as np
import pandas as pd
import pyproj
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dataretrieval import nwis
pd.options.mode.chained_assignment = None

def get_usgs_streamflow(site_id, start_date="1980-01-01", end_date=datetime.datetime.today().strftime('%Y-%m-%d')):
    """
    Retrieves daily mean streamflow data from USGS NWIS.
    
    Parameters:
    site_id (str): The USGS station ID (e.g., '09380000')
    start_date (str): Beginning date in 'YYYY-MM-DD' format
    end_date (str): End date in 'YYYY-MM-DD' format
    """
    # Parameter code '00060' refers specifically to Discharge (streamflow) in cfs
    parameter_code = '00060'
    
    print(f"Retrieving data for Site: {site_id} from {start_date} to {end_date}...")
    
    try:
        # get_dv retrieves "Daily Values"
        # returns a DataFrame and a metadata object
        df, metadata = nwis.get_dv(
            sites=site_id, 
            start=start_date, 
            end=end_date, 
            parameterCd=parameter_code
        )
        
        # Clean up the column names for easier use
        # Usually, the flow data is in a column like '00060_Mean'
        df.rename(columns={f'{parameter_code}_00003': 'Streamflow_cfs'}, inplace=True)
        
        return df
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    

#also put the SNOTEL get data function in here as well
