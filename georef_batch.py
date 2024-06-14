#!/usr/bin/env python3

import logging
import pandas
from pyproj import CRS, Transformer
import json
from os.path import exists
from pathlib import Path
import sys
from osgeo import gdal, ogr, osr
import os
import tempfile
import zipfile
import geopandas

def saveGeoref(input_file, output_file, projection, transform_type, gcp_list, cutline):
    logging.debug(output_file)
    src_ds = gdal.Open(input_file)
    # translate and warp the inputFile using GCPs and polynomial of order 1
    dst_ds = gdal.Translate('', src_ds, outputSRS=projection, GCPs=gcp_list, format='MEM')
    tps = False
    if transform_type == 'poly1':
        polynomialOrder = 1
        gdal.Warp(output_file, dst_ds, tps=tps, polynomialOrder=polynomialOrder, dstNodata=1, cutlineDSName=cutline)
    elif transform_type == 'poly2':
        polynomialOrder = 2
        gdal.Warp(output_file, dst_ds, tps=tps, polynomialOrder=polynomialOrder, dstNodata=1, cutlineDSName=cutline)
    elif transform_type == 'poly3':
        polynomialOrder = 3
        gdal.Warp(output_file, dst_ds, tps=tps, polynomialOrder=polynomialOrder, dstNodata=1, cutlineDSName=cutline)
    elif transform_type == 'tps':
        tps = True
        gdal.Warp(output_file, dst_ds, tps=tps, dstAlpha=True, cutlineDSName=cutline)
    else:
        polynomialOrder = 1
        gdal.Warp(output_file, dst_ds, tps=tps, polynomialOrder=polynomialOrder, dstNodata=1, cutlineDSName=cutline)

def georef(input_file, gcp_file, output_raster_file, projection, transform_type, polygon, old_format=False):
    # reading the CSV file
    csvFile = pandas.read_csv(gcp_file, comment='#')
    # displaying the contents of the CSV file
    if old_format:
        gcp_list = [gdal.GCP(row['mapX'], row['mapY'], 0, row['pixelX'], -row['pixelY']) for _, row in csvFile.iterrows()]
    else:
        gcp_list = [gdal.GCP(row['mapX'], row['mapY'], 0, row['sourceX'], -row['sourceY']) for _, row in csvFile.iterrows()]
    saveGeoref(input_file, output_raster_file, projection, transform_type, gcp_list, polygon)

def georef_vector(input_file, gcp_file, output_vector_file, projection_string, transform_type, old_format=False):
    # reading the CSV file
    csvFile = pandas.read_csv(gcp_file, comment='#')
    Path(output_vector_file).parent.mkdir(parents=True, exist_ok=True)
    # vector layer
    gcp_text = ''
    if old_format:
        for _, row in csvFile.iterrows():
            gcp_text += ' -gcp ' + str(row['pixelX']) + ' ' + str(row['pixelY']) + ' ' + str(row['mapX']) + ' ' + str(row['mapY'])
    else:
        for _, row in csvFile.iterrows():
            gcp_text += ' -gcp '+  str(row['sourceX']) + ' ' + str(row['sourceY']) + ' ' + str(row['mapX']) + ' ' + str(row['mapY'])
    command = f"ogr2ogr -a_srs \"{projection_string}\" -{transform_type} {gcp_text} \"{output_vector_file}\" \"{input_file}\""
    logging.warning(command)
    os.system(command)
    layername = os.path.basename(input_file.replace(".shp",""))
    gdf = geopandas.read_file(output_vector_file, layer=layername)
    modif = False
    def concat(aList): return " ".join(list(filter(lambda item: item is not None, aList)))
    if 'NOM_SAISI' not in gdf.columns:  # check if field exists
        gdf['NOM_SAISI'] = gdf.agg(lambda x: concat([x['PREFIXE 1'],x['PREFIXE 2'],x['NOM_RUE']]), axis=1)
        modif = True
    if 'EXP_GEO' not in gdf.columns:  # check if field exists
        gdf['EXP_GEO'] = 1
        modif = True
    if modif:
        gdf.to_file(output_vector_file, layer=layername, driver="GPKG")

def georef_csv(csv_file_name:str, projection_string:str, tps = False):
    logging.basicConfig(level=logging.DEBUG)
    csvFile = pandas.read_csv(csv_file_name,usecols=["source","gcp_file","id","ignore","numeros","numeros_output"],skip_blank_lines=True)
    projection = osr.SpatialReference()
    projection.ImportFromProj4(projection_string)
 
    for _, row in csvFile.iterrows():
        gcp_file_name:str = row['gcp_file']
        file_name = row['source']
        if ".jpg.points" in gcp_file_name:
            output_raster_file = gcp_file_name.replace(".jpg.points",".tif")
        else:
            output_raster_file = gcp_file_name.replace(".png.points",".tif")
        id = row['id']
        if not exists(gcp_file_name) or ("ignore" in row and row["ignore"] == 1):
            logging.warning(f"  Skipping file: {gcp_file_name}")
        else: 
            logging.debug(f"  Georeferecing file: {file_name} with {gcp_file_name} and id {id} to {output_raster_file}")
            georef(file_name, gcp_file_name, output_raster_file, projection, "tps" if tps else "poly2", None)
            numeros = row['numeros']
            print(numeros)
            if numeros and pandas.notna(numeros) and exists(numeros):
                output_vector_file = row['numeros_output']
                logging.warning(f"  Handling file: {output_vector_file}")
                with tempfile.TemporaryDirectory() as tmpdirname:
                    with zipfile.ZipFile(numeros, 'r') as zip_ref:
                        zip_ref.extractall(tmpdirname)
                        shp_filename = os.path.basename(numeros).split('/')[-1].replace(".zip",".shp")
                        input_vector_file = tmpdirname + "/" + shp_filename
                        georef_vector(input_vector_file,gcp_file_name,output_vector_file,projection_string, "tps" if tps else "poly2")
            else:
                logging.warning(f"  Skipping file: {numeros}")

if __name__ == '__main__':
    csv_file = sys.argv[1]
    proj4_string = sys.argv[2]
    tps = False
    if len( sys.argv ) > 3 and sys.argv[3] == "tps":
        logging.info("using TPS")
        tps = True
    georef_csv(csv_file_name=csv_file,projection_string=proj4_string,tps=tps)
