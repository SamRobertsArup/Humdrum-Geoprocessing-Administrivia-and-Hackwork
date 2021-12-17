import gdal, ogr, osr, numpy
import sys, os

'''
 Calculates zonal statistics of a raster within a given polygon
 
 :USAGE:
 ZonalStats.py "path/to/polygon" "path/to/raster"
 
 :INPUT:
 polygon may be:
  - geopackage/featurename (.gpkg)
  - shapefile (.shp)  
  - geodatabase featureclass (.gdb/fcname)
  
 raster may be:
  - Esri ASCII raster (.asc) with associated .prj 
  - GeoTiff (.tif) with inlined metadata or associated .tfw
  
 :OUTPUT:
 Returns for each feature a dictionary item (FID) with the statistical values for each raster band
 in the following order:
 Average, Mean, Median, Standard Deviation, Variance


 :NOTE:
  - No data is ignored in the statistics if the raster's metadata contains a nodata value, else you'll get a warning
  - Polygon must be within raster extent
  - Raster must have an SRS

 Based on: https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html#calculate-zonal-statistics
 Modified by: Samuel.Roberts@Arup.com
'''

def zonal_stats(FID, input_zone_polygon, input_value_raster):

    # Open raster
    raster = gdal.Open(input_value_raster)

    # Open poly
    file_path, file_name, fc_name = get_file_path_fc(input_zone_polygon)
    try:
        file = ogr.Open(file_path, 0)
        layer_count = file.GetLayerCount()
    except Exception as e:
        sys.exit("[ ERROR ] File cannot be opened or does not exist\n"+e)
    for i, featsClass_idx in enumerate(range(layer_count)):
        lyr = file.GetLayerByIndex(featsClass_idx)
        if lyr.GetName() == fc_name:
            break
        elif layer_count - 1 == i:
            sys.exit(f"[ ERROR ] Feature {fc_name} not found in {file_path}")

    # Get raster georeference & info
    xmin_ras, pixelWidth, xskew, ymax_ras, yskew, pixelHeight = raster.GetGeoTransform()
    raster_info = gdal.Info(raster)

    # Reproject vector geometry to same projection as raster
    sourceSR = lyr.GetSpatialRef()
    targetSR = osr.SpatialReference()
    rasterSR = raster.GetProjectionRef()
    if rasterSR == "":
        print(gdal.Info(ds=raster, options=gdal.InfoOptions(approxStats=True, reportProj4=True)))
        sys.exit("[ ERROR ] Raster SRS undefined")
    targetSR.ImportFromWkt(rasterSR)
    coordTrans = osr.CoordinateTransformation(sourceSR, targetSR)


    # Get the feature NOTE: unlike lyr.GetFeatureIndex(FID) this (odd) method handles where FIDs may not be sequential
    if FID == 0:
        feat = lyr.GetNextFeature()
    else:
        for i in range(FID+1):
            feat = lyr.GetNextFeature()

    # Get extent of feat
    geom = feat.GetGeometryRef()
    geom.Transform(coordTrans)
    geom = feat.GetGeometryRef()
    if (geom.GetGeometryName() == 'MULTIPOLYGON'):
        count = 0
        pointsX = []; pointsY = []
        for polygon in geom:
            geomInner = geom.GetGeometryRef(count)
            ring = geomInner.GetGeometryRef(0)
            numpoints = ring.GetPointCount()
            for p in range(numpoints):
                    lon, lat, z = ring.GetPoint(p)
                    pointsX.append(lon)
                    pointsY.append(lat)
            count += 1
    elif (geom.GetGeometryName() == 'POLYGON'):
        ring = geom.GetGeometryRef(0)
        numpoints = ring.GetPointCount()
        pointsX = []; pointsY = []
        for p in range(numpoints):
                lon, lat, z = ring.GetPoint(p)
                pointsX.append(lon)
                pointsY.append(lat)
    else:
        sys.exit("[ ERROR ] Geometry needs to be either Polygon or Multipolygon")

    # calc bbox & centroid
    xmin_poly = min(pointsX)
    xmax_poly = max(pointsX)
    ymin_poly = min(pointsY)
    ymax_poly = max(pointsY)
    xCentroid_poly = (xmax_poly + xmin_poly)/2
    yCentroid_poly = (ymax_poly + ymin_poly)/2

    xmax_ras = xmin_ras + (raster.RasterXSize * pixelWidth)
    ymin_ras = ymax_ras + (raster.RasterYSize * pixelHeight)
    if not (xCentroid_poly >= xmin_ras and xCentroid_poly <= xmax_ras and yCentroid_poly <= ymax_ras and yCentroid_poly >= ymin_ras):
        sys.exit("[ ERROR ] Polygon is outside raster")

    # Specify offset and rows and columns to read
    xoff = int((xmin_poly - xmin_ras)/pixelWidth)
    yoff = int((ymax_ras - ymax_poly)/pixelWidth)
    xcount = int((xmax_poly - xmin_poly)/pixelWidth)+1
    ycount = int((ymax_poly - ymin_poly)/pixelWidth)+1

    # Create memory target raster
    target_ds = gdal.GetDriverByName('MEM').Create('', xcount, ycount, 1, gdal.GDT_Byte)
    target_ds.SetGeoTransform((
        xmin_poly, pixelWidth, 0,
        ymax_poly, 0, pixelHeight,
    ))

    # Create for target raster the same projection as for the value raster
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(raster.GetProjectionRef())
    target_ds.SetProjection(raster_srs.ExportToWkt())

    # Rasterise zone polygon to raster
    gdal.RasterizeLayer(target_ds, [1], lyr, burn_values=[1])

    bandmask = target_ds.GetRasterBand(1)
    datamask = bandmask.ReadAsArray(0, 0, xcount, ycount).astype(numpy.float)
    # Read raster as arrays

    no_data_value = None
    try:
        no_data_value = int(raster_info.split("NoData Value=")[1].split(" ")[0])  # GetNoDataValue() doesn't work?
    except Exception as ex:
        print("[ WARNING ] Cannot identify nodata value!")

    stats = {}
    for band in range(1, raster.RasterCount+1):

        # get band
        banddataraster = raster.GetRasterBand(band)
        dataraster = banddataraster.ReadAsArray(xoff, yoff, xcount, ycount).astype(numpy.float)

        # name band if known
        try:
            band = raster_info.split(f"Band {band}")[1].split("ColorInterp=")[1].split("\n")[0]
            # GetColorInterpretationName() doesn't work?
        except Exception as ex:
            pass

        # Mask zone of raster
        zoneraster = numpy.ma.masked_array(dataraster, numpy.logical_not(datamask))

        # mask no data of raster
        if no_data_value is not None:
            zoneraster = numpy.ma.masked_equal(zoneraster, no_data_value)

        # Calculate statistics of zonal raster for each band
        stats[band] = {'avg': numpy.average(zoneraster),
                       'mean': numpy.mean(zoneraster),
                       'median': numpy.median(zoneraster),
                       'std': numpy.std(zoneraster),
                       'variance': numpy.var(zoneraster)}
    return stats


