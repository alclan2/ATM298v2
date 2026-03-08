import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import os

# path to the classified dataset
ClassifiedData = r"C:\Users\allcl\OneDrive\Desktop\desktop\grad school\0. Research\SyCLoPS\dataset\SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
dfc = pd.read_parquet(ClassifiedData)

# select TC and TD LPS nodes and filter QS out of Track_Info
dfc_sub = dfc[((dfc.Short_Label=='TC') | (dfc.Short_Label=='TD')) & ~(dfc['Track_Info'].str.contains('QS', case=False, na=False))]

# make a new column with YEAR only from ISOTIME
dfc_sub["YEAR"] = pd.to_datetime(dfc_sub["ISOTIME"]).dt.year

polygons_dict = {}

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "tc_basins.dat")

with open(file_path, "r") as f:
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

basins = gpd.GeoDataFrame(basin_records, geometry = "geometry", crs="EPSG:4326")

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

# pivot by year and count of TCs or TDs
count = filtered.groupby("YEAR").size()

# make the scatter plot for all TCs/TDs
plt.figure(figsize = (12,6))
plt.scatter(x = count.index, y = count.values)

# set tick marks to 10 yr intervals
plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(5))
plt.grid(color = 'gray', linestyle = '--', linewidth = 0.6, alpha = 0.5)

# axis labels
plt.xlabel('Year')
plt.ylabel('Number of TCs/TDs')
plt.title('Number of TCs/TDs in North Atlantic from 1940-2024')

# Plot basins
ax = basins.plot(edgecolor='black', alpha=0.5, figsize=(12, 8))
points.plot(ax=ax, color='blue', markersize=10)

# Add basin labels
for idx, row in basins.iterrows():
    geom = row.geometry
    name = row["basin name"]
    
    # For MultiPolygon, use the largest polygon
    if geom.geom_type == "MultiPolygon":
        largest_poly = max(geom.geoms, key=lambda p: p.area)
        centroid = largest_poly.centroid
    else:
        centroid = geom.centroid
    
    ax.text(
        centroid.x,
        centroid.y,
        name,
        horizontalalignment='center',
        fontsize=10,
        fontweight='bold',
        color='white'
    )

# axis limits
ax.set_xlim(0, 360)
ax.set_ylim(-90, 90)

ax.set_xticks(range(0, 361, 60))
ax.set_yticks(range(-90, 91, 30))

plt.title("TC Basins Layered with SyCLoPS Data Points")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()