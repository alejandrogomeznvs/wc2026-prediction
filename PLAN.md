# PLAN.md — Predicción Mundial 2026

> Documento maestro del proyecto. Cualquier sesión nueva (Sonnet u otra) debe leer este archivo **antes** de hacer cualquier cosa.
> Autor: Alejandro Gómez Navas — Analista de datos.
> Fecha de creación: 2026-05-09.

---

## 0. Reglas de trabajo (no negociables)

Estas reglas vienen del perfil del usuario y aplican a toda sesión:

1. **Calidad sobre velocidad.** Mejor hacerlo bien que rápido.
2. **Preguntar antes de ejecutar.** Si hay ambigüedad, usar `AskUserQuestion` o pedir confirmación.
3. **Mostrar plan antes de actuar.** Nunca empezar una fase sin confirmar el alcance.
4. **No inventar datos ni suposiciones.** Si falta información, pedirla o documentarla como "pendiente".
5. **No borrar nada sin aprobación explícita.**
6. **Sin relleno innecesario.** Respuestas mixtas (texto + listas), tono profesional cercano, en español.

---

## 1. Objetivo del proyecto

Construir un modelo de machine learning que prediga, con probabilidades calibradas, el resultado del **Mundial de Fútbol 2026** (USA-México-Canadá, 48 equipos):

- Probabilidad de cada selección de **ganar el torneo**.
- Probabilidad de cada selección de **avanzar ronda por ronda** (grupos → octavos → cuartos → semis → final → campeón).
- Bracket más probable y análisis de incertidumbre.

El proyecto es pieza central del **portfolio de Alejandro** para conseguir su primer trabajo como Analista de Datos.

---

## 2. Decisiones tomadas

| Decisión | Elección | Motivo |
|---|---|---|
| Edición a predecir | **Mundial 2026** | Próximo evento, máxima relevancia para portfolio |
| Entregable | **Repo en GitHub + Dashboard** | Combina parte técnica y storytelling visual |
| Tipo de modelo | **Avanzado: XGBoost / Random Forest** | Cercano a lo que se usa en empresas, mejor rendimiento |
| Lenguaje | **Python 3.11** | Stack del usuario |
| Visualización | **Streamlit** (Python) | Máximo control de diseño, sin dependencia de licencias, desplegable como URL pública |
| Formato del repo | Notebooks + código modular en `src/` + README profesional | Estándar de portfolio |

---

## 3. Estructura del proyecto

```
Predicción Mundial/
├── PLAN.md                  ← este archivo
├── README.md                ← README público para portfolio
├── requirements.txt         ← dependencias Python
├── .gitignore
├── data/
│   ├── raw/                 ← datasets originales sin tocar
│   └── processed/           ← datasets limpios listos para modelar
├── notebooks/
│   ├── 01_EDA.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_modeling.ipynb
│   └── 04_simulation.ipynb
├── src/                     ← código modular reutilizable
│   ├── data_loader.py
│   ├── features.py
│   ├── models.py
│   └── simulation.py
├── reports/                 ← outputs (gráficos, métricas, CSVs finales)
│   ├── simulation_results.csv      ← prob. por equipo y ronda (48 filas)
│   └── group_match_results.csv     ← prob. por partido de grupos (72 filas, Monte Carlo)
└── dashboard.py             ← dashboard Streamlit (arrancar con: streamlit run dashboard.py)
```

---

## 4. Roadmap por fases

### Fase 0 — Setup ✅
Estructura de carpetas, README inicial, `.gitignore`, `requirements.txt`, `git init`.

### Fase 1 — Recopilación de datos

**Fuentes a evaluar (validar licencia y actualidad antes de descargar):**

