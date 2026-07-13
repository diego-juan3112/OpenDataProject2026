| nombre | tipo | fuente |
|---|---|---|
| `anio` | numérica | SIEDCO (grano temporal) |
| `poblacion` | numérica | DANE / SDP |
| `ipm_nbi` | numérica | DANE IPM (Sumapaz: mediana train) |
| `tasa_nuse_100k` | numérica | NUSE / población × 100k |
| `lag_1` | numérica | conteo_siedco año-1 misma localidad-tipo |
| `lag_2` | numérica | conteo_siedco año-2 |
| `lag_3` | numérica | conteo_siedco año-3 |
| `roll_mean_3` | numérica | media de lags 1–3 |
| `cod_localidad` | categórica | DIVIPOLA Bogotá |
| `tipo_delito` | categórica | taxonomía SIEDCO |

**Excluido a propósito:** `conteo_siedco` del mismo año — es la variable de la que se deriva `riesgo_alto` (fuga de etiqueta).
