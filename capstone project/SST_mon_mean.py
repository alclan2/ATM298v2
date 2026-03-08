import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import xarray as xr
import rioxarray
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import cartopy.feature as cfeature
import numpy as np
import regionmask
import seaborn as sns

# read in basin definition file
polygons_dict = {}

# read in basin definition file
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

# convert basins' lon to -180-180
basins["geometry"] = basins["geometry"].apply(
    lambda geom: transform(
        lambda x, y: (((x + 180) % 360) - 180, y),
        geom
    )
)

# read in tc_subbasins_NAtl file
sub_polygons_dict = {}

with open(r"capstone project\tc_subbasins_NAtl.dat", "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(",")
        sub_basin_name = parts[0].replace('"', '')
        n_vertices = int(parts[1])

        lon_vals = list(map(float, parts[2:2+n_vertices]))
        lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

        coords = list(zip(lon_vals, lat_vals))
        poly = Polygon(coords)

        if sub_basin_name not in sub_polygons_dict:
            sub_polygons_dict[sub_basin_name] = []
        sub_polygons_dict[sub_basin_name].append(poly)

# Convert to GeoDataFrame
sub_basin_records = []

for name, poly_list in sub_polygons_dict.items():
    if len(poly_list) == 1:
        geom = poly_list[0]
    else:
        geom = MultiPolygon(poly_list)

    sub_basin_records.append({
        "sub_basin_name": name,
        "geometry": geom
    })

sub_basins = gpd.GeoDataFrame(sub_basin_records, crs="EPSG:4326",geometry="geometry")

# fix invalid polygons
sub_basins["geometry"] = sub_basins["geometry"].buffer(0)

# remove empty geometries
sub_basins = sub_basins[~sub_basins.geometry.is_empty]

# longitude conversion
import shapely.ops
def shift_lon(geom):
    return shapely.ops.transform(
        lambda x, y: (((x + 180) % 360) - 180, y),
        geom
    )

# shift lon
sub_basins["geometry"] = sub_basins["geometry"].apply(shift_lon)

# open COBE SST monthly mean file
time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)
ds = xr.open_dataset(r"capstone project\netcdf_files\sst.mon.mean.nc", decode_times=time_coder)

# filter to only SST variable
sst = ds["sst"]

# convert lon to -180-180
sst = sst.assign_coords(
    lon=(((sst.lon + 180) % 360) - 180)
).sortby("lon")

# add CRS and spatial dims
sst = sst.rio.write_crs("EPSG:4326")
sst = sst.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atlantic basin
region = basins[basins["basin name"] == "N Atlantic"]

# filter out Arctic and continental US sub-basins
region_subbasins = sub_basins[sub_basins["sub_basin_name"].isin(["Gulf", "Caribbean", "Northeastern Seaboard", "Tropical Atlantic", "Subtropical Atlantic", "Mid-latitudinal Atlantic", "Southeastern Seaboard"])]

sst_filt = (
    sst
    .rio.clip(region.geometry, region.crs, drop=True)
    .rio.clip(region_subbasins.geometry, region_subbasins.crs, drop=True)
    .sel(time=slice(None, "2025-12-31"))
)

# calculate the climatological mean
monthly_clim = sst_filt.groupby("time.month").mean("time")

# calculate the sst anomaly
sst_anom = sst_filt.groupby("time.month") - monthly_clim

# create an empty dict to store time series per sub-basin
subbasin_sst = {}

for idx, row in region_subbasins.iterrows():
    sub_name = row["sub_basin_name"]
    geom = row.geometry

    # clip SST anomaly to the sub-basin polygon
    sst_clip = sst_anom.rio.clip([geom], sst_anom.rio.crs, drop=True)

    # calculate mean over spatial dims and convert to pandas Series
    mean_series = sst_clip.mean(dim=["lat", "lon"]).to_series()
    
    subbasin_sst[sub_name] = mean_series

# combine all sub-basin time series into a DataFrame
df_sst = pd.concat(subbasin_sst, axis=1)
#print(df_sst.head())

corr_sst = df_sst.corr()
print(corr_sst)

# plot correlation matrix
plt.figure(figsize=(8,6))
sns.heatmap(corr_sst, annot=True, cmap="coolwarm", vmin=-1, vmax=1)
plt.title("SST Anomaly Correlation Across Sub-Basins (Monthly)")
plt.tight_layout()
plt.savefig("./capstone project/NAtlantic_SST_mon_mean_anom_sub_basins.png")
plt.show()