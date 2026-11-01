"""Construcción de gráficos Plotly. """
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

from modelo import (DATOS, TODOS, ORDEN_EDAD, ORDEN_SEXO,
                    aplicar_filtros, cargar_poblacion)

# Identidad visual · Propuesta 03: Laboratorio de datos
PETROLEO_OSC = '#223A36'
PETROLEO = '#2F5D56'
PETROLEO_SUAVE = '#486A63'
OLIVA = '#7C8450'
ARCILLA = '#B9784A'
ARENA = '#D4C4A0'
ARENA_SUAVE = '#ECE2CC'
GRIS = '#6C7A74'
GRIS_SUAVE = '#CFC8BB'
FONDO = '#F4F1EA'
SUPERFICIE = '#FBFAF6'

PALETA_MAPA = [
    [0.00, '#EFE1C2'],
    [0.22, '#D9C39A'],
    [0.45, '#BEA26D'],
    [0.68, '#7C8450'],
    [1.00, '#2F5D56'],
]

COLORES_PIE = ['#2F5D56', '#486A63', '#7C8450', '#A08E68', '#B9784A',
               '#D4C4A0', '#6C7A74', '#9DAB92', '#C59C7A', '#CAB8A0']

COLORES_SEXO = {
    'Masculino': '#2F5D56',
    'Femenino': '#B9784A',
    'Indeterminado': '#7C8450',
    'No informado': '#7D8580',
}

GEOJSON_URL = ('https://raw.githubusercontent.com/ytolosa/mapas-colombia/'
               'main/output/geojson/col_departamentos_real_nacional.geojson')


def tema(fig, altura=390, margenes=None):
    fig.update_layout(
        template='plotly_white',
        height=altura,
        font=dict(family='IBM Plex Sans, Arial, sans-serif', color=PETROLEO_OSC, size=12),
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        margin=margenes or dict(l=35, r=20, t=54, b=45),
        title=dict(font=dict(size=16, color=PETROLEO_OSC), x=0.02),
        hoverlabel=dict(bgcolor='#FFFFFF', font_size=12,
                        font_family='IBM Plex Sans, Arial, sans-serif',
                        bordercolor=GRIS_SUAVE),
        legend=dict(bgcolor='rgba(0,0,0,0)', title=None,
                    font=dict(size=11, color=PETROLEO_OSC)),
    )
    return fig


