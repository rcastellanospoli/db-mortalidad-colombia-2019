"""Prepara datos AGREGADOS de EEVV 2019 para Dash."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

RANGOS_EDAD = [
    ("Mortalidad neonatal", 0, 4),
    ("Mortalidad infantil", 5, 6),
    ("Primera infancia", 7, 8),
    ("Niñez", 9, 10),
    ("Adolescencia", 11, 11),
    ("Juventud", 12, 13),
    ("Adultez temprana", 14, 16),
    ("Adultez intermedia", 17, 19),
    ("Vejez", 20, 24),
    ("Longevidad / Centenarios", 25, 28),
    ("Edad desconocida", 29, 29),
]
MAPA_EDAD = {str(i): nombre for nombre, a, b in RANGOS_EDAD for i in range(a, b + 1)}
MAPA_SEXO = {"1":"Masculino","2":"Femenino","3":"Indeterminado"}


def codigo(serie: pd.Series, ancho: int | None = None) -> pd.Series:
    s = serie.astype('string').str.strip().str.replace(r'\.0$', '', regex=True)
    if ancho:
        s = s.str.zfill(ancho)
    return s


def cie(serie: pd.Series) -> pd.Series:
    return codigo(serie).str.upper().str.replace('.', '', regex=False)


def preparar(archivo_def: str | Path, archivo_causas: str | Path,
            archivo_div: str | Path, carpeta_salida: str | Path) -> dict:
    salida = Path(carpeta_salida)
    salida.mkdir(parents=True, exist_ok=True)

    datos = pd.read_excel(
        archivo_def, sheet_name=0, engine='openpyxl',
        usecols=['COD_DANE','COD_DEPARTAMENTO','AÑO','MES','SEXO','GRUPO_EDAD1','COD_MUERTE'],
        dtype={'COD_DANE':'string', 'COD_DEPARTAMENTO':'string',
               'SEXO':'string','GRUPO_EDAD1':'string','COD_MUERTE':'string'},
    )
    div = pd.read_excel(archivo_div, sheet_name=0, engine='openpyxl',
                        usecols=['COD_DANE','DEPARTAMENTO','MUNICIPIO'], dtype='string')
    causas = pd.read_excel(archivo_causas, sheet_name=0, header=8,
                           usecols='C:F', engine='openpyxl', dtype='string')
    causas.columns = ['CIE3','DESCRIPCION3','CIE4','DESCRIPCION4']
    datos['AÑO'] = pd.to_numeric(datos['AÑO'], errors='coerce')
    datos['MES'] = pd.to_numeric(datos['MES'], errors='coerce')
    if datos['AÑO'].isna().any() or not datos['AÑO'].eq(2019).all():
        raise ValueError('El Excel contiene filas de años distintos de 2019 o sin año.')
    if datos['MES'].isna().any() or not datos['MES'].between(1, 12).all():
        raise ValueError('Hay valores de MES fuera de 1-12.')
    datos['MES'] = datos['MES'].astype(int)
    datos['COD_DANE'] = codigo(datos['COD_DANE'], 5)
    datos['COD_DEPARTAMENTO'] = codigo(datos['COD_DEPARTAMENTO'], 2)
    datos['COD_MUERTE'] = cie(datos['COD_MUERTE'])
    datos['SEXO'] = codigo(datos['SEXO']).map(MAPA_SEXO).fillna('No informado')
    datos['CATEGORIA_EDAD'] = codigo(datos['GRUPO_EDAD1']).map(MAPA_EDAD)
    if datos['CATEGORIA_EDAD'].isna().any():
        raise ValueError('Existen valores de GRUPO_EDAD1 sin correspondencia.')

    div['COD_DANE'] = codigo(div['COD_DANE'], 5)
    div = div[['COD_DANE','DEPARTAMENTO','MUNICIPIO']].drop_duplicates(subset='COD_DANE')
    if not div['COD_DANE'].is_unique:
        raise ValueError('Hay códigos DIVIPOLA duplicados.')
    datos = datos.merge(div, on='COD_DANE', how='left', validate='many_to_one')
    if datos['DEPARTAMENTO'].isna().any():
        raise ValueError('Existen códigos municipales no encontrados en DIVIPOLA.')
    if not (datos['COD_DANE'].str[:2] == datos['COD_DEPARTAMENTO']).all():
        raise ValueError('La codificación departamental no coincide con los municipios.')

    causas['CIE3'] = cie(causas['CIE3'])
    causas['CIE4'] = cie(causas['CIE4'])
    for k in ['DESCRIPCION3','DESCRIPCION4']:
        causas[k] = causas[k].astype('string').str.strip()
    tabla4 = causas[['CIE4','DESCRIPCION4']].dropna().drop_duplicates('CIE4')
    tabla3 = causas[['CIE3','DESCRIPCION3']].dropna().drop_duplicates('CIE3')
    mapa4 = tabla4.set_index('CIE4')['DESCRIPCION4']
    mapa3 = tabla3.set_index('CIE3')['DESCRIPCION3']
    datos['DESCRIPCION_CAUSA'] = (datos['COD_MUERTE'].map(mapa4)
        .fillna(datos['COD_MUERTE'].map(mapa3))
        .fillna(datos['COD_MUERTE'].str[:3].map(mapa3)))
    if datos['DESCRIPCION_CAUSA'].isna().any():
        raise ValueError('Hay códigos CIE-10 sin descripción; revisar el catálogo.')

    dims = ['COD_DEPARTAMENTO', 'DEPARTAMENTO', 'SEXO', 'CATEGORIA_EDAD']
    def guardar(nombre: str, columnas: list[str], tabla: pd.DataFrame | None = None) -> tuple[int, int]:
        fuente = datos if tabla is None else tabla
        agg = (fuente.groupby(columnas, dropna=False, sort=False).size()
               .reset_index(name='TOTAL'))
        ruta = salida / nombre
        agg.to_csv(ruta, index=False, compression='gzip', encoding='utf-8')
        return len(agg), int(agg['TOTAL'].sum())

    archivos = {
        'mensual.csv.gz': guardar('mensual.csv.gz', dims + ['MES']),
        'causas.csv.gz': guardar('causas.csv.gz', dims + ['COD_MUERTE','DESCRIPCION_CAUSA']),
        'municipios.csv.gz': guardar('municipios.csv.gz', dims + ['COD_DANE','MUNICIPIO']),
        'x95.csv.gz': guardar('x95.csv.gz', dims + ['COD_DANE','MUNICIPIO'],
                            datos[datos['COD_MUERTE'].str.startswith('X95', na=False)]),
    }
    total = len(datos)
    assert all(valor[1] == total for key, valor in archivos.items() if key != 'x95.csv.gz')
    auditoria = {
        'fuente':'DANE - Estadísticas vitales, defunciones no fetales 2019',
        'url':'https://microdatos.dane.gov.co/index.php/catalog/696/study-description',
        'total_registros':total,
        'casos_prefijo_X95':archivos['x95.csv.gz'][1],
        'n_departamentos':int(datos['COD_DEPARTAMENTO'].nunique()),
        'n_municipios':int(datos['COD_DANE'].nunique()),
        'tablas':{k:{'filas':v[0], 'total':v[1]} for k,v in archivos.items()},
        'descripcion':'Tablas agregadas por variables para filtros. No incluyen microdatos fila a fila.',
        'advertencias':[
            'COD_DANE es el código geográfico registrado; verificar su alcance en diccionario oficial antes de interpretar residencia.',
            'X95 se trata como prefijo de causa CIE-10; no representa todos los homicidios.',
            'Para tasas se requiere denominador municipal de población 2019 compatible con la unidad territorial.'
        ]
    }
    (salida/'auditoria.json').write_text(json.dumps(auditoria,ensure_ascii=False,indent=2), encoding='utf-8')
    print(json.dumps(auditoria, ensure_ascii=False, indent=2))
    return auditoria


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--defunciones', required=True)
    parser.add_argument('--causas', required=True)
    parser.add_argument('--divipola', required=True)
    parser.add_argument('--salida', default='datos')
    args = parser.parse_args()
    preparar(args.defunciones, args.causas, args.divipola, args.salida)
