"""Test: is the decision driven by what the data contains, or by what it lacks.

Decision question: which risk domain should get additional mitigation effort?
In the data: P(catastrophic) under BAU and under pragmatic mitigations -> achievable reduction.
Missing: cost and feasibility of mitigations per domain.
"""
import warnings; warnings.filterwarnings("ignore")
import rdata, numpy as np, pandas as pd
rng = np.random.default_rng(20260816)

d = rdata.read_rds("data/raw/delphi/safe_for_osf/delphi_snapshot.rds")
risks = d["meta"]["risks"]; risks.columns=[str(c) for c in risks.columns]
sev = d["severity_aggregate"]; sev.columns=[str(c) for c in sev.columns]
cat = sev[sev.level=="catastrophic"].pivot(index="risk_number",columns="scenario",values="pct")
df = cat.join(risks.set_index("risk_number")[["taxonomy_id","short_name"]])
df["reduction"] = df.bau - df.pm            # achievable reduction, pp — PRESENT in the data
n = len(df)

def ranks(v): return pd.Series(v, index=df.index).rank(ascending=False)
base = ranks(df.reduction)

def stability(cost_spread, N=4000):
    """share of domain pairs whose relative order survives an unknown cost"""
    keep = np.zeros((n,n)); tot = 0
    red = df.reduction.values
    for _ in range(N):
        cost = np.exp(rng.uniform(0, np.log(cost_spread), n))   # cost is unknown
        s = red / cost
        o = np.argsort(-s)
        r = np.empty(n); r[o] = np.arange(n)
        b = np.argsort(-red); rb = np.empty(n); rb[b] = np.arange(n)
        agree = ((r[:,None]-r[None,:]) * (rb[:,None]-rb[None,:])) > 0
        keep += agree; tot += 1
    iu = np.triu_indices(n,1)
    return (keep/tot)[iu].mean()

print("="*74); print("DECISION STABILITY TEST"); print("="*74)
print("Ranking by achievable reduction (this IS in the data):\n")
print(df.sort_values("reduction",ascending=False)[["taxonomy_id","short_name","bau","pm","reduction"]]
      .head(8).to_string(index=False, float_format=lambda v:f"{v:6.2f}"))

print("\nIntroduce an UNKNOWN mitigation cost with an x-fold spread ->")
print("share of domain pairs that keep their order:\n")
for spread in (1.5, 2, 3, 5, 10, 30):
    print(f"   spread x{spread:<4} : {stability(spread):.1%}")

print("\n--- For comparison: how stable is it to what the data DOES contain?")
print(f"   BAU vs PM (scenario switch): pair order agreement = "
      f"{(np.sign(np.subtract.outer(df.bau.values,df.bau.values))*np.sign(np.subtract.outer(df.pm.values,df.pm.values))>0)[np.triu_indices(n,1)].mean():.1%}")
print(f"   BAU vs achievable reduction: "
      f"{(np.sign(np.subtract.outer(df.bau.values,df.bau.values))*np.sign(np.subtract.outer(df.reduction.values,df.reduction.values))>0)[np.triu_indices(n,1)].mean():.1%}")

# width of confidence intervals — how precise the estimates themselves are
ci = sev[(sev.level=="catastrophic")].copy()
ci["w"] = ci.pct_ci_upper - ci.pct_ci_lower
print(f"\nWidth of the 95% CI on P(catastrophic): median {ci.w.median():.1f} pp, "
      f"at a median estimate of {ci.pct.median():.1f}%")
