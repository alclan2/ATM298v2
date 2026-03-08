import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform

# path to the dataset
ClassifiedData = r"C:\Users\allcl\OneDrive\Desktop\desktop\grad school\0. Research\SyCLoPS\dataset\SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
dfc = pd.read_parquet(ClassifiedData)

# select TC and TD LPS nodes and filter QS out of Track_Info
dfc_sub = dfc[((dfc.Short_Label=='TC') | (dfc.Short_Label=='TD')) & ~(dfc['Track_Info'].str.contains('QS', case=False, na=False))]

# use tc_basins file to filter to a specific basin
# make a new column with YEAR only from ISOTIME
dfc_sub["YEAR"] = pd.to_datetime(dfc_sub["ISOTIME"]).dt.year

polygons_dict = {}

with open(r"capstone project\tc_basins.dat", "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(",")
        basin_name = parts[0].replace('"', '')
        n_vertices = int(parts[1])

        lon_vals = list(map(float, parts[2:2+n_vertices]))
        lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

        coords = list(zip(lon_vals, lat_vals))
        poly = Polygon(coords)

        if basin_name not in polygons_dict:
            polygons_dict[basin_name] = []
        polygons_dict[basin_name].append(poly)

# Convert to GeoDataFrame
basin_records = []

for name, poly_list in polygons_dict.items():
    if len(poly_list) == 1:
        geom = poly_list[0]
    else:
        geom = MultiPolygon(poly_list)

    basin_records.append({
        "basin name": name,
        "geometry": geom
    })

basins = gpd.GeoDataFrame(basin_records, crs="EPSG:4326")

# fix invalid polygons
basins["geometry"] = basins["geometry"].buffer(0)

# remove empy geometries
basins = basins[~basins.geometry.is_empty]

# filter points
points = gpd.GeoDataFrame(
    dfc_sub, 
    geometry = gpd.points_from_xy(dfc_sub.LON, dfc_sub.LAT),
    crs = "EPSG:4326"
)

filtered = gpd.sjoin(
    points,
    basins[basins["basin name"] == "NE Pacific"],
    how = "inner",
    predicate = "within"
)

# set index to ISOTIME column by year
filtered = filtered.set_index("ISOTIME")
#dfc_sub['YEAR'] = dfc_sub.index.year

# create 4deg bins
filtered['lat_bin'] = 4 * np.floor(filtered["LAT"] / 4)
filtered['lon_bin'] = 4 * np.floor(filtered["LON"] / 4)

# convert lon to -180-180 from 0-360
filtered['lon_bin'] = ((filtered['lon_bin'] + 180) % 360) - 180

# calc number TCs per bin
annual_TC_counts = filtered.groupby(["YEAR", "lat_bin", "lon_bin"]).size().reset_index(name="n_cyclones")

# pivot to get format: rows = year, columns = grid cells
wide_counts = annual_TC_counts.pivot(index="YEAR", columns=["lat_bin", "lon_bin"], values="n_cyclones").fillna(0)

# optional: compute climatological mean for each grid cell
cell_mean = wide_counts.mean(axis=0)

# subtract each cell's own mean (compute anomalies)
wide_counts_anom = wide_counts - cell_mean

# unstack MultiIndex to get lat/lon as separate dims
wide_counts_anom = wide_counts_anom.unstack()

# give the DataArray a name (required for NetCDF variable name)
wide_counts_anom.name = "n_cyclone_anomaly"

# convert to xarray DataArray
ds = wide_counts_anom.to_xarray()

# rename dimensions
ds = ds.rename({"YEAR": "time", "lat_bin": "lat", "lon_bin": "lon"})

# convert time to datetime
ds["time"] = pd.to_datetime(ds["time"].values, format="%Y")

# save to NetCDF
#ds.to_netcdf("annual_tc_counts_NAtlantic_4deg.nc")


## sense checks
# Convert to xarray DataArray if needed
#da = ds  # already a DataArray

# Compute mean over time
#cell_means = da.mean(dim="time")
#print(cell_means)


#print("Overall min:", da.min().values)
#print("Overall max:", da.max().values)
#print("Overall mean:", da.mean().values)


#lat_test = da.lat.values[3]
#lon_test = da.lon.values[3]
#print(da.sel(lat=lat_test, lon=lon_test).values)

# Average over all years to see spatial pattern (should be ~0)
#da.mean(dim="time").plot()
#plt.title("Mean anomaly per grid cell (should be ~0)")
#plt.show()
# Pick a single year to see spatial anomalies
#da.sel(time="2000-01-01").plot()
#plt.title("Cyclone anomaly in 2000")
#plt.show()