- [International football results 1872–presente](https://github.com/martj42/international_results) — partidos internacionales (CSV en GitHub, dominio público).
- [FIFA World Ranking histórico](https://www.fifa.com/fifa-world-ranking) — ranking mensual.
- [World Football Elo Ratings](https://www.eloratings.net/) — Elo dinámico por selección.
- [FBref](https://fbref.com/) o [Transfermarkt](https://www.transfermarkt.com/) — datos de jugadores y squads (opcional, fase 2).
- Calendario y clasificados oficiales del **Mundial 2026** (web FIFA cuando esté publicado).

**Entregable:** ficheros CSV originales en `data/raw/` con un `data/raw/SOURCES.md` que documente origen, fecha de descarga, licencia y columnas.

### Fase 2 — EDA y limpieza 

**Notebook:** `notebooks/01_EDA.ipynb`

Tareas:

- Cargar y unificar fuentes en un solo dataset de partidos.
- Normalizar nombres de selecciones (mismo equipo escrito de varias formas).
- Manejar fusiones políticas: URSS, Yugoslavia, Checoslovaquia, Alemania Este/Oeste, Serbia y Montenegro, etc.
- Detectar y documentar outliers y datos faltantes.
- Análisis exploratorio: ventaja local, evolución de goles por década, fuerza por confederación, calibración FIFA ranking vs resultados.

**Entregable:** `data/processed/matches_clean.csv` + notebook con EDA documentado.

### Fase 3 — Feature engineering 

**Notebook:** `notebooks/02_feature_engineering.ipynb` + módulo `src/features.py`

Variables a generar (negociables — confirmar con usuario antes de implementar todas):

- **Elo rating** de cada equipo a fecha del partido y diferencia de Elo.
- **FIFA ranking** y diferencia.
- **Forma reciente:** media de goles favor/contra y % victorias en últimos 5/10/20 partidos.
- **Head-to-head:** balance de los últimos 10 enfrentamientos directos.
- **Tipo de partido:** amistoso, clasificatorio, fase final.
- **Confederación** y partido en confederación propia (proxy de "casi local").
- **Local / visitante / neutral.**
- **Días de descanso** entre partidos.
- **Histórico en Mundiales:** apariciones, mejor resultado, partidos jugados.

**Entregable:** `data/processed/features_train.csv` y `features_test.csv`.

### Fase 4 — Modelado 

**Notebook:** `notebooks/03_modeling.ipynb` + módulo `src/models.py`

Estrategia:

- **Target principal:** clasificación multiclase (victoria local / empate / visitante) con probabilidades calibradas.
- **Target paralelo (opcional, fase avanzada):** modelo de goles esperados por equipo (regresión Poisson o regresión sobre conteo de goles).
- **Modelos:**
  - Random Forest (baseline).
  - XGBoost (modelo principal).
  - Regresión logística como sanity check.
- **Validación temporal** (no aleatoria): entrenar hasta 2018 → validar con Mundial 2022 → test final con clasificatorios 2024-2026.
- **Métricas:** log-loss, Brier score, accuracy, calibration plot.
- **Calibración:** isotonic o Platt scaling si las probabilidades no salen bien calibradas.

**Entregable:** modelo serializado en `src/models/` + notebook con métricas y comparativa.

### Fase 5 — Simulación Monte Carlo del torneo 

**Notebook:** `notebooks/04_simulation.ipynb` + módulo `src/simulation.py`

Tareas:

- Cargar el calendario y formato oficial del Mundial 2026 (48 equipos, 12 grupos de 4).
- Implementar la lógica del torneo: fase de grupos → 16avos → 8avos → 4tos → semis → final.
- Simular **10.000+ veces** todo el torneo usando las probabilidades del modelo.
- Para cada selección calcular el % de:
  - Pasar de fase de grupos.
  - Llegar a octavos / cuartos / semifinales / final.
  - Ganar el Mundial.
- Identificar el bracket más probable.

**Entregable:** `reports/simulation_results.csv` listo para alimentar el dashboard.

### Fase 6 — Dashboard ✅

Dashboard interactivo construido en **Streamlit** (dark theme, colores del Mundial 2026).

**6 páginas:**
1. **Grupos** — 12 tarjetas con clasificaciones predichas por % de avance desde grupos.
2. **Bracket** — Cuadro completo desde Ronda de 32 (2 lados + Final en centro). Cards con ganador en verde/perdedor tachado. Líneas conectoras entre rondas. Spotlight campeón/finalista.
3. **Probabilidades** — Barras H/D/A por partido, filtrable por grupo. Probabilidades empíricas Monte Carlo.
4. **Resumen** — KPIs, top 12 favoritos, donut por confederación, ranking completo 48 equipos.
5. **Simulador** — Tabs: fase de grupos (drag-and-drop) + eliminatoria interactiva (2 lados, botones). Cascade invalidation al cambiar resultados.
6. **Sobre el proyecto** — Metodología, datos, stack técnico, limitaciones.

**Decisiones técnicas:**
- Probabilidades de grupos: extraídas de la simulación Monte Carlo (`reports/group_match_results.csv`).
- Probabilidades en bracket: fórmula Elo `1 / (1 + 10^(-(EloA−EloB)/400))` para cada cruce.
- Bracket estático (Bracket) vs interactivo (Simulador) — session state con namespace para evitar conflictos.
- Cascade invalidation: al cambiar un resultado en el Simulador se borran automáticamente los resultados downstream.
- `streamlit-sortables` para drag-and-drop en simulador de grupos.

**Arrancar:** `streamlit run dashboard.py` → http://localhost:8501

**Entregable:** `dashboard.py` + `requirements.txt` + `reports/group_match_results.csv`.

### Fase 7 — README + portfolio

- README con: problema, datos, metodología, resultados, limitaciones, cómo reproducir, link al dashboard, capturas.
- Badges (Python version, licencia).
- Texto pulido para que un reclutador no técnico lo entienda en 60 segundos.
- Subir a GitHub público.

---

## 5. Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Nombres de selecciones inconsistentes entre fuentes | Diccionario manual de mapeo en `src/data_loader.py` |
| Sobreajuste al pasado: modelo "bueno" en métricas pero falla campeón | Comunicar incertidumbre con probabilidades, no solo el ganador |
| Mundial 2026 con formato nuevo (48 equipos) — sin precedente histórico | Adaptar simulación al nuevo formato; documentar la limitación |
| Datos de eloratings.net pueden requerir scraping | Validar TOS antes de scrapear; preferir fuentes con CSV directo |
| Streamlit sin watchdog — cambios no se recargan solos | Instalar watchdog (`pip install watchdog`) o reiniciar el proceso |

---

## 6. Estado actual

- [x] Fase 0 — Setup
- [x] Fase 1 — Recopilación de datos
- [x] Fase 2 — EDA y limpieza
- [x] Fase 3 — Feature engineering
- [x] Fase 4 — Modelado
- [x] Fase 5 — Simulación Monte Carlo
- [x] Fase 6 — Dashboard (Streamlit, 4 páginas, dark theme Mundial 2026)
- [ ] Fase 7 — README final y publicación

---

## 7. Próximos pasos inmediatos (Fase 7)

**Objetivo: publicar el proyecto en GitHub como pieza de portfolio.**

1. **Capturas del dashboard** — tomar screenshots de las 6 páginas para incluir en el README y en LinkedIn.
2. **Despliegue en Streamlit Community Cloud** (opcional pero recomendado):
   - Crear repo en GitHub (`wc2026-prediction` o similar).
   - Conectar con [share.streamlit.io](https://share.streamlit.io) → URL pública gratuita.
   - Asegurarse de que `reports/` y `data/processed/` están en el repo (no están en `.gitignore`).
3. **Añadir licencia MIT** — crear `LICENSE` en la raíz.
4. **Pulir LinkedIn post** — describir el proyecto en 3-4 párrafos con la URL del dashboard.
5. Para regenerar la simulación: `python3 -c "from src.simulation import run_monte_carlo, save_results; save_results(run_monte_carlo())"`

---
