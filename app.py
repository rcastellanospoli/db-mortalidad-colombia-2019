"""Dashboard de mortalidad no fetal en Colombia, año 2019."""
from dash import Dash, html, dcc, Input, Output, callback
from modelo import TODOS, ORDEN_EDAD, ORDEN_SEXO, cargar, departamentos_disponibles
from graficos import obtener_geojson, preparar_dashboard

TABLAS = cargar()
GEOJSON = obtener_geojson()

app = Dash(__name__, title='Mortalidad Colombia 2019 | DANE', update_title=None)
server = app.server

config = {'displaylogo': False, 'responsive':True,
          'toImageButtonOptions': {'format':'png', 'filename':'mortalidad_colombia_2019',
                                   'height':700, 'width':1200, 'scale':2}}


def cuadro(titulo, grafico_id, clase='visual'):
    return html.Section([
        html.Div(titulo, className='seccion-mini'),
        dcc.Loading(dcc.Graph(id=grafico_id, config=config, style={'width':'100%'}),type='dot'),
    ], className=clase)


def filtro_rotulo(titulo, elemento_id, opciones, valor=TODOS):
    return html.Div([
        html.Label(titulo, htmlFor=elemento_id),
        dcc.Dropdown(id=elemento_id, options=[{'label':'Todos','value':TODOS}] + opciones,
                     value=valor,clearable=False, searchable=True),
    ],className='filtro')


def kpi(etiqueta, identificador, detalle):
    return html.Div([
        html.Div(etiqueta,className='kpi-titulo'),
        html.Div(id=identificador,className='kpi-numero'),
        html.Div(detalle,className='kpi-detalle')
    ],className='kpi')

app.layout = html.Div([
    html.Header([
        html.Div('Actividad 4 - Aplicaciones I GR2 - Presentado por: Rodrigo Castellanos Caro',className='sello'),
        html.H1('Colombia 2019: Radiografía de la Mortalidad'),
        html.P('Una perspectiva interactiva de la mortalidad colombiana a través de los datos.')
    ],className='cabecera'),
    html.Main([
        html.Section([
            html.Div([
                html.H2('Explorar datos'),
                html.P('Los filtros afectan los siete componentes y sus totales.',className='texto-secundario')
            ],className='filtro-titulo'),
            filtro_rotulo('Departamento','filtro-departamento',departamentos_disponibles(TABLAS)),
            filtro_rotulo('Sexo','filtro-sexo',[
                {'label':s,'value':s} for s in ORDEN_SEXO if s in set(TABLAS['mensual']['SEXO'])]),
            filtro_rotulo('Grupo de edad','filtro-edad',[
                {'label':s,'value':s} for s in ORDEN_EDAD]),
            html.Button('Restablecer filtros',id='reiniciar',className='btn-reiniciar',n_clicks=0),
        ],className='panel-filtros'),

        html.Section([
            html.Div([
                kpi('Defunciones','kpi-defunciones','Registros seleccionados'),
                kpi('Código X95','kpi-x95','Subconjunto CIE-10'),
                kpi('Departamentos','kpi-departamentos','Con defunciones seleccionadas'),
                kpi('Meses','kpi-meses','Con registros en 2019'),
            ],className='indicadores'),
            html.P(id='texto-resumen',className='texto-resumen'),
            html.Div([
                cuadro('01 · Distribución territorial','grafico-mapa','visual visual-mapa'),
                cuadro('02 · Evolución temporal','grafico-lineas'),
            ],className='rejilla'),
            html.Div([
                cuadro('03 · Causas externas X95','grafico-x95'),
                cuadro('04 · Menor mortalidad municipal','grafico-circular'),
            ],className='rejilla'),
            html.Div(id='aviso-tasa',className='aviso-metodo'),
            cuadro('05 · Causas específicas de defunción','grafico-causas','visual visual-ancha'),
            cuadro('06 · Composición departamental por sexo','grafico-sexo','visual visual-ancha'),
            cuadro('07 · Distribución de edad','grafico-edad','visual visual-ancha'),
            html.Footer([
                html.P('Fuente: DANE, Estadísticas Vitales 2019 (defunciones no fetales). Valores absolutos; no tasas.'),
                html.A('Ficha oficial de la operación estadística',
                       href='https://microdatos.dane.gov.co/index.php/catalog/696/study-description',
                       target='_blank', rel='noopener noreferrer'),
                html.P('Mapas: polígonos departamentales derivados de la cartografía MGN DANE; crédito de repositorio mapas-colombia.'),
                html.P('Metodología: COD_DANE representa el territorio consignado en la base. '
                       'X95 es una categoría CIE-10 específica y no comprende todos los homicidios.'),
            ],className='pie-pagina'),
        ],className='contenido'),
    ],className='pagina')
])


@callback(
    Output('filtro-departamento','value'),
    Output('filtro-sexo','value'),
    Output('filtro-edad','value'),
    Input('reiniciar','n_clicks'),prevent_initial_call=True,
)
def reiniciar_filtros(_):
    return TODOS, TODOS, TODOS


@callback(
    Output('grafico-mapa','figure'),
    Output('grafico-lineas','figure'),
    Output('grafico-x95','figure'),
    Output('grafico-circular','figure'),
    Output('grafico-causas','figure'),
    Output('grafico-sexo','figure'),
    Output('grafico-edad','figure'),
    Output('kpi-defunciones','children'),
    Output('kpi-x95','children'),
    Output('kpi-departamentos','children'),
    Output('kpi-meses','children'),
    Output('texto-resumen','children'),
    Output('aviso-tasa','children'),
    Input('filtro-departamento','value'),
    Input('filtro-sexo','value'),
    Input('filtro-edad','value'),
)
def actualizar(departamento,sexo,edad):
    resultado = preparar_dashboard(TABLAS,departamento,sexo,edad,GEOJSON)
    kpi = resultado['indicadores']
    nombres = {opcion['value']:opcion['label'].split(' · ')[0] for opcion in departamentos_disponibles(TABLAS)}
    contexto = ' · '.join([
        f'Departamento: {nombres.get(departamento,"Todos") if departamento!=TODOS else "Todos"}',
        f'Sexo: {sexo if sexo!=TODOS else "Todos"}',
        f'Edad: {edad if edad!=TODOS else "Todas"}',
    ])
    mapa_extra = (' No fue posible cargar el GeoJSON; se muestra una gráfica territorial de respaldo.'
                  if GEOJSON is None else '')
    return (
        resultado['mapa'],resultado['lineas'],resultado['x95'],resultado['circular'],
        resultado['causas'],resultado['sexo'],resultado['edad'],
        f"{kpi['defunciones']:,}",f"{kpi['x95']:,}",str(kpi['departamentos']),str(kpi['meses']),
        contexto + mapa_extra,resultado['aviso_tasa'],
    )


if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8050)),debug=False)
