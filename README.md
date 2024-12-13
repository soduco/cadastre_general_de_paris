# Georeference the maps and the address points

```shell
python georef_batch.py cadastre_general_paris.csv "+proj=aeqd +lat_0=48.83635863 +lon_0=2.33652533 +x_0=0 +y_0=0 +ellps=GRS80 +to_meter=1.94903631 +no_defs +type=crs" tps
```

Note that the process (the csv actually) needs you to have:
- the georeferencing points in the directory *cadastre_general_paris* (for instance *cadastre_general_paris/1/FRAN_0265_00007_L.png.points*)
- the address points in the directory *cadastre_general_paris_numeros* (for instance *cadastre_general_paris_numeros/1/NUMEROS_QUARTIER_1_CORRIGES.zip*)
- the map images in the directory *FRAN_0265* (for instance *FRAN_0265/FRAN_0265_00007_L.png*)

The results are saved in directory *cadastre_general_paris_resultat* (for instance *cadastre_general_paris_resultat/1/NUMEROS_QUARTIER_1_CORRIGES_GEOREF.gpkg*)

You can merge all the files with:
```shell
ogrmerge.py -single -f GPKG -o cadastre_general_paris_addresses.gpkg cadastre_general_paris_resultat/*/*.gpkg
```


```shell
ogr2ogr \
  -sql "SELECT \
    geom, \
    CONCAT(\"NUMERO TXT\", ' ', NOM_SAISI) AS historical_name, \
    CONCAT(\"NUMERO TXT\", ' ', NOM_SAISI, ', Paris') AS normalised_name, \
    NULL AS specific_spatial_precision, \
    'cadastre_general_paris' AS historical_source, \
    'cadastre_general_paris' AS numerical_origin_process, \
    CONCAT(NOM_NOTE, ', Paris') AS associated_normalised_rough_name, \
    NUM_QUART AS quartier_numero, \
    NUMEROTATI AS numerotation, \
    INTERP AS interpretation \
    FROM merged WHERE \"EXP_GEO\" = 1" \
  -f "PostgreSQL" PG:"host='geohistoricaldata.org' user='postgres' dbname='soduco' password='GHDB_987_admin'" \
  cadastre_general_paris_addresses.gpkg \
  -lco SCHEMA=geocoder_workspace \
  -nln "cadastre_general_paris_1825_numbers_initial_import"
```

You can update the database to include the district names:
```sql
ALTER TABLE geocoder_workspace.cadastre_general_paris_1825_numbers_initial_import ADD COLUMN quartier text;

UPDATE geocoder_workspace.cadastre_general_paris_1825_numbers_initial_import AS A 
SET quartier = B."NOM_CADASTRE"
FROM public.quartiers_cadastre AS B 
WHERE A.quartier_numero = B."NUM_QUARTIER_CADASTRE";
```
