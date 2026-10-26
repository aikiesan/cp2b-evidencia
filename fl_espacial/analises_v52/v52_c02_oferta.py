"""C02 (v5.2): bagaço com o BMP proposto; regrava o cache/oferta_wide.pkl DESTA cópia."""
import pandas as pd

import fl_comum as C

RAZAO = {"min": 125 / 115, "med": 241.3 / 165, "max": 326 / 220}   # v52/mudancas.csv, C02
assert "fl_espacial_v52_C02" in str(C.HERE), f"rodando fora da cópia da C02: {C.HERE}"
f = C.CACHE / "oferta_wide.pkl"
OF = pd.read_pickle(f)
for sc, r in RAZAO.items():
    c = f"BAGACO__{sc}"
    antes = OF[c].sum()
    OF[c] = OF[c] * r
    print(f"{c}: {antes:,.0f} -> {OF[c].sum():,.0f} Nm3 CH4/dia (x{r:.3f})")
OF.to_pickle(f)
