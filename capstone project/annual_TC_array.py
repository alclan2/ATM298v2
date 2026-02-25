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
    basins[basins["basin name"] == "N Atlantic"],
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
ds.to_netcdf("annual_tc_counts_NAtlantic_4deg.nc")





#sense check
#ds = xr.open_dataset("annual_tc_counts_NAtlantic.nc")
#print(ds.n_cyclones.sel(time="1990"))
#da_1990 = ds.n_cyclones.sel(time="1990").squeeze()
#print(da_1990)

# sense check: print top 5 cells
#N = 5 
#flat_indices = np.argsort(arr.flatten())[::-1][:N]  # indices of top N values
#rows, cols = np.unravel_index(flat_indices, arr.shape)
#for r, c in zip(rows, cols):
#    print(f"Year: {wide_counts.index[r]}, Cell (lat, lon): {wide_counts.columns[c]}, Cyclones: {arr[r, c]}")


# sense check: print a sample of the array
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

