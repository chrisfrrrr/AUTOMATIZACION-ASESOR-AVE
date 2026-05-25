from __future__ import annotations
import os
from datetime import datetime, date, timezone
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

from core.canvas_client import CanvasClient, CanvasAPIError
from core.analytics import normalize_enrollments, normalize_assignments, normalize_submissions, build_student_summary
from core.reports import excel_bytes, pdf_bytes, DEV
from core.storage import save_snapshot, load_history

load_dotenv()
st.set_page_config(page_title='AVE Canvas Analytics', page_icon='assets/app_icon.ico', layout='wide')

LOGO_AVE = 'assets/logo_ave.png'
LOGO_UVG = 'assets/logo_uvg.png'

RISK_ORDER = ['Bajo','Medio','Alto']

st.markdown('''
<style>
.block-container {padding-top: 1.2rem;}
.metric-card {border:1px solid #e5e7eb;border-radius:16px;padding:14px;background:#fff;box-shadow:0 1px 8px rgba(0,0,0,.04)}
.small-muted {font-size:0.85rem;color:#6b7280;}
</style>
''', unsafe_allow_html=True)

if 'client' not in st.session_state: st.session_state.client = None
if 'courses' not in st.session_state: st.session_state.courses = []
if 'analysis' not in st.session_state: st.session_state.analysis = None

with st.sidebar:
    cols = st.columns(2)
    if Path(LOGO_AVE).exists(): cols[0].image(LOGO_AVE, use_container_width=True)
    if Path(LOGO_UVG).exists(): cols[1].image(LOGO_UVG, use_container_width=True)
    st.title('Configuración Canvas')
    st.caption('Herramienta de análisis académico - AVE')
    canvas_url = st.text_input('URL Canvas', value=os.getenv('CANVAS_URL', 'https://uvg.instructure.com'))
    token = st.text_input('Token de acceso', value=os.getenv('CANVAS_TOKEN', ''), type='password')
    generated_by = st.text_input('Nombre de quien genera el informe', value='')
    st.divider()
    daily_hours = st.number_input('Meta mínima diaria de conexión (horas)', min_value=0.5, max_value=12.0, value=2.0, step=0.5)
    course_start = st.date_input('Fecha de inicio del curso', value=date.today())
    only_business = st.checkbox('Calcular meta solo con días hábiles', value=False)
    analysis_date = st.date_input('Fecha de corte del análisis', value=date.today())
    st.divider()
    if st.button('Probar conexión / cargar cursos', use_container_width=True):
        try:
            c = CanvasClient(canvas_url, token)
            me = c.whoami()
            courses = c.courses()
            st.session_state.client = c
            st.session_state.courses = courses
            st.success(f'Conexión correcta: {me.get("name", "usuario Canvas")}')
        except Exception as e:
            st.error(f'No se pudo conectar: {e}')
    st.caption(f'Desarrollador: {DEV}')

st.title('Herramienta profesional de seguimiento académico AVE')
st.markdown('**Automatización de riesgo de desconexión, cumplimiento de horas, avance de actividades y reportes ejecutivos desde Canvas.**')

if not st.session_state.client:
    st.info('Ingrese la URL de Canvas y el token en la barra lateral. Luego presione “Probar conexión / cargar cursos”.')
    st.stop()

client: CanvasClient = st.session_state.client
courses = st.session_state.courses or []
if not courses:
    st.warning('No se encontraron cursos activos con este token.')
    st.stop()

course_options = {f"{c.get('name','Sin nombre')} | ID {c.get('id')}": c for c in courses}
selected_course_label = st.selectbox('Seleccione curso', list(course_options.keys()))
course = course_options[selected_course_label]
course_id = course.get('id')
course_name = course.get('name','Curso')

try:
    sections = client.sections(course_id)
except Exception:
    sections = []
section_options = {'Todas las secciones': None}
for s in sections:
    section_options[f"{s.get('name','Sección')} | ID {s.get('id')}"] = s
selected_section_label = st.selectbox('Seleccione sección', list(section_options.keys()))
section = section_options[selected_section_label]
section_id = section.get('id') if section else None
section_name = section.get('name') if section else 'Todas las secciones'

