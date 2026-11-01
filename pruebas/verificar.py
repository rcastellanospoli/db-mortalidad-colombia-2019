"""Pruebas"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from modelo import cargar, TODOS
from graficos import preparar_dashboard, grafico_mapa
import plotly.graph_objects as go

tablas = cargar()
a = tablas['auditoria']
assert a['total_registros']==244355, 'No coincide el total de registros esperado'
assert a['casos_prefijo_X95']==9273, 'No coincide el total de casos X95'
assert a['n_departamentos']==33, 'No coincide el número de departamentos'

casos = [
    ((TODOS,TODOS,TODOS),244355,9273),
    (('11',TODOS,TODOS),38760,601),
    (('05','Masculino','Adultez temprana'),1788,538),
]
for filtros,total,x95 in casos:
    p = preparar_dashboard(tablas,*filtros,geo=None)
    assert p['indicadores']['defunciones']==total, filtros
    assert p['indicadores']['x95']==x95, filtros
    for clave in ['lineas','mapa','x95','circular','causas','sexo','edad']:
        assert isinstance(p[clave], go.Figure), (filtros,clave)
    print('OK',filtros,'defunciones=',total,'X95=',x95)


p = preparar_dashboard(tablas,'91','Indeterminado','Niñez',geo=None)
assert p['indicadores']['defunciones']==0
print('OK sin datos -> gráficos vacíos informativos')

features=[]
for i,codigo in enumerate(sorted(set(tablas['mensual']['COD_DEPARTAMENTO']))):
    x=-80+i*0.18
    features.append({'type':'Feature','properties':{'divipola_dep':codigo},
                    'geometry':{'type':'Polygon','coordinates':[[[x,4],[x+0.09,4],
                                        [x+0.09,4.1],[x,4.1],[x,4]]]}})
geo={'type':'FeatureCollection','features':features}
catalogo=tablas['mensual'][['COD_DEPARTAMENTO','DEPARTAMENTO']].drop_duplicates()
m=grafico_mapa(tablas['mensual'],catalogo,geo)
assert isinstance(m,go.Figure) and m.data[0].type=='choropleth'
assert float(m.data[0].marker.line.width)==0.9
print('OK construcción Plotly coroplético y bordes negros')
print('PRUEBAS DE DATOS Y FIGURAS: CORRECTAS')
