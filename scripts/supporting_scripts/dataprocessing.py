import pandas as pd
import os


# def processSNOTEL(site, stateab, WYOI):
#     print(site)

#     sitedf = pd.read_csv(f"files/SNOTEL/df_{site}.csv")

#     WYs = sitedf['Water_Year'].unique()

#     WYsitedf = pd.DataFrame()

#     for WY in WYs:
#         cols =['M', 'D', 'Snow Water Equivalent (m) Start of Day Values']

#         #get water year of interest
#         wydf = sitedf[sitedf['Water_Year']==WY]
#         wydf['M'] = pd.to_datetime(sitedf['Date']).dt.month
#         wydf['D'] = pd.to_datetime(sitedf['Date']).dt.day

#         #change NaN to 0, most NaN values are from low to 0 SWE measurements
#         wydf['Snow Water Equivalent (m) Start of Day Values'] = wydf['Snow Water Equivalent (m) Start of Day Values'].fillna(0)
#         wydf = wydf[cols]
#         wydf.rename(columns = {'Snow Water Equivalent (m) Start of Day Values':f"{WY}_SWE_m"}, inplace=True)
#         wydf.reset_index(inplace=True, drop=True)
#         WYsitedf[f"{WY}_SWE_in"] = wydf[f"{WY}_SWE_m"]*39.3701 #converting m to inches (standard for snotel)

#         if len(wydf) == 365:
#             try:
#                 WYsitedf.insert(0,'M',wydf['M'])
#                 WYsitedf.insert(1,'D',wydf['D'])
#             except:
#                 pass
#     #WYsitedf.fillna(0)

#     #remove July, August, September
#     months = [8,9]
#     WYsitedf = WYsitedf[~WYsitedf['M'].isin(months)]

#     #remove M/D to calculate row min, mean, median, max tiers
#     df = WYsitedf.copy()
#     #drop the water year of interest from WYsitedf to calculate the min, mean, median, max SWE for each day of the water year across all other years of data available for that site
    
#     print(f"Dropping {WYOI} from the calculations of the min, mean, median, max SWE for each day of the water year across all other years of data available for that site")
#     try:
#         WYOIdrop = f"{WYOI}_SWE_in"
#         coldrop = ['M', 'D', WYOIdrop]
#         WYsitedf = WYsitedf.drop(columns = coldrop)
#     except:
#         print(f"{WYOI} not found in the data, not dropping any columns")
    
    
#     df['min'] = WYsitedf.min(axis=1)
#     df['Q10'] = WYsitedf.quantile(0.10, axis=1)
#     df['Q25'] = WYsitedf.quantile(0.25, axis=1)
#     df['mean'] = WYsitedf.mean(axis=1)
#     df['median'] = WYsitedf.median(axis=1)
#     df['Q75'] = WYsitedf.quantile(0.75, axis=1)
#     df['Q90'] = WYsitedf.quantile(0.90, axis=1)
#     df['max'] = WYsitedf.max(axis=1)

#     #add back in M/d for plotting
#     # df.insert(0,'M',WYsitedf['M'])
#     # df.insert(1,'D',WYsitedf['D'])

#     # Convert to datetime format
#     df['date'] = pd.to_datetime(dict(year = 2023, month = df['M'], day = df['D'])) 

#     # Format the date
#     df['M-D'] = df['date'].dt.strftime('%m-%d')
#     df.set_index('M-D', inplace=True)

#     return df