colA, colB, colC = st.columns([1,1,2])
with colA:
    generate = st.button('Generar análisis completo', type='primary', use_container_width=True)
with colB:
    clear = st.button('Limpiar resultados', use_container_width=True)
if clear:
    st.session_state.analysis = None
    st.rerun()

if generate:
    progress = st.progress(0, text='Conectando con Canvas...')
    try:
        analysis_dt = datetime.combine(analysis_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        progress.progress(15, text='Extrayendo estudiantes e inscripciones...')
        enrollments = client.enrollments(course_id, section_id)
        enroll_df = normalize_enrollments(enrollments, analysis_dt, course_start, daily_hours, only_business)
        valid_ids = set(enroll_df['user_id'].dropna().astype(int).tolist()) if not enroll_df.empty else set()
        progress.progress(35, text='Extrayendo actividades...')
        assignments = client.assignments(course_id)
        assign_df = normalize_assignments(assignments)
        progress.progress(55, text='Extrayendo entregas de estudiantes...')
        submissions = client.submissions(course_id)
        sub_df = normalize_submissions(submissions)
        if section_id and valid_ids and not sub_df.empty:
            sub_df = sub_df[sub_df['user_id'].isin(valid_ids)]
        progress.progress(75, text='Calculando indicadores de riesgo...')
        summary = build_student_summary(enroll_df, sub_df, analysis_dt)
        created_at = datetime.now().isoformat(timespec='seconds')
        save_snapshot(summary, course_id, course_name, section_id, section_name, created_at)
        hist = load_history(course_id)
        st.session_state.analysis = {
            'summary': summary,
            'submissions': sub_df,
            'assignments': assign_df,
            'history': hist,
            'course_name': course_name,
            'course_id': course_id,
            'section_name': section_name,
            'section_id': section_id,
            'analysis_date': str(analysis_date),
            'generated_by': generated_by,
        }
        progress.progress(100, text='Análisis finalizado')
        st.success('Análisis generado correctamente.')
    except CanvasAPIError as e:
        st.error(f'Canvas devolvió un error: {e}')
    except Exception as e:
        st.error(f'Ocurrió un error durante el análisis: {e}')

analysis = st.session_state.analysis
if not analysis:
    st.stop()

summary = analysis['summary']
sub_df = analysis['submissions']
hist = analysis['history']

st.subheader('Resumen ejecutivo')
if summary.empty:
    st.warning('No hay estudiantes para analizar.')
    st.stop()

risk_counts = summary['riesgo_integral'].value_counts().to_dict()
cols = st.columns(6)
cols[0].metric('Estudiantes', len(summary))
cols[1].metric('Riesgo bajo', risk_counts.get('Bajo', 0))
cols[2].metric('Riesgo medio', risk_counts.get('Medio', 0))
cols[3].metric('Riesgo alto', risk_counts.get('Alto', 0))
cols[4].metric('Avance promedio', f"{summary['porcentaje_avance'].mean():.1f}%")
cols[5].metric('Horas prom.', f"{summary['tiempo_total_horas'].mean():.1f}")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(['Dashboard', 'Estudiantes', 'Entregas', 'Historial', 'Mensajes'])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.histogram(summary, x='riesgo_integral', category_orders={'riesgo_integral': RISK_ORDER}, title='Distribución de riesgo integral')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(summary, x='horas_sin_actividad', y='porcentaje_avance', size='puntaje_riesgo', hover_name='nombre', color='riesgo_integral', title='Riesgo vs avance académico')
        st.plotly_chart(fig, use_container_width=True)
    c3, c4 = st.columns(2)
    with c3:
        fig = px.bar(summary.sort_values('puntaje_riesgo', ascending=False).head(20), x='puntaje_riesgo', y='nombre', orientation='h', title='Top 20 estudiantes prioritarios')
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        fig = px.histogram(summary, x='cumplimiento_horas', title='Cumplimiento de meta mínima de horas')
        st.plotly_chart(fig, use_container_width=True)
    st.info('El riesgo integral combina desconexión, déficit de horas, entregas pendientes, entregas atrasadas y avance académico. La prioridad de atención se ordena de mayor a menor puntaje.')

with tab2:
    risk_filter = st.multiselect('Filtrar riesgo integral', RISK_ORDER, default=RISK_ORDER)
    filtered = summary[summary['riesgo_integral'].isin(risk_filter)]
    st.dataframe(filtered, use_container_width=True, hide_index=True)

with tab3:
    st.dataframe(sub_df, use_container_width=True, hide_index=True)

with tab4:
    st.dataframe(hist, use_container_width=True, hide_index=True)
    if not hist.empty:
        hist2 = hist.copy()
        hist2['created_at'] = pd.to_datetime(hist2['created_at'], errors='coerce')
        trend = hist2.groupby([hist2['created_at'].dt.date, 'riesgo_integral']).size().reset_index(name='cantidad')
        fig = px.line(trend, x='created_at', y='cantidad', color='riesgo_integral', markers=True, title='Evolución histórica del riesgo')
        st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.markdown('### Mensaje para riesgo alto')
    st.code('Hola {nombre}, espero que estés bien. Identifiqué que tienes más de 72 horas sin actividad reciente o varios pendientes en Canvas. Te recomiendo ingresar hoy, revisar los módulos activos y priorizar las entregas vencidas o próximas. Estoy pendiente para apoyarte si tienes alguna dificultad.', language='text')
    st.markdown('### Mensaje para riesgo medio')
    st.code('Hola {nombre}, noté que tu actividad reciente o avance del curso requiere atención. Te recomiendo ingresar hoy a Canvas y avanzar con las actividades pendientes para mantenerte al día. Cualquier duda, estoy pendiente para apoyarte.', language='text')

    st.markdown('### Estudiantes para contactar')
    st.info('Este apartado muestra estudiantes con riesgo integral Medio o Alto. Puedes ver todos los casos o limitar la lista a los casos más prioritarios del día.')

    high_all = summary[summary['riesgo_integral'] == 'Alto'].copy()
    medium_all = summary[summary['riesgo_integral'] == 'Medio'].copy()
    contact_all = summary[summary['riesgo_integral'].isin(['Alto', 'Medio'])].copy()
    contact_all = contact_all.sort_values(['puntaje_riesgo', 'horas_sin_actividad', 'pendientes', 'atrasadas'], ascending=[False, False, False, False])

    c1, c2, c3 = st.columns(3)
    c1.metric('Total riesgo alto', len(high_all))
    c2.metric('Total riesgo medio', len(medium_all))
    c3.metric('Total a contactar', len(contact_all))

    modo_contacto = st.radio(
        'Modo de visualización',
        ['Mostrar todos los estudiantes en riesgo medio y alto', 'Mostrar solo prioritarios del día'],
        horizontal=True
    )

    if modo_contacto == 'Mostrar solo prioritarios del día':
        limite_contacto = st.slider('Cantidad máxima de estudiantes sugeridos', min_value=5, max_value=100, value=20, step=5)
        contact_view = contact_all.head(limite_contacto)
    else:
        contact_view = contact_all

    columnas_contacto = [
        'nombre', 'correo', 'riesgo_integral', 'puntaje_riesgo',
        'horas_sin_actividad', 'pendientes', 'atrasadas',
        'porcentaje_avance', 'cumplimiento_horas', 'accion_recomendada'
    ]
    columnas_contacto = [c for c in columnas_contacto if c in contact_view.columns]

    st.dataframe(contact_view[columnas_contacto], use_container_width=True, hide_index=True)

    csv_contactos = contact_view[columnas_contacto].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        'Descargar listado de contactos CSV',
        csv_contactos,
        file_name=f'contactos_prioritarios_{course_id}.csv',
        mime='text/csv',
        use_container_width=True
    )

st.divider()
st.subheader('Exportables')
col1, col2 = st.columns(2)
with col1:
    xlsx = excel_bytes(summary, sub_df, hist)
    st.download_button('Descargar Excel completo', xlsx, file_name=f'reporte_canvas_ave_{course_id}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
with col2:
    pdf = pdf_bytes(summary, course_name, section_name, generated_by, str(analysis_date))
    st.download_button('Descargar PDF ejecutivo', pdf, file_name=f'informe_ejecutivo_ave_{course_id}.pdf', mime='application/pdf', use_container_width=True)

st.caption(f'Desarrollador: {DEV} | Universidad del Valle de Guatemala - AVE')
