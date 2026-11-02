"""
simulator.py - FINCH What-If Financial Scenario Simulator (Phase 4 Edition)
"""

def run_simulation(totals: dict, revenue_adj_pct: float, cost_adj_pct: float) -> dict:
    """
    Simulates adjusted financial performance based on percentage changes 
    to revenue and operational costs.
    
    Args:
        totals (dict): Dictionary containing base KPI values ('total_revenue', 'total_costs', 'net_profit').
        revenue_adj_pct (float): Percentage adjustment for revenue (e.g., +10.0 or -5.0).
        cost_adj_pct (float): Percentage adjustment for costs (e.g., +5.0 or -10.0).
        
    Returns:
        dict: Simulated revenue, costs, net profit, and profit margin.
    """
    if not totals:
        return {
            "revenue": 0.0,
            "costs": 0.0,
            "net_profit": 0.0,
            "profit_margin": 0.0
        }
        
    base_revenue = totals.get("total_revenue", 0.0)
    base_costs = totals.get("total_costs", 0.0)
    
    # If base_costs wasn't explicitly extracted but total_revenue and net_profit exist, estimate costs
    if base_costs == 0.0 and base_revenue > 0:
        net_profit_base = totals.get("net_profit", base_revenue * 0.25)
        base_costs = max(0.0, base_revenue - net_profit_base)

    # Apply percentage adjustments
    simulated_revenue = base_revenue * (1 + revenue_adj_pct / 100.0)
    simulated_costs = base_costs * (1 + cost_adj_pct / 100.0)
    
    simulated_net_profit = simulated_revenue - simulated_costs
    simulated_margin = (simulated_net_profit / simulated_revenue * 100) if simulated_revenue > 0 else 0.0
    
    return {
        "revenue": simulated_revenue,
        "costs": simulated_costs,
        "net_profit": simulated_net_profit,
        "profit_margin": simulated_margin
    }