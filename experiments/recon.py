"""Reality check on the MIT AI risk data: what is physically there and does it join."""
import warnings; warnings.filterwarnings("ignore")
import rdata, pandas as pd, numpy as np
pd.set_option("display.width", 200)

d = rdata.read_rds("data/raw/delphi/safe_for_osf/delphi_snapshot.rds")
meta = d["meta"]; risks = meta["risks"]; risks.columns=[str(c) for c in risks.columns]
for k in ("consensus","severity_aggregate","severity_expert","top_concerns"):
    d[k].columns=[str(c) for c in d[k].columns]
sev, cons, tc = d["severity_aggregate"], d["consensus"], d["top_concerns"]

print("="*78); print("1. WHAT IS IN THE DELPHI SNAPSHOT"); print("="*78)
print("round:", meta["round"], "| experts (per severity_expert):", d["severity_expert"].expert_hash.nunique())
print("risks:", len(risks), "| actors:", len(meta["actors"]), "| sectors:", len(meta["sectors"]))
print("\nDelphi risk taxonomy_ids:", sorted(risks.taxonomy_id.astype(str).tolist()))

# P(catastrophic) under BAU vs pragmatic mitigations
cat = sev[sev.level=="catastrophic"].pivot(index="risk_number", columns="scenario", values="pct")
cat = cat.join(risks.set_index("risk_number")[["taxonomy_id","short_name"]])
print(f"\ndomains with P(catastrophic)>10% — BAU: {(cat.bau>10).sum()}/24, PM: {(cat.pm>10).sum()}/24")
print("(the paper abstract reports 18 and 5)")

print("\n" + "="*78); print("2. EXPERIMENT: DOES THE SCENARIO CHANGE THE RANKING"); print("="*78)
cat["rank_bau"]=cat.bau.rank(ascending=False); cat["rank_pm"]=cat.pm.rank(ascending=False)
cat["shift"]=cat.rank_bau-cat.rank_pm
cat["reduction_pp"]=cat.bau-cat.pm
o=cat.sort_values("bau",ascending=False)
print(o[["taxonomy_id","short_name","bau","pm","reduction_pp","rank_bau","rank_pm","shift"]]
      .head(24).to_string(float_format=lambda v:f"{v:6.2f}"))
print(f"\nSpearman BAU vs PM: {cat.bau.corr(cat.pm, method='spearman'):.3f}")
print("max rank shift:", int(cat["shift"].abs().max()), "| shifted >=3 positions:", int((cat["shift"].abs()>=3).sum()))

print("\n" + "="*78); print("3. WHAT IS THERE ABOUT ACTORS"); print("="*78)
print(meta["actors"].to_string(index=False))
print("\ncriteria:", cons.criterion.unique(), "| target types:", cons.target_type.unique())
print("share of pairs with consensus:", f"{cons.consensus.mean():.1%}")
