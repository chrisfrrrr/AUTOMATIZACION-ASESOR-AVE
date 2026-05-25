from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path('data/historial_ave_canvas.db')

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            course_id TEXT,
            course_name TEXT,
            section_id TEXT,
            section_name TEXT,
            user_id TEXT,
            estudiante TEXT,
            correo TEXT,
            ultima_actividad TEXT,
            horas_sin_actividad REAL,
            riesgo_desconexion TEXT,
            tiempo_total_horas REAL,
            horas_esperadas REAL,
            deficit_horas REAL,
            cumplimiento_horas TEXT,
            actividades_total REAL,
            entregadas REAL,
            pendientes REAL,
            atrasadas REAL,
            porcentaje_avance REAL,
            promedio_score REAL,
            puntaje_riesgo REAL,
            riesgo_integral TEXT,
            accion_recomendada TEXT
        )''')
        con.commit()

def save_snapshot(df: pd.DataFrame, course_id, course_name, section_id, section_name, created_at: str):
    init_db()
    temp = df.copy()
    temp['created_at'] = created_at
    temp['course_id'] = str(course_id)
    temp['course_name'] = course_name
    temp['section_id'] = '' if section_id is None else str(section_id)
    temp['section_name'] = section_name or 'Todas'
    cols = ['created_at','course_id','course_name','section_id','section_name','user_id','estudiante','correo','ultima_actividad',
            'horas_sin_actividad','riesgo_desconexion','tiempo_total_horas','horas_esperadas','deficit_horas','cumplimiento_horas',
            'actividades_total','entregadas','pendientes','atrasadas','porcentaje_avance','promedio_score','puntaje_riesgo','riesgo_integral','accion_recomendada']
    for c in cols:
        if c not in temp.columns: temp[c] = None
    temp['ultima_actividad'] = temp['ultima_actividad'].astype(str)
    with sqlite3.connect(DB_PATH) as con:
        temp[cols].to_sql('snapshots', con, if_exists='append', index=False)

def load_history(course_id=None) -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        q = 'SELECT * FROM snapshots'
        params = []
        if course_id:
            q += ' WHERE course_id=?'
            params.append(str(course_id))
        q += ' ORDER BY created_at DESC'
        return pd.read_sql_query(q, con, params=params)
