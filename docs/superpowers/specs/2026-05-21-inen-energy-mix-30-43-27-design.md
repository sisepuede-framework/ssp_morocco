# Diseño — Mix energético de industria 30/43/27 a 2030

**Fecha:** 2026-05-21
**Proyecto:** SSP Morocco — sector INEN (Industrial Energy)
**Autor:** Fabian Fuentes (con Claude)

## 1. Contexto y objetivo

Se requiere que el mix de energía final de la industria marroquí alcance, hacia
**2030**, la siguiente composición:

- **30%** electricidad
- **43%** combustibles fósiles (incluye gas natural como combustible de transición)
- **27%** energía renovable directa, repartida de forma equilibrada en **9% hidrógeno
  verde + 9% biomasa sólida + 9% solar térmica**

Esto se modela como **proyección de referencia** (Enfoque B): el mix se incorpora
al caso BASE editando las trayectorias de entrada de SISEPUEDE, no como una
estrategia (`TX:`) comparable contra BASE.

### Por qué no sirven los transformadores INEN existentes

SISEPUEDE tiene solo tres transformadores INEN:

| Transformador | Efecto | ¿Sirve aquí? |
|---|---|---|
| `TFR:INEN:INC_EFFICIENCY_ENERGY` | Reduce consumo de energía final por unidad de producto | No — no reasigna combustibles |
| `TFR:INEN:INC_EFFICIENCY_PRODUCTION` | Reduce intensidad material/producción | No — no reasigna combustibles |
| `TFR:INEN:SHIFT_FUEL_HEAT` | Desplaza demanda de calor a electricidad + hidrógeno | Parcial — no puede generar biomasa ni solar térmica |

No existe ningún transformador que fije un mix de combustibles arbitrario. Por eso
el objetivo (renovables = H₂ + biomasa + solar) se implementa editando directamente
las fracciones de combustible de entrada.

## 2. Alcance

**Incluye:**
- Edición de las fracciones de combustible INEN (`frac_inen_energy_<categoría>_<combustible>`)
  para que el mix industrial converja a 30/43/27 hacia 2030.

**No incluye (tareas separadas):**
- Captura del 25% de GEI de fosfatos — es CCS, no una fracción de combustible.
  Se maneja con `TX:PFLO:INC_IND_CCS` sobre la categoría `chemicals` (ver §8).
- Que el hidrógeno sea efectivamente "verde" — depende de la producción de H₂ en
  ENTC; requeriría acompañar con `TX:ENTC:TARGET_CLEAN_HYDROGEN` en las estrategias.

## 3. Ubicación de la implementación

`ssp_modeling/notebooks/industry/moroco_manager_wb_inen.ipynb`, sección **"Custom
data modifications"** (celdas 20-21).

- Añadir una fila documentada a la tabla de racional en la celda markdown 20.
- Añadir una celda de código nueva después de la celda 21 (ajuste de gas MSP).

La modificación opera **en memoria** sobre `df_inputs_raw_complete`, antes de
construir `transformers` (celda 23). No altera el CSV en disco
(`sisepuede_raw_input_morocco_fuels.csv`), de modo que la fuente sigue siendo
reproducible. Como `df_inputs_raw_complete` alimenta al caso BASE, el mix queda
incorporado a la proyección de referencia.

## 4. Especificación del mix objetivo 2030

Las 13 fracciones de combustible por categoría INEN deben sumar 1.0. Objetivo
2030 (idéntico para todas las categorías):

| Combustible (columna SISEPUEDE) | Fracción 2030 |
|---|---:|
| `electricity` | 0.30 |
| `hydrogen` | 0.09 |
| `solid_biomass` | 0.09 |
| `solar` | 0.09 |
| `coal`, `coke`, `diesel`, `furnace_gas`, `gasoline`, `hydrocarbon_gas_liquids`, `kerosene`, `natural_gas`, `oil` | 0.43 (total) |
| **Suma** | **1.00** |

### Reparto del 43% fósil

El 0.43 se reparte entre los 9 combustibles fósiles **proporcionalmente a la
composición fósil de cada categoría en el año de inicio de rampa (2025)**:

```
share_f   = base_2025[f] / sum(base_2025[fósiles])      para cada fósil f
target[f] = 0.43 * share_f
```

Esto preserva la estructura realista de cada industria (p.ej. el cemento sigue
siendo carbón-intensivo) y mantiene al gas natural con su peso relativo dentro
del bloque fósil.

**Caso borde:** si una categoría tiene 0% de fósiles en 2025, se reparte el 0.43
en partes iguales entre los 9 combustibles fósiles (0.43 / 9 ≈ 0.0478 c/u).

### Aplicación uniforme

El mismo mix objetivo se aplica a las **21 categorías** INEN:
`agriculture_and_livestock`, `cement`, `chemicals`, `electronics`, `glass`,
`lime_and_carbonite`, `metals`, `mining`, `other_product_manufacturing`, `paper`,
`plastic`, `recycled_glass`, `recycled_metals`, `recycled_paper`,
`recycled_plastic`, `recycled_rubber_and_leather`, `recycled_textiles`,
`recycled_wood`, `rubber_and_leather`, `textiles`, `wood`.

Como el mix es idéntico en todas las categorías, el agregado nacional de la
industria es exactamente 30/43/27 (independiente de los pesos de demanda
energética por categoría).

## 5. Trayectoria temporal

Horizonte del modelo: `time_period` 0–55, años 2015–2070.

- **2015–2025:** se mantiene el valor calibrado/baseline (sin cambios).
- **2025–2030:** rampa lineal desde el valor baseline 2025 hasta el objetivo.
- **2030–2070:** plano en el objetivo.

