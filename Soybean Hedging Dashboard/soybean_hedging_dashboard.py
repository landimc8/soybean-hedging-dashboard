# soybean_hedging_dashboard_streamlit.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.title("Soybean Hedging Strategy Comparison Dashboard")

uploaded_file = st.file_uploader("Upload Historical Price Data (CSV file)", type="csv")

col1, col2 = st.columns(2)
start_date = col1.date_input("Start Date:", datetime(2020, 1, 1))
end_date = col2.date_input("End Date:", datetime.now().date())

fixed_hedge_ratio = st.slider("Fixed Hedge Ratio:", 0.0, 1.0, 0.5, 0.01)

if st.button("Run Analysis"):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if 'Date' not in df.columns or 'Spot_Price' not in df.columns or 'Futures_Price_Near' not in df.columns:
                st.error("CSV must have 'Date', 'Spot_Price', 'Futures_Price_Near' columns.")
            else:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                data = df[start_date:end_date].copy()

                if not data.empty:
                    spot_prices = data['Spot_Price']
                    futures_prices = data['Futures_Price_Near']

                    portfolio_values = pd.DataFrame(index=spot_prices.index)
                    portfolio_values['No_Hedge'] = spot_prices
                    portfolio_values['Fixed_Ratio_Hedge'] = spot_prices - fixed_hedge_ratio * (futures_prices - futures_prices.iloc[0])
                    portfolio_values['Naive_Hedge'] = spot_prices - 1 * (futures_prices - futures_prices.iloc[0])

                    performance = {}
                    for col in portfolio_values.columns:
                        returns = portfolio_values[col].pct_change().dropna()
                        if not returns.empty:
                            performance[col] = {
                                'Cumulative Return': (1 + returns).cumprod().iloc[-1] - 1,
                                'Annual Volatility': returns.std() * np.sqrt(252)
                            }
                        else:
                            performance[col] = {'Cumulative Return': np.nan, 'Annual Volatility': np.nan}

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
                else:
                    st.warning("No data available for the selected date range.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please upload a CSV file.")