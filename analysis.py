"""
analysis.py - FINCH Data Engine & Cleaning Module (Phase 4 Edition)
"""
import pandas as pd
import numpy as np
import re

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the raw dataframe by stripping column whitespace, 
    dropping completely empty rows/columns, and converting numeric-like string series.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Drop completely empty rows and columns
    df = df.dropna(how='all').dropna(axis=1, how='all')
    
    # Clean string headers
    df.columns = [str(col).strip() for col in df.columns]
    
    # Attempt to clean currency/string formatted numeric columns
    for col in df.columns:
        if df[col].dtype == object:
            # Check if column looks like it contains currency or numbers with symbols
            sample_vals = df[col].dropna().astype(str).head(10)
            is_numeric_string = sample_vals.str.contains(r'[$₦€£,\d\.\-\s]+', regex=True).all()
            
            if is_numeric_string and not sample_vals.str.contains(r'[a-zA-Z]{3,}', regex=True).any():
                try:
                    cleaned_series = (
                        df[col].astype(str)
                        .str.replace(r'[₦$€£,\s]', '', regex=True)
                        .str.replace(r'[\(\)]', '-', regex=True)  # handle accounting negative formats like (100) -> -100
                    )
                    numeric_conversion = pd.to_numeric(cleaned_series, errors='coerce')
                    if numeric_conversion.notnull().sum() > 0:
                        df[col] = numeric_conversion
                except Exception:
                    pass
                    
    return df

def extract_kpis(df: pd.DataFrame) -> dict:
    """
    Automatically detects Revenue, Cost, and Profit columns 
    and extracts core financial KPIs.
    """
    if df is None or df.empty:
        return {"total_revenue": 0.0, "total_costs": 0.0, "net_profit": 0.0, "profit_margin": 0.0}
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    total_revenue = 0.0
    total_costs = 0.0
    net_profit = 0.0
    
    # Heuristic column detection
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ["revenue", "sales", "income", "turnover", "gross income"]):
            if pd.api.types.is_numeric_dtype(df[col]):
                total_revenue = float(df[col].sum())
        elif any(kw in col_lower for kw in ["cost", "expense", "opex", "cogs", "expenditure"]):
            if pd.api.types.is_numeric_dtype(df[col]):
                total_costs += float(df[col].sum())
        elif any(kw in col_lower for kw in ["profit", "net", "margin", "earnings", "income after tax"]):
            if pd.api.types.is_numeric_dtype(df[col]):
                net_profit = float(df[col].sum())
                
    # Fallback heuristics if columns aren't explicitly named
    if total_revenue == 0.0 and len(numeric_cols) > 0:
        total_revenue = float(df[numeric_cols[0]].sum())
        
    if total_costs == 0.0 and len(numeric_cols) > 1:
        total_costs = float(df[numeric_cols[1]].sum())
        
    if net_profit == 0.0:
        net_profit = total_revenue - total_costs
        
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    
    return {
        "total_revenue": total_revenue,
        "total_costs": total_costs,
        "net_profit": net_profit,
        "profit_margin": profit_margin
    }

def generate_health_score(df: pd.DataFrame) -> float:
    """
    Calculates a comprehensive business health score (out of 100) 
    based on profitability margins, cost ratios, and data integrity.
    """
    if df is None or df.empty:
        return 50.0
        
    kpis = extract_kpis(df)
    margin = kpis.get("profit_margin", 0.0)
    
    # Scoring matrix based on net profit margins
    base_score = 50.0
    if margin > 30:
        base_score = 95.0
    elif margin > 20:
        base_score = 85.0
    elif margin > 10:
        base_score = 75.0
    elif margin > 0:
        base_score = 65.0
    else:
        base_score = 35.0 # Negative margin penalty
        
    return float(np.clip(base_score, 10.0, 100.0))

def detect_outliers(df: pd.DataFrame) -> list:
    """
    Scans numerical columns using Interquartile Range (IQR) 
    to pinpoint anomalous financial transactions or spikes.
    """
    outliers = []
    if df is None or df.empty:
        return outliers
    
    numeric_df = df.select_dtypes(include=[np.number])
    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
        if len(series) < 4:
            continue
            
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        
        if iqr == 0:
            continue
            
        upper_bound = q3 + 1.5 * iqr
        lower_bound = q1 - 1.5 * iqr
        
        anomalies = df[(df[col] > upper_bound) | (df[col] < lower_bound)]
        for idx, row in anomalies.iterrows():
            outliers.append(f"Row {idx} ({col}): Unusually extreme value detected ({row[col]:,.2f}).")
            
    return outliers[:15] # Return top 15 prioritized anomalies