def get_file_path_fc(input_path):
    file_name = [path for path in input_path.split('\\') if '.' in path][0]
    fc_name = input_path.split(file_name)[-1].strip('\\')
    file_path = input_path
    if fc_name == '':
        fc_name = os.path.splitext(file_name)[0]
    else:
        file_path = input_path.split('\\'+fc_name)[0]
    return file_path, file_name, fc_name


def loop_zonal_stats(input_zone_polygon, input_value_raster):
    file_path, file_name, fc_name = get_file_path_fc(input_zone_polygon)

    # Open poly
    file_path, file_name, fc_name = get_file_path_fc(input_zone_polygon)
    try:
        file = ogr.Open(file_path, 0)
        layer_count = file.GetLayerCount()
    except Exception as e:
        sys.exit("[ ERROR ] File cannot be opened or does not exist, check path\n"+e)
    for i, featsClass_idx in enumerate(range(layer_count)):
        lyr = file.GetLayerByIndex(featsClass_idx)
        if lyr.GetName() == fc_name:
            break
        elif layer_count - 1 == i:
            sys.exit(f"[ ERROR ] Feature {fc_name} not found in {file_path}")

    statDict = {}
    featList = range(lyr.GetFeatureCount())
    for FID in featList:
        statDict[FID] = zonal_stats(FID, input_zone_polygon, input_value_raster)

    return statDict


def main(input_zone_polygon, input_value_raster):
    return loop_zonal_stats(input_zone_polygon, input_value_raster)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("[ ERROR ] you must supply two arguments: \"path/to/polygon\" \"path/to/raster\" ")
    res = main(sys.argv[1], sys.argv[2])
    print(res)