import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import cartopy.crs as ccrs

# path to the classified dataset
ClassifiedData = r"C:\Users\allcl\OneDrive\Desktop\desktop\grad school\0. Research\SyCLoPS\dataset\SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
dfc = pd.read_parquet(ClassifiedData)

# select TC and TD LPS nodes and filter QS out of Track_Info
dfc_sub = dfc[((dfc.Short_Label=='TC') | (dfc.Short_Label=='TD')) & ~(dfc['Track_Info'].str.contains('QS', case=False, na=False))]

# make a new column with YEAR only from ISOTIME
dfc_sub["YEAR"] = pd.to_datetime(dfc_sub["ISOTIME"]).dt.year

# pivot by year and count of TCs or TDs
count = dfc_sub.groupby("YEAR").size()

# make the scatter plot for all TCs/TDs
plt.figure(figsize = (12,6))
plt.scatter(x = count.index, y = count.values)

# set tick marks to 10 yr intervals
plt.gca().xaxis.set_major_locator(ticker.MultipleLocator(5))
plt.grid(color = 'gray', linestyle = '--', linewidth = 0.6, alpha = 0.5)

# axis labels
plt.xlabel('Year')
plt.ylabel('Number of TCs/TDs')
plt.title('Number of TCs/TDs from 1940-2024 (GLOBAL)')

plt.show()