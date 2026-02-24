import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

# path to the dataset
ClassifiedData = r"C:\Users\allcl\OneDrive\Desktop\desktop\grad school\0. Research\SyCLoPS\dataset\SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
dfc = pd.read_parquet(ClassifiedData)

# select TC and TD LPS nodes and filter QS out of Track_Info
dfc_sub = dfc[((dfc.Short_Label=='TC') | (dfc.Short_Label=='TD')) & ~(dfc['Track_Info'].str.contains('QS', case=False, na=False))]

# set index to ISOTIME column by year
dfc_sub = dfc_sub.set_index("ISOTIME")
dfc_sub['YEAR'] = dfc_sub.index.year

# create 4deg bins
dfc_sub['lat_bin'] = 4 * np.floor(dfc_sub["LAT"] / 4)
dfc_sub['lon_bin'] = 4 * np.floor(dfc_sub["LON"] / 4)

# convert lon to -180-180 from 0-360
dfc_sub['lon_bin'] = ((dfc_sub['lon_bin'] + 180) % 360) - 180

# calc number TCs per bin
annual_TC_counts = dfc_sub.groupby(["YEAR", "lat_bin", "lon_bin"]).size().reset_index(name="n_cyclones")

# give each line an ID
annual_TC_counts["cell_id"] = list(zip(annual_TC_counts["lat_bin"], annual_TC_counts["lon_bin"]))

# pivot to get format: rows = year, columns = grid cells
wide_counts = annual_TC_counts.pivot(index="YEAR", columns="cell_id", values="n_cyclones").fillna(0)

# convert to array
arr = wide_counts.values


# save to net cdf format for region generation function
# Get unique sorted coordinates
years = np.sort(annual_TC_counts["YEAR"].unique())
lats = np.sort(annual_TC_counts["lat_bin"].unique())
lons = np.sort(annual_TC_counts["lon_bin"].unique())

# Create empty 3D array (year x lat x lon)
data = np.zeros((len(years), len(lats), len(lons)))

# Fill array
for _, row in annual_TC_counts.iterrows():
    y_idx = np.where(years == row["YEAR"])[0][0]
    lat_idx = np.where(lats == row["lat_bin"])[0][0]
    lon_idx = np.where(lons == row["lon_bin"])[0][0]
    data[y_idx, lat_idx, lon_idx] = row["n_cyclones"]

# Create xarray DataArray
da = xr.DataArray(
    data,
    coords={
        "year": years,
        "lat": lats,
        "lon": lons
    },
    dims=["year", "lat", "lon"],
    name="n_cyclones"
)

da = da.rename({"year": "time"})
da["time"] = pd.to_datetime(da["time"].values, format="%Y")

# Convert to Dataset (recommended for NetCDF)
ds = da.to_dataset()

# save to netcdf file
ds.to_netcdf("annual_tc_counts.nc")

#sense check
ds = xr.open_dataset("annual_tc_counts.nc")
print(ds.n_cyclones.sel(time="1990"))

da_1990 = ds.n_cyclones.sel(time="1990").squeeze()
print(da_1990)


# check: print top 5 cells
#N = 5 
#flat_indices = np.argsort(arr.flatten())[::-1][:N]  # indices of top N values
#rows, cols = np.unravel_index(flat_indices, arr.shape)

#for r, c in zip(rows, cols):
#    print(f"Year: {wide_counts.index[r]}, Cell (lat, lon): {wide_counts.columns[c]}, Cyclones: {arr[r, c]}")


# check: print a sample of the array
#cells = (
#    dfc_sub[['lat_bin', 'lon_bin']]
#    .drop_duplicates()
#    .sort_values(['lat_bin', 'lon_bin'])
#    .reset_index(drop=True)
#)

#years = np.sort(dfc_sub["YEAR"].unique())

#nyears, ncells = arr.shape

#random_year_idx = np.random.choice(nyears, 3, replace=False)
#random_cell_idx = np.random.choice(ncells, 5, replace=False)

#sample = arr[np.ix_(random_year_idx, random_cell_idx)]

#row_labels = years[random_year_idx]

#col_labels = [
#    f"({cells.loc[i,'lat_bin']}, {cells.loc[i,'lon_bin']})"
#    for i in random_cell_idx
#]

#df_sample = pd.DataFrame(sample, index=row_labels, columns=col_labels)
#print(df_sample)

