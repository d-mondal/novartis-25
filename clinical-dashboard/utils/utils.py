import numpy as np

def compute_dqi(df):
    df["dqi"] = (
        0.4 * df.metric1 +
        0.3 * df.metric2 +
        0.3 * (100 - df.severity)
    ).clip(0,100)

    df["alert_flag"] = (df.dqi < 60).astype(int)
    return df
