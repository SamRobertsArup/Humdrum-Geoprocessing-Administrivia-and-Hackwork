import geopandas as gpd
import requests
import json
from shapely.geometry import shape

def getFrom(url):
    res = requests.get(url)
    data = json.loads(res.text)
    return data

def getDataESRImapserver(url, bbox, sr):
    name=url.split("services/")[1].split("/MapServer")[0]
    print(f"fetching {name} data")
    wkid = "".join([c for c in str(sr) if c in '0123456789'])
    geometry = {  # http://sampleserver3b.arcgisonline.com/arcgis/SDK/REST/geometry.html
        "xmin": bbox[0], "ymin": bbox[1], "xmax": bbox[2], "ymax": bbox[3],
        "spatialReference": {"wkid": wkid}
    }
    # feature 0 is vector corine data
    url += f"&geometry={geometry}&inSR={wkid}&outSR={wkid}"
    url += "&outFields=*"
    #url += "&objectIds=*" # can specify individual IDs but not all!??!?!

    corine_data = getFrom(url)
    features = corine_data['features']
    features_retrieved = len(features)
    while 'exceededTransferLimit' in corine_data.keys():
        print(f"fetched {features_retrieved}")
        if "&resultOffset" in url:
            url = url.split("&resultOffset")[0]
        url+=f"&resultOffset={features_retrieved}"
        corine_data = getFrom(url)
        features += corine_data['features']
        features_retrieved += len(features)
    print(f"feature count: {features_retrieved}")

    # convert to geopandas dataframe
    geom = [shape(f['geometry']) for f in features]
    props = [f['properties'] for f in features]
    features_df = gpd.GeoDataFrame(data=props, geometry=geom).set_crs(sr)

    return features_df

if __name__ == "__main__":
    aoiPath = r"C:\dev\Requests and Tasks\EAST LINDSEY heatmap\data\AOI\WithernTheddlethorpeMarblethorpeWards.shp"
    aoi = gpd.read_file(aoiPath)
    bbox = aoi.total_bounds
    sr = aoi.crs
    
    floodZone2_wfs = "https://environment.data.gov.uk/arcgis/rest/services/EA/FloodMapForPlanningRiversAndSeaFloodZone2/MapServer/0/query?where=1%3D1&f=geojson"
    floodZone3_wfs = "https://environment.data.gov.uk/arcgis/rest/services/EA/FloodMapForPlanningRiversAndSeaFloodZone3/MapServer/0/query?where=1%3D1&f=geojson"
    corine_wfs = "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/0/query?where=1%3D1&f=geojson"

    data = getDataESRImapserver(url=floodZone3_wfs, bbox=bbox, sr=sr)

    data.to_file(r"C:\dev\Requests and Tasks\EAST LINDSEY heatmap\data\fz3.shp")
