import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Define colors
bull_css = 'rgba(255, 255, 255, 1)'
bull_avg_css = '#9598a1'
bear_css = '#ff1100'
bear_avg_css = '#9598a1'

# Define input parameters
length = 5
bull_ext_last = 3
bear_ext_last = 3
mitigation = 'Wick' #['Wick', 'Close']

# Define data
csv_path = "data/GBPUSD_3Y_H1_OHLCV.csv"
data = pd.read_csv(csv_path)
data['hl2'] = (data['high'] + data['low']) / 2

# Define functions
def get_coordinates(condition, top, btm, ob_val):
    ob_top = []
    ob_btm = []
    ob_avg = []
    ob_left = []

    ob = np.nan

    if condition.any():
        avg = (top + btm) / 2
        ob_top.insert(0, top)
        ob_btm.insert(0, btm)
        ob_avg.insert(0, avg)
        ob_left.insert(0, length)

        ob = ob_val

    return ob_top, ob_btm, ob_avg, ob_left, ob

def remove_mitigated(ob_top, ob_btm, ob_left, ob_avg, target, bull):
    mitigated = False
    target_array = ob_btm if bull else ob_top

    for element in target_array:
        idx = target_array.index(element)

        if ((bull and (target < element).any()) or (not bull and (target > element).any())):  # or .all(), depending on your needs
            mitigated = True

            del ob_top[idx]
            del ob_btm[idx]
            del ob_avg[idx]
            del ob_left[idx]

    return mitigated

def set_order_blocks(fig, ob_top, ob_btm, ob_left, ob_avg, ext_last, border_css, lvl_css):

    for i in range(min(ext_last, len(ob_top))):
        fig.add_shape(type="rect",
                      x0=ob_left[i], y0=ob_top[i], x1=ob_left[i] + 1, y1=ob_btm[i],
                      line=dict(color=border_css),
                      fillcolor="rgba(255, 255, 255, 0.3)"  # semi-transparent white
                    )

        fig.add_shape(type="rect",
                      x0=ob_left[i], y0=ob_avg[i], x1=ob_left[i] + 1, y1=ob_avg[i],
                      line=dict(color=border_css),
                      fillcolor="rgba(255, 255, 255, 0.3)"  # semi-transparent white
                      )

    return fig

def create_candlestick_chart(df: pd.DataFrame):
    # Load data
    df['time'] = pd.to_datetime(df['time'])
    # Filter out weekends
    df = df[df['time'].dt.dayofweek < 5]

    # Create figure
    fig = go.Figure()
    # Add candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=list(df.time),
            open=list(df.open),
            high=list(df.high),
            low=list(df.low),
            close=list(df.close)
        )
    )

    # Set title
    fig.update_layout(
        title_text="Candlestick Chart - GBPUSD",
        template="plotly_dark"
    )

    # Add range selector
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ]),
            bgcolor="#444",  # dark background color
            bordercolor="#444",  # dark border color
            font=dict(color="white")  # white font color                
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig

def add_blocks(fig, x0, x1, y0, y1):
    fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                fillcolor="rgba(255, 255, 255, 0.3)",  # semi-transparent white
                line=dict(color="rgba(255, 255, 255, 1)")  # fully opaque white
    )
    return fig

# Main logic
data['upper'] = data['high'].rolling(window=length).max()
data['lower'] = data['low'].rolling(window=length).min()

if mitigation == 'Close':
    data['target_bull'] = data['close'].rolling(window=length).min()
    data['target_bear'] = data['close'].rolling(window=length).max()
else:
    data['target_bull'] = data['lower']
    data['target_bear'] = data['upper']

data['os'] = np.where(data['high'].shift(length) > data['upper'], 0, np.where(data['low'].shift(length) < data['lower'], 1, np.nan))
data['os'].ffill(inplace=True)
data.dropna(subset = ['os'],inplace = True)
data['os'] = data['os'].astype(int)

data['phv'] = data['volume'].rolling(window=length * 2 + 1, center=True).max() == data['volume']
print("DF with cols computed:\n",data.tail()) #.iloc[:, -5:]

bull_top, bull_btm, bull_avg, bull_left, bull_ob = get_coordinates(data['phv'] & (data['os'] == 1), data['hl2'].shift(length), data['low'].shift(length), data['low'].shift(length))
bear_top, bear_btm, bear_avg, bear_left, bear_ob = get_coordinates(data['phv'] & (data['os'] == 0), data['high'].shift(length), data['hl2'].shift(length), data['high'].shift(length))

mitigated_bull = remove_mitigated(bull_top, bull_btm, bull_left, bull_avg, data['target_bull'].iloc[-1], True)
mitigated_bear = remove_mitigated(bear_top, bear_btm, bear_left, bear_avg, data['target_bear'].iloc[-1], False)

# Create a candlestick chart
fig = create_candlestick_chart(df = data)

# Set bullish order blocks
fig = set_order_blocks(fig, bull_top, bull_btm, bull_left, bull_avg, bull_ext_last, bull_css, bull_avg_css)

# Set bearish order blocks
fig = set_order_blocks(fig, bear_top, bear_btm, bear_left, bear_avg, bear_ext_last, bear_css, bear_avg_css)

fig = add_blocks(fig, x0="2023-10-30", x1="2023-11-15", y0=1.2122, y1=1.23250)

# Show the plot
fig.show()
               