def vacio(titulo, mensaje='No hay datos para los filtros elegidos.'):
    fig = go.Figure()
    fig.add_annotation(
        text=mensaje,
        showarrow=False,
        font=dict(size=14, color=GRIS),
        x=0.5, y=0.5,
        xref='paper', yref='paper'
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(title=titulo)
    return tema(fig)


def obtener_geojson():
    ruta = DATOS / 'departamentos.geojson'
    try:
        if ruta.exists():
            geo = json.loads(ruta.read_text(encoding='utf-8'))
        else:
            respuesta = requests.get(GEOJSON_URL, timeout=20)
            respuesta.raise_for_status()
            geo = respuesta.json()
        features = geo.get('features', [])
        codigos = [str(f.get('properties', {}).get('divipola_dep', '')).zfill(2) for f in features]
        if len(features) != 33 or len(set(codigos)) != 33:
            raise ValueError('El GeoJSON no contiene 33 departamentos únicos')
        for f in features:
            if f.get('geometry', {}).get('type') not in ('Polygon', 'MultiPolygon'):
                raise ValueError('Geometría departamental inválida')
        if not ruta.exists():
            try:
                ruta.write_text(json.dumps(geo, ensure_ascii=False), encoding='utf-8')
            except OSError:
                pass
        return geo
    except (requests.RequestException, ValueError, OSError, KeyError) as error:
        print('Aviso: mapa geográfico no disponible:', error)
        return None


def grafico_mensual(tabla):
    ser = tabla.groupby('MES', as_index=False)['TOTAL'].sum()
    ser = pd.DataFrame({'MES': range(1, 13)}).merge(ser, on='MES', how='left').fillna({'TOTAL': 0})
    ser['MES_NOMBRE'] = ser['MES'].map(dict(enumerate(
        ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'], 1)))
    fig = px.line(
        ser, x='MES_NOMBRE', y='TOTAL', markers=True,
        title='Evolución mensual de defunciones',
        labels={'TOTAL': 'Defunciones', 'MES_NOMBRE': 'Mes'}
    )
    fig.update_traces(
        line_color=PETROLEO, line_width=3,
        marker=dict(size=7, color=ARCILLA, line=dict(color=PETROLEO_OSC, width=0.8)),
        hovertemplate='%{x}<br>Defunciones: %{y:,.0f}<extra></extra>'
    )
    fig.update_yaxes(rangemode='tozero', tickformat=',', gridcolor='#E8E1D5')
    fig.update_xaxes(showgrid=False)
    return tema(fig)


def grafico_mapa(tabla, catalogo, geo=None):
    d = tabla.groupby('COD_DEPARTAMENTO', as_index=False)['TOTAL'].sum()
    base = catalogo.merge(d, on='COD_DEPARTAMENTO', how='left').fillna({'TOTAL': 0})
    if geo is None:
        fig = px.bar(
            base.sort_values('TOTAL'), y='DEPARTAMENTO', x='TOTAL', orientation='h',
            title='Mapa no disponible: comparación por departamento',
            labels={'DEPARTAMENTO': '', 'TOTAL': 'Defunciones'},
            color_discrete_sequence=[PETROLEO]
        )
        fig.update_traces(marker_line_color=PETROLEO_OSC, marker_line_width=0.7)
        fig.update_layout(height=620, yaxis=dict(tickfont=dict(size=9)))
        fig.update_xaxes(gridcolor='#E8E1D5', tickformat=',')
        return tema(fig, altura=620)
    fig = px.choropleth(
        base,
        geojson=geo,
        locations='COD_DEPARTAMENTO',
        featureidkey='properties.divipola_dep',
        color='TOTAL',
        custom_data=['DEPARTAMENTO'],
        color_continuous_scale=PALETA_MAPA,
        range_color=(0, max(1, int(base['TOTAL'].max()))),
        title='Defunciones no fetales por departamento · 2019',
        labels={'TOTAL': 'Defunciones'},
        projection='mercator'
    )
    fig.update_traces(
        marker_line_color='#141414',
        marker_line_width=0.9,
        hovertemplate='<b>%{customdata[0]}</b><br>Defunciones: %{z:,.0f}<extra></extra>'
    )
    fig.update_geos(
        visible=False,
        showland=True,
        landcolor='#E7E1D6',
        showcountries=False,
        showcoastlines=False,
        lonaxis_range=[-82.5, -66.0],
        lataxis_range=[-5.2, 14.2],
        bgcolor='#F0ECE4'
    )
    fig.update_layout(
        coloraxis_colorbar=dict(
            title='Defunciones',
            thickness=16,
            len=0.78,
            tickformat=',',
            outlinewidth=0,
        )
    )
    return tema(fig, altura=590, margenes=dict(l=0, r=0, t=55, b=0))


def grafico_x95(tabla):
    if tabla.empty:
        return vacio('Cinco municipios con más casos X95')
    d = tabla.groupby(['COD_DANE', 'MUNICIPIO', 'DEPARTAMENTO'], as_index=False)['TOTAL'].sum()
    top = d.nlargest(5, 'TOTAL').sort_values('TOTAL')
    top['MUNICIPIO_LABEL'] = top['MUNICIPIO'] + ' · ' + top['DEPARTAMENTO']
    maximo = float(top['TOTAL'].max()) if not top.empty else 0
    limite = max(maximo * 1.20, maximo + 60)
    fig = px.bar(
        top,
        x='TOTAL', y='MUNICIPIO_LABEL', orientation='h',
        title='Cinco municipios con más defunciones X95',
        labels={'TOTAL': 'Defunciones con código X95', 'MUNICIPIO_LABEL': ''},
        text='TOTAL',
        color_discrete_sequence=[ARCILLA]
    )
    fig.update_traces(
        marker_line_color=PETROLEO_OSC,
        marker_line_width=0.6,
        texttemplate='%{x:,.0f}',
        textposition='outside',
        cliponaxis=False,
        hovertemplate='%{y}<br>Casos X95: %{x:,.0f}<extra></extra>'
    )
    fig.update_xaxes(
        range=[0, limite],
        rangemode='tozero',
        tickformat=',',
        gridcolor='#E8E1D5',
        automargin=True
    )
    fig.update_yaxes(automargin=True)
    return tema(fig, altura=400, margenes=dict(l=25, r=95, t=54, b=45))


def grafico_menores(tabla, sexo=TODOS, edad=TODOS, poblacion=None):
    if tabla.empty:
        return vacio('Municipios con menor mortalidad'), 'No hay registros para los filtros seleccionados.'
    d = tabla.groupby(['COD_DANE', 'MUNICIPIO', 'DEPARTAMENTO'], as_index=False)['TOTAL'].sum()
    d = d[d['TOTAL'] > 0]
    tasas_validas = poblacion is not None and sexo == TODOS and edad == TODOS
    sin_poblacion = 0
    if tasas_validas:
        sin_poblacion = len(set(d['COD_DANE']) - set(poblacion['COD_DANE']))
        if sin_poblacion:
            tasas_validas = False
    if tasas_validas:
        d = d.merge(poblacion, on='COD_DANE', how='inner', validate='one_to_one')
        d = d[d['POBLACION_2019'] > 0]
        d['TASA_100K'] = d['TOTAL'] / d['POBLACION_2019'] * 100_000
        d = d.nsmallest(10, 'TASA_100K').copy()
        titulo = 'Diez municipios con menor tasa bruta (sectores: número de defunciones)'
        aviso = ('La selección se realiza con tasas por 100.000 habitantes. Los sectores representan defunciones, '
                 'porque las tasas no son magnitudes sumables. Verificar compatibilidad del criterio territorial.')
    else:
        d = d.nsmallest(10, 'TOTAL').copy()
        titulo = 'Diez municipios con menor recuento · provisional'
        aviso = ('Sobre la gráfica «Municipios con menor mortalidad»: '
    'esta visualización presenta los diez municipios con menor número '
    'de defunciones registradas durante 2019, sin incluir aquellos '
    'que no tienen registros. Los resultados corresponden a cantidades '
    'absolutas, no a tasas de mortalidad. Por tanto, no permiten concluir '
    'que estos municipios tengan un menor riesgo de mortalidad, '
    'ya que para ello es necesario considerar también su población.')
        if sin_poblacion:
            aviso += f' Se omitió el cálculo de tasas porque faltan {sin_poblacion} municipios en la población.'
    if d.empty:
        return vacio(titulo), aviso
    d['ETIQUETA'] = d['MUNICIPIO'] + ' · ' + d['DEPARTAMENTO']
    if tasas_validas:
        fig = px.pie(
            d, names='ETIQUETA', values='TOTAL', custom_data=['TASA_100K'],
            title=titulo, color_discrete_sequence=COLORES_PIE
        )
        fig.update_traces(
            textinfo='percent',
            hovertemplate='<b>%{label}</b><br>Defunciones: %{value:,.0f}<br>Tasa por 100 mil: %{customdata[0]:.2f}<extra></extra>'
        )
    else:
        fig = px.pie(
            d, names='ETIQUETA', values='TOTAL', title=titulo,
            color_discrete_sequence=COLORES_PIE
        )
        fig.update_traces(
            textinfo='percent',
            hovertemplate='<b>%{label}</b><br>Defunciones: %{value:,.0f}<extra></extra>'
        )
    fig.update_layout(legend=dict(font=dict(size=9), orientation='v'))
    return tema(fig, altura=410, margenes=dict(l=10, r=10, t=57, b=8)), aviso


def grafico_causas(tabla):
    if tabla.empty:
        return vacio('Diez principales causas de muerte')
    d = tabla.groupby(['COD_MUERTE', 'DESCRIPCION_CAUSA'], as_index=False)['TOTAL'].sum().nlargest(10, 'TOTAL')
    d = d.reset_index(drop=True)
    fig = go.Figure(data=[go.Table(
        columnwidth=[40, 90, 430, 100],
        header=dict(
            values=['N.º', 'Código CIE-10', 'Causa de muerte', 'Defunciones'],
            fill_color=PETROLEO_OSC,
            font=dict(color='white', size=12, family='IBM Plex Sans, Arial, sans-serif'),
            align=['center', 'left', 'left', 'right'],
            height=34
        ),
        cells=dict(
            values=[list(range(1, len(d) + 1)), d['COD_MUERTE'], d['DESCRIPCION_CAUSA'],
                    d['TOTAL'].map(lambda n: f'{n:,}')],
            fill_color=[[ARENA_SUAVE, '#FFFFFF'] * 6],
            font=dict(color=PETROLEO_OSC, size=11, family='IBM Plex Sans, Arial, sans-serif'),
            align=['center', 'left', 'left', 'right'],
            height=32,
        ),
    )])
    fig.update_layout(title='Diez principales causas específicas de muerte')
    return tema(fig, altura=440, margenes=dict(l=12, r=12, t=55, b=8))


def grafico_sexo(tabla):
    if tabla.empty:
        return vacio('Defunciones por departamento y sexo')
    d = tabla.groupby(['DEPARTAMENTO', 'SEXO'], as_index=False)['TOTAL'].sum()
    orden = d.groupby('DEPARTAMENTO')['TOTAL'].sum().sort_values(ascending=False).index.tolist()
    fig = px.bar(
        d, x='DEPARTAMENTO', y='TOTAL', color='SEXO',
        title='Defunciones por departamento y sexo', barmode='stack',
        category_orders={'DEPARTAMENTO': orden, 'SEXO': ORDEN_SEXO},
        color_discrete_map=COLORES_SEXO,
        labels={'DEPARTAMENTO': 'Departamento', 'TOTAL': 'Defunciones', 'SEXO': 'Sexo'}
    )
    fig.update_xaxes(tickangle=-55, tickfont=dict(size=10), showgrid=False)
    fig.update_yaxes(tickformat=',', gridcolor='#E8E1D5')
    fig.update_traces(
        hovertemplate='%{x}<br>Defunciones: %{y:,.0f}<extra>%{fullData.name}</extra>'
    )
    return tema(fig, altura=480, margenes=dict(l=45, r=20, t=52, b=140))


def grafico_edad(tabla):
    if tabla.empty:
        return vacio('Distribución por grupo de edad')
    d = tabla.groupby('CATEGORIA_EDAD', as_index=False)['TOTAL'].sum()
    d['CATEGORIA_EDAD'] = pd.Categorical(d['CATEGORIA_EDAD'], categories=ORDEN_EDAD, ordered=True)
    d = d.sort_values('CATEGORIA_EDAD')
    fig = px.bar(
        d, x='CATEGORIA_EDAD', y='TOTAL', title='Distribución de defunciones por grupo de edad',
        labels={'CATEGORIA_EDAD': 'Grupo de edad DANE', 'TOTAL': 'Defunciones'},
        color_discrete_sequence=[OLIVA]
    )
    fig.update_xaxes(tickangle=-35, tickfont=dict(size=10), showgrid=False)
    fig.update_yaxes(gridcolor='#E8E1D5', tickformat=',')
    fig.update_traces(
        marker_line_color=PETROLEO_OSC,
        marker_line_width=0.4,
        hovertemplate='%{x}<br>Defunciones: %{y:,.0f}<extra></extra>'
    )
    return tema(fig, altura=410, margenes=dict(l=45, r=20, t=54, b=118))


def preparar_dashboard(tablas, departamento=TODOS, sexo=TODOS, edad=TODOS, geo=None):
    mensual = aplicar_filtros(tablas['mensual'], departamento, sexo, edad)
    causas = aplicar_filtros(tablas['causas'], departamento, sexo, edad)
    municipios = aplicar_filtros(tablas['municipios'], departamento, sexo, edad)
    x95 = aplicar_filtros(tablas['x95'], departamento, sexo, edad)
    total = int(mensual['TOTAL'].sum())
    total_causas = int(causas['TOTAL'].sum())
    total_mun = int(municipios['TOTAL'].sum())
    if total != total_causas or total != total_mun:
        raise AssertionError('Inconsistencia de cubos filtrados (mes/causa/municipio).')
    base_dep = tablas['mensual'][['COD_DEPARTAMENTO', 'DEPARTAMENTO']].drop_duplicates().sort_values('DEPARTAMENTO')
    pop = cargar_poblacion()
    pie, aviso = grafico_menores(municipios, sexo, edad, pop)
    meses_activos = int(mensual.loc[mensual.TOTAL > 0, 'MES'].nunique())
    return {
        'lineas': grafico_mensual(mensual),
        'mapa': grafico_mapa(mensual, base_dep, geo),
        'x95': grafico_x95(x95),
        'circular': pie,
        'causas': grafico_causas(causas),
        'sexo': grafico_sexo(mensual),
        'edad': grafico_edad(mensual),
        'indicadores': {
            'defunciones': total,
            'x95': int(x95['TOTAL'].sum()),
            'departamentos': int(mensual.COD_DEPARTAMENTO.nunique()),
            'meses': meses_activos,
        },
        'aviso_tasa': aviso,
    }
