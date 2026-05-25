from __future__ import annotations
from io import BytesIO
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.units import inch
from pathlib import Path

DEV = 'Ing. Christian Pocol, Ingeniero Electrónico'

def excel_bytes(summary: pd.DataFrame, submissions: pd.DataFrame, history: pd.DataFrame | None = None) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine='openpyxl') as writer:
        summary.to_excel(writer, sheet_name='Resumen estudiantes', index=False)
        submissions.to_excel(writer, sheet_name='Entregas detalle', index=False)
        if history is not None and not history.empty:
            history.to_excel(writer, sheet_name='Historial', index=False)
    return bio.getvalue()

def _watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 42)
    canvas.setFillColor(colors.Color(0.85,0.85,0.85, alpha=0.25))
    canvas.translate(5.5*inch, 4.2*inch)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, 'AVE - UVG')
    canvas.restoreState()
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(0.4*inch, 0.3*inch, f'Desarrollador: {DEV}')
    canvas.drawRightString(10.6*inch, 0.3*inch, f'Página {doc.page}')
    canvas.restoreState()

def pdf_bytes(summary: pd.DataFrame, course_name: str, section_name: str, generated_by: str, analysis_date: str, logo_ave='assets/logo_ave.png', logo_uvg='assets/logo_uvg.png') -> bytes:
    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Small', fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='TitleAVE', fontSize=18, leading=22, alignment=1, textColor=colors.HexColor('#003865')))
    story = []
    header_data = []
    if Path(logo_ave).exists():
        header_data.append(Image(logo_ave, width=1.2*inch, height=0.55*inch))
    else: header_data.append('')
    header_data.append(Paragraph('Informe Ejecutivo de Seguimiento Académico AVE', styles['TitleAVE']))
    if Path(logo_uvg).exists():
        header_data.append(Image(logo_uvg, width=1.1*inch, height=0.55*inch))
    else: header_data.append('')
    ht = Table([header_data], colWidths=[1.4*inch, 7.2*inch, 1.4*inch])
    ht.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story += [ht, Spacer(1, 10)]
    story.append(Paragraph(f'<b>Curso:</b> {course_name}<br/><b>Sección:</b> {section_name}<br/><b>Fecha de análisis:</b> {analysis_date}<br/><b>Generado por:</b> {generated_by or "No especificado"}<br/><b>Desarrollador:</b> {DEV}', styles['Small']))
    story.append(Spacer(1, 12))
    total = len(summary)
    counts = summary['riesgo_integral'].value_counts().to_dict() if not summary.empty else {}
    kpi = [['Total estudiantes', 'Riesgo bajo', 'Riesgo medio', 'Riesgo alto', 'Prom. avance', 'Prom. horas'],
           [total, counts.get('Bajo',0), counts.get('Medio',0), counts.get('Alto',0), f"{summary['porcentaje_avance'].mean():.1f}%" if total else '0%', f"{summary['tiempo_total_horas'].mean():.1f}" if total else '0']]
    kt = Table(kpi, colWidths=[1.5*inch]*6)
    kt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#003865')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.25,colors.grey),('ALIGN',(0,0),(-1,-1),'CENTER')]))
    story += [kt, Spacer(1, 12)]
    cols = ['estudiante','correo','horas_sin_actividad','riesgo_desconexion','tiempo_total_horas','pendientes','atrasadas','porcentaje_avance','puntaje_riesgo','riesgo_integral','accion_recomendada']
    view = summary[cols].head(35).copy() if not summary.empty else pd.DataFrame(columns=cols)
    view.columns = ['Estudiante','Correo','Horas sin act.','Riesgo conexión','Horas','Pend.','Atras.','Avance %','Puntaje','Riesgo total','Acción']
    data = [list(view.columns)] + view.fillna('').astype(str).values.tolist()
    table = Table(data, repeatRows=1, colWidths=[1.45*inch,1.55*inch,0.7*inch,0.95*inch,0.55*inch,0.45*inch,0.45*inch,0.6*inch,0.55*inch,0.75*inch,1.35*inch])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#6c757d')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.25,colors.lightgrey),('FONTSIZE',(0,0),(-1,-1),6.5),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(table)
    story.append(Spacer(1, 8))
    story.append(Paragraph('Nota: el listado prioriza los estudiantes con mayor puntaje de riesgo. Los datos dependen de los permisos del token y de los registros disponibles en Canvas.', styles['Small']))
    doc.build(story, onFirstPage=_watermark, onLaterPages=_watermark)
    return bio.getvalue()
