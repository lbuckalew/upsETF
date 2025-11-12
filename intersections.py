from typing import Dict, List
import json
from upsetplot import UpSet, from_memberships

class HoldingsSumException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}"

def parse_etf_pre_series(etf_json: dict):
    """
    Returns (net_assets, holding_values) where holding_values maps holding symbol -> dollar value in this ETF.
    value = net_assets * weight
    """
    try:
        net_assets = float(etf_json.get("net_assets", "0"))
    except Exception:
        net_assets = 0.0

    etf_json['net_assets'] = net_assets
    weights_sum = 0
    for h in etf_json.get("holdings", []):
        w = float(h.get('weight', '0').replace('%', '')) * 100
        h['weight'] = w
        weights_sum += w

    if weights_sum < 99:
        raise HoldingsSumException(f"ETF {etf_json['ticker']} holdings only sum to {int(weights_sum)}%")

def compute_weighted_intersections(etfs: List, pre_series: Dict):
    # Orgnaize holdings by which ETFs hold them
    holding_map = {}
    for etf in etfs:
        etf_t = etf.get("ticker", "UNKNOWN")
        for h in etf.get("holdings", []):
            holding_t = h.get("symbol", "UNKNOWN")
            if holding_map.get(holding_t) is None:
                holding_map[holding_t] = [{'etf': etf_t, 'value': h['weight']}]
            else:
                holding_map[holding_t].append({'etf': etf_t, 'value': h['weight']})

    removed_ticker = None
    while len(holding_map) > 0:
        if removed_ticker is not None:
            holding_map.pop(removed_ticker, None)
            removed_ticker = None

        for ticker, owners in holding_map.items():
            if len(owners) == 0:
                removed_ticker = ticker
                continue

            # Handle the interesction names and data population
            intersection_name = []
            for owner in owners:
                intersection_name.append(owner['etf'])
            if intersection_name not in pre_series['intersections']:
                pre_series['intersections'].append(intersection_name)
                pre_series['data'].append(0.0)
            intersection_index = pre_series['intersections'].index(intersection_name)

            # Find which owner has the minimum weight for this holding and add that weight to the
            # intersection data.
            owners.sort(key=lambda x: x['value'])
            min_owner = owners[0]
            min_value = min_owner['value']
            pre_series['data'][intersection_index] += min_value

            # Subtract the minimum weight from all other owners for this holding.
            for owner in owners:
                owner['value'] -= min_value

            # Pop the owner with the minimum weight, and add that weight to the intersection data.
            owners.pop(0)

    # Build a Series indexed by memberships with per-element values, then aggregate by sum
    s = from_memberships(pre_series['intersections'], data=pre_series['data'])
    # Ensure aggregation by exact membership signature
    s = s.groupby(level=s.index.names).sum()

    return s