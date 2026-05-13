# SOURCES.md — Datasets de Fase 1

> Documento de trazabilidad. Registra origen, fecha de descarga, licencia y estructura de cada dataset en `data/raw/`.
> Actualizado: 2026-05-09

---

## 1. results.csv

| Campo | Detalle |
|---|---|
| **Archivo** | `data/raw/results.csv` |
| **Fuente** | [martj42/international_results](https://github.com/martj42/international_results) |
| **URL de descarga** | `https://raw.githubusercontent.com/martj42/international_results/master/results.csv` |
| **Fecha de descarga** | 2026-05-09 |
| **Licencia** | CC0 1.0 — Dominio público |
| **Cobertura temporal** | 1872-11-30 → 2026-06-27 |
| **Filas** | 49,328 partidos internacionales |

**Columnas:**

| Columna | Descripción |
|---|---|
| `date` | Fecha del partido (YYYY-MM-DD) |
| `home_team` | Selección local |
| `away_team` | Selección visitante |
| `home_score` | Goles del equipo local (NaN si no jugado) |
| `away_score` | Goles del equipo visitante (NaN si no jugado) |
| `tournament` | Nombre del torneo (ej. "FIFA World Cup", "Friendly") |
| `city` | Ciudad donde se jugó |
| `country` | País sede |
| `neutral` | True si cancha neutral |

**Notas:** Incluye los 72 partidos programados del Mundial 2026 (fase de grupos) con resultados pendientes (NaN). Cubre más de 150 años de fútbol internacional incluyendo amistosos, clasificatorias y torneos oficiales.

---

## 2. goalscorers.csv

| Campo | Detalle |
|---|---|
| **Archivo** | `data/raw/goalscorers.csv` |
| **Fuente** | [martj42/international_results](https://github.com/martj42/international_results) |
| **URL de descarga** | `https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv` |
| **Fecha de descarga** | 2026-05-09 |
| **Licencia** | CC0 1.0 — Dominio público |
| **Filas** | 47,601 registros de goles |

**Columnas:**

| Columna | Descripción |
|---|---|
| `date` | Fecha del partido |
| `home_team` | Equipo local |
| `away_team` | Equipo visitante |
| `team` | Equipo del goleador |
| `scorer` | Nombre del goleador |
| `minute` | Minuto del gol |
| `own_goal` | True si es gol en propia puerta |
| `penalty` | True si es penalti |

---

## 3. shootouts.csv

| Campo | Detalle |
|---|---|
| **Archivo** | `data/raw/shootouts.csv` |
| **Fuente** | [martj42/international_results](https://github.com/martj42/international_results) |
| **URL de descarga** | `https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv` |
| **Fecha de descarga** | 2026-05-09 |
| **Licencia** | CC0 1.0 — Dominio público |
| **Filas** | 677 tandas de penaltis |

**Columnas:**

| Columna | Descripción |
|---|---|
| `date` | Fecha del partido |
| `home_team` | Equipo local |
| `away_team` | Equipo visitante |
| `winner` | Equipo ganador en penaltis |
| `first_shooter` | Equipo que tiró primero |

---

## 4. elo_ratings.csv

| Campo | Detalle |
|---|---|
| **Archivo** | `data/raw/elo_ratings.csv` |
| **Fuente** | [World Football Elo Ratings](https://www.eloratings.net/) |
| **URL de descarga** | `https://www.eloratings.net/World.tsv` + `https://www.eloratings.net/en.teams.tsv` |
| **Fecha de descarga** | 2026-05-09 |
| **Licencia** | Sin robots.txt restrictivo; no scraping masivo. Uso educativo/portfolio. |
| **Cobertura temporal** | Snapshot estático — ratings vigentes a 2026-05-09 |
| **Filas** | 244 selecciones nacionales |

**Columnas:**

| Columna | Descripción |
|---|---|
| `rank` | Posición en el ranking Elo mundial |
| `code` | Código interno de eloratings.net (ej. "ES", "AR") |
| `team` | Nombre completo del equipo en inglés |
| `elo_rating` | Rating Elo actual (a 2026-05-09) |
| `peak_elo` | Mejor rating Elo histórico del equipo |

**Notas:** Este dataset es un snapshot actual, no histórico. Para Elo histórico por partido se calculará en Fase 3 directamente desde `results.csv` usando el algoritmo estándar Elo con K=40 para torneos oficiales y K=20 para amistosos.

---

## 5. fifa_ranking.csv

| Campo | Detalle |
|---|---|
| **Archivo** | `data/raw/fifa_ranking.csv` |
| **Fuente** | [FIFA/Coca-Cola Men's World Ranking](https://www.fifa.com/fifa-world-ranking/men) — API pública de inside.fifa.com |
| **URL base** | `https://inside.fifa.com/api/ranking-overview?locale=en&dateId=id{ID}` |
| **Fecha de descarga** | 2026-05-09 |
| **Licencia** | Datos públicos FIFA. Uso educativo/portfolio. |
| **Cobertura temporal** | 2020-09-17 → 2025-09-18 (36 publicaciones) |
| **Filas** | 7,576 (equipos × publicación) |

**Columnas:**

| Columna | Descripción |
|---|---|
| `date_id` | ID interno de la publicación FIFA |
| `ranking_date` | Fecha de publicación del ranking (YYYY-MM-DD) |
| `rank` | Posición en el ranking FIFA |
| `team` | Nombre del equipo en inglés |
| `country_code` | Código FIFA de 3 letras (ej. "ESP", "ARG") |
| `points` | Puntuación FIFA/Coca-Cola |
| `confederation` | Confederación (UEFA, CONMEBOL, CAF, AFC, CONCACAF, OFC) |

**Notas:** La última publicación disponible vía API es septiembre 2025. No se encontraron publicaciones de 2026 en la API (posiblemente el portal FIFA no las expone aún, o requieren sesión). Para el modelado se usará la publicación más cercana a la fecha de cada partido usando `ranking_date`.

---

## 6. wc2026_groups.csv

| Campo | Detalle |
|---|---|
| **Archivo** | `data/raw/wc2026_groups.csv` |
| **Fuente** | Sorteo oficial FIFA — diciembre 2025. Construido manualmente. |
| **Fecha de creación** | 2026-05-09 |
| **Licencia** | Datos de dominio público (resultado de sorteo oficial FIFA). |
| **Filas** | 48 equipos clasificados |

**Columnas:**

| Columna | Descripción |
|---|---|
| `group` | Letra del grupo (A–L) |
| `team` | Nombre del equipo (mismo naming que `results.csv`) |
| `confederation` | Confederación del equipo |
| `host_country` | Yes/No — si el equipo es uno de los 3 anfitriones |
| `pot` | Bombo del sorteo (1–4) |

**Notas:** Los nombres de los equipos están normalizados para coincidir con los de `results.csv`. Verificado contra el calendario oficial que aparece en el propio `results.csv` (72 partidos de fase de grupos).

---

## Pendiente (Fase 2 o posterior)

| Dataset | Descripción | Prioridad |
|---|---|---|
| FIFA ranking 2026 | Las publicaciones de enero–mayo 2026 no están disponibles en la API pública. Posible obtención manual o scraping del portal FIFA cuando se habilite. | Media |
| Datos de jugadores/plantillas | FBref o Transfermarkt — estadísticas de jugadores para features avanzadas. | Baja (Fase 3 avanzada) |
