import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import seaborn as sns
import shapely.ops
import cartopy.crs as ccrs
import matplotlib.patheffects as pe

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

# make points a geo data frame
points = gpd.GeoDataFrame(
    dfc_sub, 
    geometry = gpd.points_from_xy(dfc_sub.LON, dfc_sub.LAT),
    crs = "EPSG:4326"
)

# filter to north atlantic basin
n_atl = basins[basins["basin name"] == "N Atlantic"]

# filter to only points inside of North Atlantic basin
points_natl = gpd.sjoin(
    points,
    n_atl,
    predicate="within",
    how="inner"
)
points_natl = points_natl.drop(columns=["index_right"])

# filter out Arctic and CONUS subbasin
exclude_subbasins = ["Arctic", "Mid-latitudinal US/CA"] 
sub_basins_filtered = sub_basins[~sub_basins["sub_basin_name"].isin(exclude_subbasins)]

# assign each point to its correct subbasin
points_natl_sub = gpd.sjoin(
    points_natl,
    sub_basins_filtered,
    predicate="within",
    how="left"
)
points_natl_sub = points_natl_sub.drop(columns=["index_right"])

# aggregate TC counts by year
counts = (
    points_natl_sub
    .groupby(["YEAR", "sub_basin_name"])
    .size()
    .reset_index(name="count")
)

# correlation matrix between sub-basins
pivot = counts.pivot(
    index="YEAR",
    columns="sub_basin_name",
    values="count"
).fillna(0)

corr_matrix = pivot.corr()
print(corr_matrix)

# plot correlation matrix
plt.figure(figsize=(10,8))

sns.heatmap(
    corr_matrix,
    annot=True,
    cmap="coolwarm",
    vmin=-1,
    vmax=1
)

plt.title("North Atlantic TC Count Correlation By Sub-Basin")
plt.tight_layout()
plt.savefig("./capstone project/NAtlantic_sub_basins_correlation_matrix.png")
plt.show()

# shift longitude for next plots
def shift_lon(geom):
    return shapely.ops.transform(
        lambda x, y: (((x + 180) % 360) - 180, y),
        geom
    )

sub_basins_filtered["geometry"] = sub_basins_filtered["geometry"].apply(shift_lon)
basins["geometry"] = basins["geometry"].apply(shift_lon)
points_natl_sub["geometry"] = points_natl_sub["geometry"].apply(shift_lon)

# plot TC points over subbasin map
# get latitude bounds from the points
min_lat = points_natl_sub.geometry.y.min()
max_lat = points_natl_sub.geometry.y.max()

# longitude bounds
min_lon = points_natl_sub.geometry.x.min()
max_lon = points_natl_sub.geometry.x.max()

fig = plt.figure(figsize=(10,8))
ax = plt.axes(projection=ccrs.PlateCarree())

# set map extent
ax.set_extent([min_lon-5, max_lon+5, min_lat-5, max_lat+2], crs=ccrs.PlateCarree())

# coastlines
ax.coastlines(resolution="50m", linewidth=1)

# plot subbasin boundaries only
sub_basins_filtered.boundary.plot(
    ax=ax,
    color="black",
    linewidth=1,
    transform=ccrs.PlateCarree()
)

# plot TC points
points_natl_sub.plot(
    ax=ax,
    color="lightblue",
    markersize=1.5,
    alpha=0.6,
    transform=ccrs.PlateCarree()
)

# add labels for each subbasin
for idx, row in sub_basins_filtered.iterrows():
    label_point = row.geometry.representative_point()

    ax.text(
        label_point.x,
        label_point.y,
        row["sub_basin_name"],
        transform=ccrs.PlateCarree(),
        fontsize=9,
        fontweight="bold",
        ha="center",
        color="black",
        path_effects=[pe.withStroke(linewidth=3, foreground="white")]
    )

plt.title("TCs Points per North Atlantic Sub-Basins")
plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.tight_layout()
plt.savefig("./capstone project/NAtlantic_TC_count_sub_basins.png")
plt.show()