def processSNOTEL(site, stateab):
    print(site)

    sitedf = pd.read_csv(f"files/SNOTEL/df_{site}.csv")

     # Convert datetime and add Water_Year column
    sitedf['datetime'] = pd.to_datetime(sitedf['datetime'])
    sitedf['Water_Year'] = sitedf['datetime'].apply(lambda x: x.year + 1 if x.month >= 10 else x.year)
    sitedf['Snow Water Equivalent (m) Start of Day Values'] = sitedf['WTEQ'] * 0.0254
    sitedf['Date'] = sitedf['datetime']

    WYs = sitedf['Water_Year'].unique()

    WYs = sitedf['Water_Year'].unique()

    WYsitedf = pd.DataFrame()

    for WY in WYs:
        cols =['M', 'D', 'Snow Water Equivalent (m) Start of Day Values']

        wydf = sitedf[sitedf['Water_Year']==WY]
        wydf['M'] = pd.to_datetime(sitedf['Date']).dt.month
        wydf['D'] = pd.to_datetime(sitedf['Date']).dt.day

        wydf['Snow Water Equivalent (m) Start of Day Values'] = wydf['Snow Water Equivalent (m) Start of Day Values'].fillna(0)
        wydf = wydf[cols]
        wydf.rename(columns = {'Snow Water Equivalent (m) Start of Day Values':f"{WY}_SWE_m"}, inplace=True)
        wydf.reset_index(inplace=True, drop=True)
        WYsitedf[f"{WY}_SWE_in"] = wydf[f"{WY}_SWE_m"]*39.3701

        if len(wydf) == 365:
            try:
                WYsitedf.insert(0,'M',wydf['M'])
                WYsitedf.insert(1,'D',wydf['D'])
            except:
                pass

    months = [8,9]
    WYsitedf = WYsitedf[~WYsitedf['M'].isin(months)]

    df = WYsitedf.copy()
    
    # Drop M and D before calculating stats
    year_cols = [col for col in WYsitedf.columns if col.endswith('_SWE_in')]
    WYsitedf_stats = WYsitedf[year_cols]
    print(WYsitedf_stats.columns.tolist())

    #add statistical columns
    df['min'] = WYsitedf_stats.min(axis=1)
    df['Q10'] = WYsitedf_stats.quantile(0.10, axis=1)
    df['Q25'] = WYsitedf_stats.quantile(0.25, axis=1)
    df['mean'] = WYsitedf_stats.mean(axis=1)
    df['median'] = WYsitedf_stats.median(axis=1)
    df['Q75'] = WYsitedf_stats.quantile(0.75, axis=1)
    df['Q90'] = WYsitedf_stats.quantile(0.90, axis=1)
    df['max'] = WYsitedf_stats.max(axis=1)

    df['date'] = pd.to_datetime(dict(year = 2023, month = df['M'], day = df['D'])) 
    df['M-D'] = df['date'].dt.strftime('%m-%d')
    df.set_index('M-D', inplace=True)


    # Save processed data
    OutputFolder = 'files/SNOTEL_processed'
    if not os.path.exists(OutputFolder):
        os.makedirs(OutputFolder)
    df.to_csv(f'{OutputFolder}/{site}_processed.csv')

    return df

def clean_nwis_dataframe(df):
    """
    Cleans an NWIS Daily Values (DV) DataFrame:
    - Converts index to datetime (date only)
    - Renames '00060_Mean' to 'flow_cfs'
    - Removes any extra '00060_Mean_cd' (qualification code) columns
    """
    # 1. Ensure the index is datetime and strip H:M:S
    df.index = pd.to_datetime(df.index).date
    df.index = pd.to_datetime(df.index)
    
    # 2. Rename the flow column
    # USGS usually names this '00060_Mean' for Daily Values
    if '00060_Mean' in df.columns:
        df.rename(columns={'00060_Mean': 'flow_cfs'}, inplace=True)
    
    # 3. Remove the '00060_Mean_cd' column (the metadata/quality code)
    if '00060_Mean_cd' in df.columns:
        df.drop(columns=['00060_Mean_cd'], inplace=True)
    
    # 4. Replace negative values with NaN
    df['flow_cfs'] = df['flow_cfs'].where(df['flow_cfs'] >= 0)

    #5 our other measurements are all in SI units, lets convert cfs to cms
    df['flow_cfs'] = df['flow_cfs'] * 0.0283168
    df.rename(columns={'flow_cfs': 'flow_cms'}, inplace=True)

    return df