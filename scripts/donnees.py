"""Annexe A, graine 7, sans modification de la génération."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def main():
    rng = np.random.default_rng(7)
    n = 5000
    montant = np.round(rng.lognormal(6.2, 1.1, n), 2)
    anciennete = rng.integers(0, 120, n)
    freq = rng.poisson(3, n) + 1
    nuit = rng.binomial(1, 0.18, n)
    score = 2.2*(np.log10(montant)-3.0) - anciennete/60 + (freq-3)/3 + nuit*1.2
    fraude = ((score + rng.normal(0, 0.35, n)) > 0.6).astype(int)
    df = pd.DataFrame({'montant': montant, 'anciennete': anciennete,
                       'freq_24h': freq, 'nuit': nuit, 'fraude': fraude})
    path = ROOT / 'data/transactions.csv'
    path.parent.mkdir(exist_ok=True)
    df.to_csv(path, index=False, lineterminator='\n')
    assert len(path.read_text().splitlines()) == 5001
    assert len(df) == 5000 and int(fraude.sum()) == 568
    assert not df.isna().any().any()
    result = {'provenance': 'simulation scikit-learn : données synthétiques Annexe A (NumPy/pandas)',
              'graine': 7, 'transactions': len(df), 'fraudes': int(fraude.sum()),
              'taux_fraude': float(fraude.mean()), 'lignes_avec_entete': 5001,
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'numpy': np.__version__, 'pandas': pd.__version__}
    (ROOT / 'reports/donnees_validation.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))

if __name__ == '__main__':
    main()
