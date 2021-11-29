from shapely.geometry import Polygon
import geopandas as gdp
import numpy as np
import tqdm
import os

def generateGrid(bbox, cell_m, crs):
    """
    bbox: area to grid
    cell_m: side of a grid square in m / crs unit 
    crs: coordinate reference system (only tested with crs using m ie UTM, BNG...)
    """
    xmin, ymin, xmax, ymax = bbox
    cellsX = int(np.ceil((xmax - xmin) / cell_m))
    cellsY = int(np.ceil((ymax - ymin) / cell_m))
    x = np.linspace(xmin, xmax, num=cellsX)
    y = np.linspace(ymin, ymax, num=cellsY)
    print(f"Grid will be {cellsX} (x) by {cellsY} (y) cells where each cell is {cell_m}m2")

    polygons = []
    cols = []
    rows = []
    print("creating grid...")
    for i in tqdm.tqdm(range(len(x)-1)):
        for j in range(len(y)-1):
            cell = Polygon([(x[i], y[j]), (x[i + 1], y[j]), (x[i + 1], y[j + 1]), (x[i], y[j + 1])])
            polygons.append(cell)
            cols.append(i)
            rows.append(j)
    polyGrid = gdp.GeoDataFrame({'geometry': polygons, 'col': cols, 'row':rows}, crs=crs).set_crs(crs)

    return polyGrid

if __name__ == "__main__":

    outpath=r"C:\dev\temp\UK10kmGrid.shp"
    bbox = [-90619.29, 10097.13, 612435.55, 1234954.16]  # UK bbox BNG
    cell_m = 10000  # 10 km grid cells
    espg = 27700  # espg code

    if not outpath.endswith(".shp"):
        outpath = os.path.join(outpath, "grid.shp")
        
    polyGrid=generateGrid(bbox, cell_m, espg)
    polyGrid.to_file(outpath)
