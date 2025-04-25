import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.title("Soybean Hedging Strategy Comparison Dashboard")

uploaded_file = st.file_uploader("Upload Historical Price Data (CSV file with 'Date', 'Spot_Price', 'Futures_Near_M1', 'Futures_Near_M2', ... columns)", type="csv")

col1, col2 = st.columns(2)
start_date = col1.date_input("Start Date:", datetime(2020, 1, 1))
end_date = col2.date_input("End Date:", datetime.now().date())

fixed_hedge_ratio = st.slider("Fixed Hedge Ratio:", 0.0, 1.0, 0.5, 0.01)
confidence_level = st.slider("VaR/CVaR Confidence Level:", 0.8, 0.99, 0.95, 0.01)
rolling_window = st.slider("Rolling Window for Min Variance (days):", 20, 252, 63)

# Widget for selecting the futures contract maturity for basis risk
futures_maturity_column = st.selectbox(
    "Select Futures Contract Column for Basis Risk Analysis:",
    ["Futures_Near_M1", "Futures_Near_M2"]  # Initial options, will be updated from the file
)

if st.button("Run Analysis"):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if 'Date' not in df.columns or 'Spot_Price' not in df.columns or 'Futures_Near_M1' not in df.columns:
                st.error("CSV must have 'Date', 'Spot_Price', and at least one 'Futures_Near_Mx' column.")
            else:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                data = df[start_date:end_date].copy()

                # Update futures maturity options based on available columns
                futures_columns = [col for col in data.columns if col.startswith('Futures_Near_')]
                if futures_columns:
                    futures_maturity_column = st.selectbox(
                        "Select Futures Contract Column for Basis Risk Analysis:",
                        futures_columns,
                        index=0 if "Futures_Near_M2" in futures_columns else 0 # Default selection
                    )

                if not data.empty:
                    spot_prices = data['Spot_Price']
                    futures_prices_near = data['Futures_Near_M1'] # Default near-term futures
                    futures_prices_basis = data[futures_maturity_column] if futures_maturity_column in data.columns else futures_prices_near

                    portfolio_values = pd.DataFrame(index=spot_prices.index)
                    portfolio_values['No_Hedge'] = spot_prices
                    portfolio_values['Fixed_Ratio_Hedge'] = spot_prices - fixed_hedge_ratio * (futures_prices_near - futures_prices_near.iloc[0])
                    portfolio_values['Naive_Hedge'] = spot_prices - 1 * (futures_prices_near - futures_prices_near.iloc[0])

                    # Minimum Variance Hedge Calculation
                    hedge_ratio_mv = pd.Series(index=spot_prices.index)
                    for i in range(rolling_window, len(spot_prices)):
                        spot_window = spot_prices[i - rolling_window:i]
                        futures_window = futures_prices_near[i - rolling_window:i]
                        if spot_window.std() > 0 and futures_window.std() > 0:
                            covariance = np.cov(spot_window, futures_window)[0, 1]
                            variance_futures = np.var(futures_window)
                            hedge_ratio_mv.iloc[i] = covariance / variance_futures if variance_futures > 0 else 0
                        else:
                            hedge_ratio_mv.iloc[i] = 0
                    hedge_ratio_mv = hedge_ratio_mv.fillna(method='ffill').fillna(0) # Forward fill NaNs

                    portfolio_values['Min_Variance_Hedge'] = spot_prices - hedge_ratio_mv * (futures_prices_near - futures_prices_near.iloc[0])

                    # Basis Risk Hedge
                    portfolio_values['Basis_Risk_Hedge'] = spot_prices - 1 * (futures_prices_basis - futures_prices_basis.iloc[0])

                    performance = {}
                    for col in portfolio_values.columns:
                        returns = portfolio_values[col].pct_change().dropna()
                        if not returns.empty:
                            var_level = 1 - confidence_level
                            var = returns.quantile(var_level)
                            cvar = returns[returns <= var].mean()

                            # Simplified Cost of Hedging (assuming daily roll and a small cost)
                            cost_of_hedging_near = np.abs((futures_prices_near - futures_prices_near.shift(1)).dropna()).mean()
                            cost_of_hedging_basis = np.abs((futures_prices_basis - futures_prices_basis.shift(1)).dropna()).mean()

                            cost = 0
                            if col == 'Fixed_Ratio_Hedge':
                                cost = cost_of_hedging_near * fixed_hedge_ratio
                            elif col == 'Naive_Hedge':
                                cost = cost_of_hedging_near * 1
                            elif col == 'Min_Variance_Hedge':
                                cost = (hedge_ratio_mv.abs() * (futures_prices_near - futures_prices_near.shift(1)).abs()).mean()
                            elif col == 'Basis_Risk_Hedge':
                                cost = cost_of_hedging_basis * 1

                            performance[col] = {
                                'Cumulative Return': (1 + returns).cumprod().iloc[-1] - 1,
                                'Annual Volatility': returns.std() * np.sqrt(252),
                                'VaR': var,
                                'CVaR': cvar,
                                'Cost of Hedging (Est.)': cost if col != 'No_Hedge' else 0
                            }
                        else:
                            performance[col] = {
                                'Cumulative Return': np.nan,
                                'Annual Volatility': np.nan,
                                'VaR': np.nan,
                                'CVaR': np.nan,
                                'Cost of Hedging (Est.)': np.nan
                            }

                    performance_df = pd.DataFrame.from_dict(performance, orient='index')
                    st.dataframe(performance_df)

                    fig_prices = go.Figure()
                    for col in portfolio_values.columns:
                        fig_prices.add_trace(go.Scatter(x=portfolio_values.index, y=portfolio_values[col], mode='lines', name=col))
                    fig_prices.update_layout(title='Price Series Comparison', xaxis_title='Date', yaxis_title='Price')
                    st.plotly_chart(fig_prices)

                    fig_volatility = go.Figure(data=[go.Bar(x=performance_df.index, y=performance_df['Annual Volatility'])])
                    fig_volatility.update_layout(title='Annual Volatility', xaxis_title='Strategy', yaxis_title='Volatility')
                    st.plotly_chart(fig_volatility)

                    st.subheader("Risk Metrics")
                    st.write(f"Confidence Level for VaR/CVaR: {confidence_level:.2f}")

                else:
                    st.warning("No data available for the selected date range.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please upload a CSV file.")