Factor de rampa por año:

```
ramp(year) = clip( (year - 2025) / (2030 - 2025), 0, 1 )
```

Valor nuevo de cada fracción:

```
nuevo[year] = (1 - ramp(year)) * baseline[year] + ramp(year) * target
```

## 6. Algoritmo (pseudocódigo de la celda nueva)

```python
# CUSTOM DATA MODIFICATION — INEN energy mix 30/43/27 by 2030
# Reference projection: industry reaches 30% electricity, 43% fossils,
# 27% renewables (9% H2 + 9% biomass + 9% solar thermal) by 2030.
# Baseline held through 2025, linear ramp 2025->2030, flat 2030->2070.

INEN_CATEGORIES = [...]          # las 21 categorías de §4
RENEW_ELEC_TARGET = {"electricity": 0.30, "hydrogen": 0.09,
                     "solid_biomass": 0.09, "solar": 0.09}
FOSSIL_FUELS = ["coal", "coke", "diesel", "furnace_gas", "gasoline",
                "hydrocarbon_gas_liquids", "kerosene", "natural_gas", "oil"]
FOSSIL_TOTAL = 0.43
RAMP_START, RAMP_END = 2025, 2030

df   = df_inputs_raw_complete
year = df["year"]
ramp = ((year - RAMP_START) / (RAMP_END - RAMP_START)).clip(0, 1)

for cat in INEN_CATEGORIES:
    col = lambda f: f"frac_inen_energy_{cat}_{f}"

    # composición fósil baseline en 2025
    row25  = df.loc[year == RAMP_START].iloc[0]
    f_base = {f: row25[col(f)] for f in FOSSIL_FUELS}
    f_sum  = sum(f_base.values())
    if f_sum > 0:
        f_target = {f: FOSSIL_TOTAL * f_base[f] / f_sum for f in FOSSIL_FUELS}
    else:
        f_target = {f: FOSSIL_TOTAL / len(FOSSIL_FUELS) for f in FOSSIL_FUELS}

    target = {**RENEW_ELEC_TARGET, **f_target}   # 13 combustibles, suma 1.0

    for fuel, tval in target.items():
        c = col(fuel)
        df[c] = (1 - ramp) * df[c] + ramp * tval
```

## 7. Validación

Tras ejecutar la celda, verificar dentro del notebook:

1. **Suma = 1.0:** para cada categoría y año, la suma de las 13 fracciones
   `frac_inen_energy_<cat>_*` es 1.0 (tolerancia 1e-9).
2. **Objetivo 2030:** en `year == 2030`, para cada categoría:
   `electricity` = 0.30; `hydrogen` = `solid_biomass` = `solar` = 0.09;
   suma de fósiles = 0.43.
3. **Sin cambios pre-2025:** las fracciones en `year <= 2025` son idénticas al
   baseline original.
4. **Agregado nacional:** ponderando por demanda de energía INEN, el mix
   industrial total da 30/43/27 en 2030.

## 8. Componente separado — captura de fosfatos (25%)

Fuera del alcance de este diseño de mix. Se documenta para referencia:

- La captura del 25% de GEI **no es una fracción de combustible**; es CCS.
- Se implementa con `TX:PFLO:INC_IND_CCS` (transformador "Industrial Point of
  Capture"), que toma `dict_magnitude_prev` (prevalencia) y `dict_magnitude_eff`
  (eficacia). Fracción capturada = prevalencia × eficacia. Para 25%: p.ej.
  prevalencia 0.5 × eficacia 0.5, o prevalencia 0.28 × eficacia 0.9.
- Se aplica sobre la categoría industrial **`chemicals`** — SISEPUEDE no tiene
  categoría "fosfatos"; la industria de OCP cae en `chemicals`. Advertencia: la
  captura afectaría a toda la química, no solo a fosfatos.
- Decisión pendiente: implementarla como proyección de referencia (editar las
  variables de captura en el template IPPU) o como estrategia `TX:`.

## 9. Riesgos y supuestos conocidos

1. **Realismo a 2030.** Aplicar 30% electricidad + 27% renovable directo (incl.
   solar térmica y biomasa) a categorías de alta temperatura — `cement`, `metals`,
   `glass` — para 2030 es muy ambicioso técnicamente. El modelo lo acepta sin
   problema (las fracciones son inputs puros), pero es un escenario normativo, no
   restringido por factibilidad. Documentarlo así en la tabla de racional.

2. **Categorías ya limpias se vuelven más fósiles.** La aplicación uniforme fuerza
   el 43% de fósiles incluso en categorías que hoy son casi 100% eléctricas (p.ej.
   varias `recycled_*`). En esas categorías el cambio *aumenta* el uso de fósiles,
   lo opuesto a descarbonizar. Esto es consecuencia inevitable de exigir un
   agregado nacional exacto de 30/43/27 con mix uniforme.
   - **Alternativa documentada:** aplicar un tope "no peor que baseline" — si una
     categoría ya tiene electricidad+renovable por encima del objetivo, dejarla en
     su baseline. El agregado nacional resultaría algo *más limpio* que 43% fósil,
     no exacto. **Punto a decidir en la revisión del spec.**

3. **Hidrógeno verde.** En INEN, `hydrogen` es solo una fracción de combustible; su
   carácter "verde" depende de la producción en ENTC. Para que el 9% sea verde en
   el balance de emisiones, acompañar con `TX:ENTC:TARGET_CLEAN_HYDROGEN`.

4. **13 combustibles, sin geotérmica.** El CSV de Marruecos define 13 combustibles
   INEN por categoría (sin `geothermal`). Las 13 columnas quedan cubiertas: 4 de
   electricidad/renovables + 9 fósiles.
