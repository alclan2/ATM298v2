## Analyzing North Atlantic Ocean Tropical Cyclone Sub-Basins

# Project Introduction

The goal of this project is to identify and evaluate sub-basins within the North Atlantic Ocean basin based on Tropical Cyclone (TC) activity. Geography-based sub-basins can be used to identify signaling between key metrics for TC development and behavior.

# Data Overview

Two key datasets were used in this project:
- System for Classification of Low-Pressure Systems (SyCLoPS): dataset developed by Yushan Han (UC Davis) and Paul Ullrich (UC Davis) which contains classifications for low-pressue systems (tropical cyclone, tropical depression, subtropical cyclone, etc.) across the globe from 1940-2024. Dataset can be found here: https://zenodo.org/records/18320508.
- Centennial in situ Observation-Based Estimates (COBE2-SST): dataset developed by NOAA which contains sea surface temperature monthly means across the globe from 1850-2026 Dataset can be found here: https://psl.noaa.gov/data/gridded/data.cobe2.html.

# Methodology

First, sub-basins for the North Atlantic Ocean were determined based on common geographical regions. The regions are as follows:
- Arctic
- Mid-latitudinal US/CA
- Mid-latitudinal Atlantic
- Northeastern Seaboard
- Gulf
- Southeastern Seaboard
- Caribbean
- Subtropical Atlantic
- Tropical Atlantic
Basin and sub-basin polygon definitions are stored in the "basin polygons" folder.

Both SyCLoPS and COBE datasets were filtered to North Atlantic data points only as well as assigned to a sub-basin. Arctic and Mid-latitudinal US/CA sub-basins were excluded due to low or no TC data in these regions.

Two analyses were performed to determine correlation between sub-basins for TC annual count and SST monthly mean anomaly.

For the frequency analysis, after filtering the SyCLoPS dataset to include tropical cyclones and tropical depressions only, the count of TCs per sub-basin was calculated per year. A correlation matrix was then produced for the correlation between sub-basins based on annual TC count.

For the SST analysis, the monthly mean SST anomaly was calculated for each data point after calculating the monthly climatological mean. Then the data was aggregated to each sub-basin and the sub-basin monthly mean SST anomaly was calculated. A correlation matric was then produced for the correlation between sub-basins based on SST monthly mean anomaly. 

# References

[https://doi.org/10.1029/2024JD041287] Han, Y. and P.A. Ullrich (2025) "The System for Classification of Low-Pressure Systems (SyCLoPS): An all-in-one objective framework for large-scale datasets" J. Geophys. Res. Atm. 130 (1), e2024JD041287, doi: 10.1029/2024JD041287.