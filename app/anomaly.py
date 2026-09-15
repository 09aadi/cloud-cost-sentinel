def compute_anomalies(records, window=7, threshold_pct=50.0):
    """
    Flags days where spend is more than `threshold_pct` above the
    average of the prior `window` days (or fewer, if less history exists).
    The first chronological record is always skipped -- there's no prior
    data to compare it against.
    """
    sorted_records = sorted(records, key=lambda r: r.date)
    anomalies = []
 
    for i in range(1, len(sorted_records)):
        prior_window = sorted_records[max(0, i - window):i]
        average = sum(r.amount for r in prior_window) / len(prior_window)
        threshold = average * (1 + threshold_pct / 100)
 
        if sorted_records[i].amount > threshold:
            anomalies.append({
                "date": sorted_records[i].date,
                "amount": sorted_records[i].amount,
                "average": average,
                "pct_above": ((sorted_records[i].amount - average) / average) * 100,
            })
 
    return anomalies