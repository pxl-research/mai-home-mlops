# TODO: Waterlek-detectie

## Achtergrond

De generator produceert synthetische tijdreeksdata (uurlijks, per huishoudtype) met realistische nul-periodes
tijdens de nacht (uur 1–4). Een waterlek manifesteert zich typisch als een constante lage basisflow die
deze nulperiodes wegwerkt.

---

## 1. Rule-based baseline

**Idee:** als er in een venster van meerdere opeenvolgende nachten geen enkele nul-meting meer opduikt
tijdens de verwachte slaapuren, is er waarschijnlijk een lek.

**Implementatie:**

```python
def detect_leak_rule_based(df: pd.DataFrame, night_hours=(1, 4), window_days=3, threshold=0) -> pd.Series:
    """
    Geeft per dag True als er mogelijk een lek is, False als alles normaal lijkt.

    Logica: als het minimum nachtverbruik over een rollend venster van `window_days` nachten
    boven `threshold` ligt, wordt een lek gesignaleerd.
    """
    night = df[df['Timestamp'].dt.hour.between(*night_hours)].copy()
    night['date'] = night['Timestamp'].dt.date
    daily_min = night.groupby('date')['Volume_Liter'].min()
    rolling_min = daily_min.rolling(window_days).min()
    return rolling_min > threshold
```

**Parameters om te tunen:**
- `window_days`: hoeveel nachten achter elkaar zonder nul? (aanbeveling: 3)
- `night_hours`: welke uren gelden als slaapvenster? (aanbeveling: 1–4)
- `threshold`: onder welk volume is het "nul"? (aanbeveling: 0, of 1 bij ruizige metingen)

**Sterkte:** interpreteerbaar, geen trainingsdata nodig, vangt grove lekken direct.  
**Zwakte:** mist subtiele lekken overdag of lekken die kleiner zijn dan de meetresolutie.

---

## 2. Isolation Forest (unsupervised)

**Idee:** train een Isolation Forest op normale dagelijkse feature-vectors. Dagen die afwijken
van het normale patroon krijgen een lage anomaly score.

**Feature engineering (per dag):**

| Feature | Beschrijving | Waarom zinvol |
|---|---|---|
| `night_min` | Min verbruik in uur 1–4 | Lek → nooit meer 0 |
| `night_zero_ratio` | % uren 1–4 met Volume == 0 | Lek → ratio daalt naar 0% |
| `night_mean` | Gemiddeld nachtverbruik | Lek → stijgt structureel |
| `rolling_7d_night_min` | Rolling minimum over 7 nachten | Vangt geleidelijke lekken |
| `day_min` | Min verbruik overdag | Lek overdag (bijv. tuinslang) |
| `total_daily_volume` | Totaal dagverbruik | Lek verhoogt baseline |
| `zero_ratio_all` | % van alle uren met Volume == 0 | Lek reduceert nuluren |

**Implementatie:**

```python
from sklearn.ensemble import IsolationForest
import pandas as pd

def build_daily_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['date'] = df['Timestamp'].dt.date
    df['hour'] = df['Timestamp'].dt.hour
    df['is_night'] = df['hour'].between(1, 4)

    features = df.groupby('date').apply(lambda g: pd.Series({
        'night_min':           g[g['is_night']]['Volume_Liter'].min(),
        'night_zero_ratio':    (g[g['is_night']]['Volume_Liter'] == 0).mean(),
        'night_mean':          g[g['is_night']]['Volume_Liter'].mean(),
        'day_min':             g[~g['is_night']]['Volume_Liter'].min(),
        'total_daily_volume':  g['Volume_Liter'].sum(),
        'zero_ratio_all':      (g['Volume_Liter'] == 0).mean(),
    })).reset_index()

    features['rolling_7d_night_min'] = features['night_min'].rolling(7, min_periods=1).min()
    return features

def train_isolation_forest(features: pd.DataFrame, contamination=0.01) -> IsolationForest:
    feature_cols = ['night_min', 'night_zero_ratio', 'night_mean',
                    'rolling_7d_night_min', 'day_min', 'total_daily_volume', 'zero_ratio_all']
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(features[feature_cols])
    return model

def detect_leak_isolation_forest(model: IsolationForest, features: pd.DataFrame) -> pd.DataFrame:
    feature_cols = ['night_min', 'night_zero_ratio', 'night_mean',
                    'rolling_7d_night_min', 'day_min', 'total_daily_volume', 'zero_ratio_all']
    scores = model.decision_function(features[feature_cols])  # lager = meer afwijkend
    predictions = model.predict(features[feature_cols])       # -1 = anomalie, 1 = normaal
    features = features.copy()
    features['anomaly_score'] = scores
    features['is_anomaly'] = predictions == -1
    return features
```

**Parameters om te tunen:**
- `contamination`: verwacht aandeel lekdagen in trainingsdata (aanbeveling: 0.01 bij gezonde data)
- `random_state`: vastgepind op 42 voor reproduceerbaarheid

**Sterkte:** detecteert ook subtielere afwijkingen, geen gelabelde data nodig.  
**Zwakte:** minder interpreteerbaar; kan false positives geven bij vakantiedagen.

---

## Volgende stappen

- [ ] Lekpatronen toevoegen aan de generator (bijv. `leak_start`, `leak_rate` parameter)
- [ ] Rule-based baseline evalueren op gegenereerde data met en zonder lek
- [ ] Isolation Forest trainen op normale data en testen op data met gesimuleerd lek
- [ ] Vergelijk false positive rate: vakantiedagen vs. lekdagen (beide hebben lage nachtflow)
