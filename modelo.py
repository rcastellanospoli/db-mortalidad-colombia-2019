"""Lectura de datos agregados y utilidades estadísticas compartidas."""
from functools import lru_cache
from pathlib import Path
import json
import pandas as pd

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / 'datos'
TODOS = '__TODOS__'
ORDEN_EDAD = [
    'Mortalidad neonatal','Mortalidad infantil','Primera infancia',
    'Niñez','Adolescencia','Juventud','Adultez temprana',
    'Adultez intermedia','Vejez','Longevidad / Centenarios','Edad desconocida'
]
ORDEN_SEXO = ['Masculino','Femenino','Indeterminado','No informado']

@lru_cache(maxsize=1)
def cargar() -> dict:
    tablas = {}
    for nombre in ['mensual','causas','municipios','x95']:
        ruta = DATOS / f'{nombre}.csv.gz'
        if not ruta.exists():
            raise FileNotFoundError(f'Falta {ruta.name}; ejecuta preparar_datos.py.')
        tablas[nombre] = pd.read_csv(
            ruta, compression='gzip',
            dtype={'COD_DEPARTAMENTO':'string','COD_DANE':'string',
                   'COD_MUERTE':'string','SEXO':'string','CATEGORIA_EDAD':'string'}
        )
        tablas[nombre]['COD_DEPARTAMENTO'] = tablas[nombre]['COD_DEPARTAMENTO'].str.zfill(2)
        if 'COD_DANE' in tablas[nombre]:
            tablas[nombre]['COD_DANE'] = tablas[nombre]['COD_DANE'].str.zfill(5)
        tablas[nombre]['TOTAL'] = pd.to_numeric(tablas[nombre]['TOTAL'],errors='raise').astype(int)
    tablas['auditoria'] = json.loads((DATOS/'auditoria.json').read_text(encoding='utf-8'))
    total = tablas['auditoria']['total_registros']
    assert all(tablas[nombre]['TOTAL'].sum()==total for nombre in ['mensual','causas','municipios'])
    assert int(tablas['x95']['TOTAL'].sum()) == tablas['auditoria']['casos_prefijo_X95']
    return tablas


def aplicar_filtros(tabla: pd.DataFrame, departamento=TODOS, sexo=TODOS, edad=TODOS) -> pd.DataFrame:
    mask = pd.Series(True, index=tabla.index)
    if departamento != TODOS:
        mask &= tabla['COD_DEPARTAMENTO'].eq(departamento)
    if sexo != TODOS:
        mask &= tabla['SEXO'].eq(sexo)
    if edad != TODOS:
        mask &= tabla['CATEGORIA_EDAD'].eq(edad)
    return tabla.loc[mask]


def departamentos_disponibles(tablas: dict) -> list[dict]:
    dep = tablas['mensual'][['COD_DEPARTAMENTO','DEPARTAMENTO']].drop_duplicates()
    dep = dep.sort_values('DEPARTAMENTO')
    return [{'label':f'{r.DEPARTAMENTO} · {r.COD_DEPARTAMENTO}', 'value':r.COD_DEPARTAMENTO}
            for r in dep.itertuples(index=False)]


def cargar_poblacion() -> pd.DataFrame | None:
    """Población municipal 2019 opcional; NO se inventan denominadores."""
    ruta = DATOS/'poblacion_municipal_2019.csv'
    if not ruta.exists():
        return None
    p = pd.read_csv(ruta, dtype={'COD_DANE':'string'})
    if not {'COD_DANE','POBLACION_2019'} <= set(p.columns):
        raise ValueError('poblacion_municipal_2019.csv requiere COD_DANE y POBLACION_2019')
    p['COD_DANE'] = p['COD_DANE'].str.strip().str.zfill(5)
    p['POBLACION_2019'] = pd.to_numeric(p['POBLACION_2019'], errors='coerce')
    p = p.dropna(subset=['COD_DANE','POBLACION_2019'])
    if p['COD_DANE'].duplicated().any() or (p['POBLACION_2019']<=0).any():
        raise ValueError('Poblaciones inválidas, no positivas o códigos duplicados.')
    return p[['COD_DANE','POBLACION_2019']]
