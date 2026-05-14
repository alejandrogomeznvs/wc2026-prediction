# Predicción Mundial 2026 ⚽

> Modelo de Machine Learning con simulación Monte Carlo para predecir el **Mundial de Fútbol 2026** (USA · México · Canadá · 48 equipos).  
> **Autor:** Alejandro Gómez Navas — Analista de Datos — Barcelona.

---

## Demo

**[wc2026-prediction.streamlit.app](https://wc2026-prediction.streamlit.app/)** — live dashboard

```bash
# O en local:
streamlit run dashboard.py
```

---

## Qué hace el proyecto

A partir del histórico completo de partidos internacionales (1872–2026), ratings Elo y ranking FIFA, se entrena un modelo de clasificación multiclase que estima:

- Probabilidad de **ganar el torneo** para cada selección.
- Probabilidad de **avanzar ronda a ronda** (grupos → octavos → cuartos → semis → final).
- **Bracket más probable** con probabilidades en cada cruce.

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.11 |
| Modelo | Regresión Logística multiclase (scikit-learn) |
| Simulación | Monte Carlo × 10.000 iteraciones |
| Dashboard | Streamlit (dark theme) |
| Visualización | Plotly + HTML/CSS custom |
| Datos | pandas · numpy |
| Entorno | JupyterLab |

---

## Estructura del repositorio

```
Predicción Mundial/
├── dashboard.py             ← Dashboard Streamlit (punto de entrada)
├── requirements.txt
├── .gitignore
├── PLAN.md                  ← Documento maestro del proyecto
├── data/
│   ├── raw/                 ← Datasets originales (SOURCES.md documenta origen)
│   └── processed/           ← Datasets limpios listos para modelar
├── notebooks/
│   ├── 00_data_collection.ipynb
│   ├── 01_EDA.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_modeling.ipynb
│   └── 04_simulation.ipynb
├── src/                     ← Código modular reutilizable
│   ├── features.py          ← Ingeniería de variables
│   ├── models.py            ← Entrenamiento y evaluación
│   ├── simulation.py        ← Simulación Monte Carlo
│   └── models/              ← Modelos serializados
└── reports/                 ← Outputs: métricas, gráficos, CSVs finales
    ├── simulation_results.csv       ← Probabilidades por equipo y ronda
    └── group_match_results.csv      ← Probabilidades por partido de grupos
```

---

## Cómo reproducir

```bash
# 1. Clonar el repositorio
git clone <url>
cd "Predicción Mundial"

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate    # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Lanzar el dashboard
streamlit run dashboard.py

# Regenerar simulación (si cambian los datos)
python3 -c "from src.simulation import run_monte_carlo, save_results; save_results(run_monte_carlo())"
```

---

## Dashboard — páginas

| Página | Descripción |
|---|---|
| **Grupos** | 12 tarjetas con clasificaciones predichas por % de avance |
| **Bracket** | Cuadro completo desde Ronda de 32 con líneas conectoras y ganadores destacados |
| **Probabilidades** | Barras H/D/A por partido filtrable por grupo (Monte Carlo) |
| **Resumen** | KPIs, top 12 favoritos, donut por confederación, ranking 48 equipos |
| **Simulador** | Simula grupos y eliminatoria de forma interactiva |
| **Sobre el proyecto** | Metodología, datos y limitaciones |

---

## Metodología

### Datos
- **49.328 partidos** internacionales (1872–2026) — fuente abierta.
- **Elo ratings** actualizados a mayo 2026.
- **Ranking FIFA** histórico desde 2020.
- Calendario oficial del Mundial 2026 (48 equipos, 12 grupos).

### Modelo
- **Regresión Logística** multiclase: victoria local / empate / derrota visitante.
- **41 variables:** diferencia Elo, ranking FIFA, forma reciente (últimos 5/10 partidos), head-to-head, experiencia en Mundiales.
- **Validación temporal** estricta: entrenado hasta 2018, validado 2019–2022, test 2023–2025.
- **Métricas:** Accuracy 61.6% · Log-loss 0.845 · Brier 0.166.

### Simulación
- 10.000 simulaciones completas del torneo, incluyendo los 72 partidos de grupos y toda la eliminatoria.
- Las probabilidades reflejan el nivel real del grupo, no solo el partido aislado.
- Para el bracket: probabilidades Elo directas para cada cruce específico.

---

## Limitaciones

- El modelo predice en base a **rendimiento histórico** — no considera lesiones, sanciones ni condición física actual.
- El formato de **48 equipos** es nuevo en 2026; el modelo nunca ha entrenado con ese formato exacto.
- El ranking FIFA más reciente disponible es de **septiembre 2025**.
- XGBoost fue descartado por incompatibilidades en macOS; la **Regresión Logística** resultó ser el modelo con mejor rendimiento en validación.

---

## Estado del proyecto

- [x] Fase 0 — Setup inicial
- [x] Fase 1 — Recopilación de datos
- [x] Fase 2 — EDA y limpieza
- [x] Fase 3 — Feature engineering
- [x] Fase 4 — Modelado
- [x] Fase 5 — Simulación Monte Carlo
- [x] Fase 6 — Dashboard Streamlit
- [ ] **Fase 7 — Publicación en GitHub** ← siguiente

---

## Licencia

MIT — ver [LICENSE](./LICENSE) cuando se añada antes de publicar.

## Contacto

Alejandro Gómez Navas · Barcelona · [GitHub](https://github.com/alejandrogomeznvs/wc2026-prediction)
