import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import minimize

# --- Helper Functions ---
def calculate_returns(prices):
    return prices.pct_change().dropna()

def calculate_volatility(returns):
    return returns.std() * np.sqrt(252)

def calculate_var(returns, confidence_level=0.95):
    return -np.percentile(returns, 100 * (1 - confidence_level))

def calculate_cvar(returns, confidence_level=0.95):
    alpha = 1 - confidence_level
    sorted_returns = returns.sort_values()
    var = -np.percentile(sorted_returns, 100 * alpha)
    cvar = -sorted_returns[sorted_returns <= -var].mean()
    return cvar

def calculate_portfolio_value(spot_prices, futures_prices, hedge_ratio):
    portfolio_value = [spot_prices.iloc[0]]
    for i in range(1, len(spot_prices)):
        delta_spot = spot_prices.iloc[i] - spot_prices.iloc[i-1]
        delta_futures = futures_prices.iloc[i] - futures_prices.iloc[i-1]
        portfolio_value.append(portfolio_value[-1] + delta_spot - (hedge_ratio * delta_futures))
    return pd.Series(portfolio_value, index=spot_prices.index)

def calculate_min_variance_hedge_ratio(spot_returns, futures_returns, window=20):
    hedge_ratios = pd.Series(index=spot_returns.index)
    for i in range(window, len(spot_returns)):
        covariance = np.cov(spot_returns[i-window:i], futures_returns[i-window:i])[0, 1]
        futures_variance = np.var(futures_returns[i-window:i])
        if futures_variance > 0:
            hedge_ratios.iloc[i] = covariance / futures_variance
        else:
            hedge_ratios.iloc[i] = 0
    return hedge_ratios.fillna(method='ffill').fillna(0)

# --- Load Data from Excel Files ---
@st.cache_data
def load_data():
    try:
        spot_df = pd.read_excel("PSOYBUSDM.xlsx", parse_dates=['Date'], index_col=['Date']).rename(columns={'Price': 'Spot_Price'})  # Adjust 'Price' if your spot price column has a different name
        futures_df = pd.read_excel("Soybean_contract.xlsx", parse_dates=['Date'], index_col=['Date']).rename(columns={'Price': 'Futures_Price'})  # Adjust 'Price' if your futures price column has a different name
        data = spot_df.merge(futures_df, left_index=True, right_index=True, how='inner')
        st.success("Data loaded successfully from Excel files.")
        return data
    except FileNotFoundError as e:
        st.error(f"Error: One or both Excel files not found. Please ensure 'PSOYBUSDM.xlsx' and 'Soybean_contract.xlsx' are in the same directory as the script.")
        return None
    except Exception as e:
        st.error(f"Error loading Excel data: {e}")
        return None

data = load_data()

# --- Sidebar for Settings ---
st.sidebar.header("Hedging Parameters")
fixed_hedge_ratio = st.sidebar.slider("Fixed Hedge Ratio:", 0.0, 2.0, 1.0, 0.05)
mv_window = st.sidebar.slider("Minimum Variance Window:", 10, 100, 20, 5)

# --- Main Dashboard ---
st.title("Soybean Hedging Strategy Comparison Dashboard")
st.markdown("Evaluate the performance of different hedging strategies using local Excel data.")

