"""Do the datasets join: Delphi (numbers) <-> Risk Repository (risks) <-> Mitigations."""
import warnings; warnings.filterwarnings("ignore")
import rdata, pandas as pd, numpy as np
from scipy.stats import spearmanr

d = rdata.read_rds("data/raw/delphi/safe_for_osf/delphi_snapshot.rds")
risks = d["meta"]["risks"]; risks.columns=[str(c) for c in risks.columns]
sev = d["severity_aggregate"]; sev.columns=[str(c) for c in sev.columns]
cat = sev[sev.level=="catastrophic"].pivot(index="risk_number",columns="scenario",values="pct")
rho,p = spearmanr(cat.bau, cat.pm)
print(f"Spearman BAU vs PM ranking: rho={rho:.3f} (p={p:.2g})")
print(f"Pearson: {np.corrcoef(cat.bau,cat.pm)[0,1]:.3f}")

repo = pd.read_excel("data/raw/ai-risk-repository.xlsx", sheet_name="AI Risk Database v4", header=2).dropna(how="all")
print("\n--- REPOSITORY")
print("rows:", len(repo), "| unique Sub-domains:", repo["Sub-domain"].nunique())
sd = repo["Sub-domain"].dropna().astype(str)
codes = sd.str.extract(r"^\s*(\d+\.\d+)")[0]
print("codes of the form N.N recognized:", codes.notna().sum(), "of", len(sd))
print("unrecognized values:", sorted(set(sd[codes.isna()]))[:10])

repo_codes = set(codes.dropna().unique()); delphi_codes = set(risks.taxonomy_id.astype(str))
print(f"\n--- JOIN DELPHI <-> REPOSITORY")
print("codes in Delphi:", len(delphi_codes), "| in repository:", len(repo_codes))
print("matched:", len(delphi_codes & repo_codes), "| repository only:", sorted(repo_codes-delphi_codes))
rows = codes.notna().sum()
print(f"repository rows that receive a numeric estimate via the join: {rows}/{len(repo)} = {rows/len(repo):.1%}")

cnt = codes.value_counts().rename_axis("code").rename("n_risk_rows").reset_index()
m = cnt.merge(risks.assign(code=risks.taxonomy_id.astype(str))[["code","short_name","risk_number"]], on="code", how="left")
m = m.merge(cat.reset_index()[["risk_number","bau"]], on="risk_number", how="left")
print("\nrisk rows per domain that carries a single estimate:")
print(m.sort_values("n_risk_rows",ascending=False).head(8).to_string(index=False))
print(f"\nmedian rows per domain: {m.n_risk_rows.median():.0f}, max: {m.n_risk_rows.max()}")
