import os
os.environ['USE_PYGEOS'] = '0'
from netCDF4 import Dataset
import numpy as np
from datetime import date
from tqdm import tqdm


import pandas as pd
import json

def get_terraclimate_data(lat_list, lon_list, varname, year_start, year_end, month_start, month_end):
    NUM_POINTS = len(lat_list)
    
    # TerraClimate OPeNDAP file URL
    pathname = f'http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_terraclimate_{varname}_1958_CurrentYear_GLOBE.nc'
    filehandle = Dataset(pathname, 'r', format="NETCDF4")
    
    # Get the variable handle
    datahandle = filehandle.variables[varname]
    # print(datahandle)
    
    # Get the scale and offset for the variable
    scale_factor = datahandle.scale_factor
    add_offset = datahandle.add_offset

    
    # Subset in time
    timehandle = filehandle.variables['time']
    time = timehandle[:]
    time_min = (date(year_start, month_start, 1) - date(1900, 1, 1)).days
    time_max = (date(year_end, month_end, 1) - date(1900, 1, 1)).days
    time_index_min = (np.abs(time - time_min)).argmin()
    time_index_max = (np.abs(time - time_max)).argmin()
    time_index_range = range(time_index_min, time_index_max + 1)
    time = timehandle[time_index_range]

    
    # Subset in space (lat/lon)
    lathandle = filehandle.variables['lat']
    lonhandle = filehandle.variables['lon']
    lat = lathandle[:]
    lon = lonhandle[:]
    # print(lat)
    
    myLat = []
    myLon = []
    myData = []
    myLat_org = []
    myLon_org = []
    
    for i in tqdm(range(NUM_POINTS)):
        # print(lat_list[i], lon_list[i])
        # Find indices of target lat/lon
        lat_index = (np.abs(lat - lat_list[i])).argmin()
        lon_index = (np.abs(lon - lon_list[i])).argmin()
        # print(lat[lat_index], lon[lon_index])
        
        # Get grid centers extracted
        myLat.append(lat[lat_index])
        myLon.append(lon[lon_index])

        myLat_org.append(lat_list[i])
        myLon_org.append(lon_list[i])
        
    #     # Subset data, applying the scale_factor and add_offset
        # myData.append(add_offset + scale_factor * datahandle[time_index_range, lat_index, lon_index])
        # print(myData)
        myData.append(datahandle[time_index_range, lat_index, lon_index])
        # print(myData)
    #     # print('*******************************')
        # break
    
    return myLat, myLon, myLat_org, myLon_org, myData



def generate_month_year_list(year_start, year_end, month_start, month_end):
    month_year_list = []
    for year in range(year_start, year_end + 1):
        start_month = month_start if year == year_start else 1
        end_month = month_end if year == year_end else 12
        for month in range(start_month, end_month + 1):
            month_year_list.append(f"{month:02d}-{year}")
    return month_year_list




def csv_to_geojson(csv_file, geojson_file):
    # Load the CSV file
    df = pd.read_csv(csv_file)
    
    # Create a list to hold the GeoJSON features
    features = []
    
    # Iterate over each row in the DataFrame
    for _, row in df.iterrows():
        # Extract properties except latitude and longitude
        properties = row.to_dict()
        lat = properties.pop('lat')
        lon = properties.pop('lon')
        
        # Create a feature for each row
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": properties
        }
        features.append(feature)
    
    # Create the GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Write the GeoJSON to a file
    with open(geojson_file, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"GeoJSON file created: {geojson_file}")




if __name__=='__main__':
    import pandas as pd
    import geopandas as gpd
    # coord_data = pd.read_csv('../RGB/assets/embedding_cluster_5.csv')
    coord_data = gpd.read_file('./data/ka-grid-4km.geojson')



    lab_list = list(coord_data['grid-id'])
    lon_list = list((coord_data['left']+ coord_data['right'])/2)
    lat_list = list((coord_data['top']+ coord_data['bottom'])/2)

    # print(len(lab_list))

    # Example usage
    year_start = 2023
    year_end = 2023
    month_start = 1
    month_end = 12


    month_year_list = generate_month_year_list(year_start, year_end, month_start, month_end)

    varnames = ['tmax','aet','tmin','vap','vpd','ws','def','swe','q','soil','PDSI','pet','ppt','srad']
    for varname in varnames:
        print(f'Processing : {varname}')
        myLat, myLon, myLat_org, myLon_org, data = get_terraclimate_data(lat_list, lon_list, varname, year_start, year_end, month_start, month_end)
        df = pd.DataFrame(data, columns=month_year_list)
        df['lat'] = myLat_org
        df['lon'] = myLon_org
        df['close_lat'] = myLat
        df['close_lon'] = myLon
        df['label'] = lab_list
        columns_order = ['label', 'lat', 'lon','close_lat','close_lon'] + month_year_list
        df = df[columns_order]
        
        csv_path = f'./data/weather-data/2023/data_{varname}.csv'
        geojson_path = f'./data/weather-data/2023/data_{varname}.geojson'
        df.to_csv(csv_path, index=False)

        csv_to_geojson(csv_path, geojson_path)