if data is not None:
    st.subheader("Price Data")
    st.dataframe(data.head())

    # --- Calculate Returns ---
    spot_returns = calculate_returns(data['Spot_Price'])
    futures_returns = calculate_returns(data['Futures_Price'])

    # --- Implement Hedging Strategies ---
    data['No_Hedge_Portfolio'] = data['Spot_Price']
    data['Naive_Hedge_Portfolio'] = calculate_portfolio_value(data['Spot_Price'], data['Futures_Price'], 1)
    data['Fixed_Hedge_Portfolio'] = calculate_portfolio_value(data['Spot_Price'], data['Futures_Price'], fixed_hedge_ratio)
    data['Min_Variance_Ratio'] = calculate_min_variance_hedge_ratio(spot_returns, futures_returns, window=mv_window)
    data['Min_Variance_Hedge_Portfolio'] = calculate_portfolio_value(data['Spot_Price'], data['Futures_Price'], data['Min_Variance_Ratio'])

    # --- Calculate Performance Metrics ---
    metrics = {}
    strategies = {
        'No Hedge': 'No_Hedge_Portfolio',
        'Naive Hedge (1:1)': 'Naive_Hedge_Portfolio',
        f'Fixed Hedge ({fixed_hedge_ratio:.2f})': 'Fixed_Hedge_Portfolio',
        f'Min Variance Hedge (window={mv_window})': 'Min_Variance_Hedge_Portfolio'
    }

    for name, column in strategies.items():
        returns = calculate_returns(data[column])
        metrics[name] = {
            'Annualized Volatility': f"{calculate_volatility(returns):.2f}",
            'VaR (95%)': f"{calculate_var(returns):.2f}",
            'CVaR (95%)': f"{calculate_cvar(returns):.2f}",
            'Total Return (%)': f"{(data[column].iloc[-1] / data[column].iloc[0] - 1) * 100:.2f}%",
            'Volatility Reduction vs. No Hedge (%)': f"{((calculate_volatility(calculate_returns(data['No_Hedge_Portfolio'])) - calculate_volatility(returns)) / calculate_volatility(calculate_returns(data['No_Hedge_Portfolio'])) * 100):.2f}%" if name != 'No Hedge' else "0.00%"
        }

    st.subheader("Performance Metrics")
    metrics_df = pd.DataFrame(metrics).T
    st.dataframe(metrics_df)

    # --- Interactive Visualizations ---
    st.subheader("Price Series Comparison")
    fig_prices = px.line(data[['Spot_Price', 'Futures_Price', 'No_Hedge_Portfolio', 'Naive_Hedge_Portfolio', 'Fixed_Hedge_Portfolio', 'Min_Variance_Hedge_Portfolio']],
                         title="Spot, Futures, and Portfolio Values")
    st.plotly_chart(fig_prices)

    st.subheader("Volatility Comparison")
    volatility_data = {name: calculate_volatility(calculate_returns(data[column])) for name, column in strategies.items()}
    fig_volatility = px.bar(x=list(volatility_data.keys()), y=list(volatility_data.values()),
                            title="Annualized Volatility Comparison", labels={'x': 'Strategy', 'y': 'Annualized Volatility'})
    st.plotly_chart(fig_volatility)

    st.subheader("Return Distribution")
    fig_returns_dist = go.Figure()
    for name, column in strategies.items():
        returns = calculate_returns(data[column])
        fig_returns_dist.add_trace(go.Histogram(x=returns, name=name, nbinsx=50))
    fig_returns_dist.update_layout(title="Return Distribution", xaxis_title="Daily Return", yaxis_title="Frequency")
    st.plotly_chart(fig_returns_dist)

    st.subheader("Cumulative Return")
    cumulative_returns_data = pd.DataFrame()
    for name, column in strategies.items():
        cumulative_returns_data[name] = (1 + calculate_returns(data[column])).cumprod()
    fig_cumulative_returns = px.line(cumulative_returns_data, title="Cumulative Return")
    st.plotly_chart(fig_cumulative_returns)

    # Optional: Rolling Volatility Chart
    st.subheader("Rolling Volatility (30-day window)")
    rolling_volatility_data = pd.DataFrame()
    window = 30
    for name, column in strategies.items():
        returns = calculate_returns(data[column])
        rolling_volatility_data[name] = returns.rolling(window=window).std() * np.sqrt(252)
    fig_rolling_volatility = px.line(rolling_volatility_data, title=f"Rolling Volatility ({window}-day window)")
    st.plotly_chart(fig_rolling_volatility)

    # Optional: Risk vs. Return Scatter Plot
    st.subheader("Risk vs. Return")
    risk_return_data = {}
    for name, column in strategies.items():
        returns = calculate_returns(data[column])
        risk_return_data[name] = {
            'Annualized Return': (data[column].iloc[-1] / data[column].iloc[0] - 1) * 100,
            'Annualized Volatility': calculate_volatility(returns)
        }
    risk_return_df = pd.DataFrame.from_dict(risk_return_data, orient='index')
    fig_risk_return = px.scatter(risk_return_df, x='Annualized Volatility', y='Annualized Return',
                                 text=risk_return_df.index, title="Risk vs. Return")
    fig_risk_return.update_traces(textposition='top center')
    st.plotly_chart(fig_risk_return)

else:
    st.info("Please ensure 'PSOYBUSDM.xlsx' and 'Soybean_contract.xlsx' are in the same directory as the script.")