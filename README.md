# AVE Canvas Analytics - Seguimiento Académico

Aplicación profesional en Streamlit para automatizar el seguimiento del asesor AVE mediante Canvas API.

## Funciones principales
- Conexión segura a Canvas por token.
- Listado de cursos y secciones.
- Extracción de estudiantes activos.
- Cálculo de riesgo por desconexión:
  - Bajo: 0 a 24 horas sin actividad.
  - Medio: más de 24 y hasta 72 horas.
  - Alto: más de 72 horas o sin registro.
- Medición del cumplimiento de mínimo 2 horas diarias.
- Extracción de entregas, tareas pendientes, atrasadas y avance académico.
- Índice integral de riesgo académico.
- Dashboard ejecutivo con gráficas.
- Historial en base SQLite local.
- Exportación a Excel y PDF con marca institucional.
- Mensajes sugeridos para seguimiento.

## Uso
1. Instale Python 3.10 o superior.
2. Descomprima esta carpeta.
3. Ejecute `INICIAR_APP_WINDOWS.bat`.
4. Ingrese URL de Canvas y token.
5. Presione `Probar conexión`.
6. Seleccione curso/sección y genere el análisis.

## Seguridad
El token no se guarda automáticamente. Si desea usar `.env`, copie `.env.example` como `.env` y complete sus datos.

Desarrollador: Ing. Christian Pocol, Ingeniero Electrónico.
