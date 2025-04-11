import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
import plotly.graph_objects as go
import os
import base64
import io

# Dash app setup
app = dash.Dash(__name__)

# Directory with CSVs
CSV_DIR = './'  # Replace with your directory of CSV files

def get_csv_files():
    return [f for f in os.listdir(CSV_DIR) if f.endswith('.csv')]

def read_csv(file_name):
    file_path = os.path.join(CSV_DIR, file_name)
    df = pd.read_csv(file_path)
    df['Date_Time'] = pd.to_datetime(df['Date_Time'], format='%Y%m%d %H:%M:%S.%f')
    return df

# Layout
app.layout = html.Div([
    html.H1("Time-Series Pressure and Sizing Data"),

    html.Label("Select CSV File:"),
    dcc.Dropdown(
        id='csv-selector',
        options=[{'label': f, 'value': f} for f in get_csv_files()],
        value=get_csv_files()[0] if get_csv_files() else None
    ),

    html.Br(),

    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select a CSV File')]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),

    html.Label("Show Sizing Trace:"),
    dcc.Checklist(
        id='sizing-toggle',
        options=[{'label': 'Include Sizing', 'value': 'show_sizing'}],
        value=['show_sizing']
    ),

    dcc.RangeSlider(
        id='time-range',
        step=1,
        marks=None,
        tooltip={"placement": "bottom", "always_visible": True}
    ),

    dcc.Graph(id='timeseries-plot'),

    dcc.Store(id='stored-data'),
    dcc.Store(id='selected-filename')
])

@app.callback(
    Output('stored-data', 'data'),
    Output('selected-filename', 'data'),
    Output('time-range', 'min'),
    Output('time-range', 'max'),
    Output('time-range', 'value'),
    Input('csv-selector', 'value'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def load_csv(file_name, uploaded_contents, uploaded_filename):
    ctx = dash.callback_context

    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'upload-data' and uploaded_contents:
        content_type, content_string = uploaded_contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        df['Date_Time'] = pd.to_datetime(df['Date_Time'], format='%Y%m%d %H:%M:%S.%f')
        file_name = uploaded_filename
    elif trigger_id == 'csv-selector' and file_name:
        df = read_csv(file_name)
    else:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    min_ts = df['Date_Time'].min().timestamp()
    max_ts = df['Date_Time'].max().timestamp()
    if min_ts >= max_ts:
        max_ts = min_ts + 1

    return df.to_json(date_format='iso'), file_name, min_ts, max_ts, [min_ts, max_ts]

@app.callback(
    Output('timeseries-plot', 'figure'),
    Input('stored-data', 'data'),
    Input('time-range', 'value'),
    Input('selected-filename', 'data'),
    Input('sizing-toggle', 'value')
)
def update_graph(data, time_range, file_name, sizing_toggle):
    if data is None or time_range is None:
        return go.Figure()

    df = pd.read_json(data)
    start_time, end_time = pd.to_datetime(time_range, unit='s')
    filtered_df = df[(df['Date_Time'] >= start_time) & (df['Date_Time'] <= end_time)]

    fig = go.Figure()

    # Sizing trace first to appear behind others if toggled on
    if 'show_sizing' in sizing_toggle:
        fig.add_trace(go.Scatter(
            x=filtered_df['Date_Time'],
            y=filtered_df['Droplet Dia From Area [um]'],
            mode='markers',
            name='Sizing',
            yaxis='y2',
            opacity=0.5,
            marker=dict(size=6, color='lightgreen')
        ))

    fig.add_trace(go.Scatter(x=filtered_df['Date_Time'], y=filtered_df['AQ Press [mbar]'], mode='lines', name='AQ Pressure', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=filtered_df['Date_Time'], y=filtered_df['Oil Press [mbar]'], mode='lines', name='Oil Pressure', line=dict(color='red')))

    fig.update_layout(
        title=f'Pressure and Sizing Over Time ({file_name})',
        xaxis_title='Datetime',
        yaxis=dict(title='Pressure'),
        yaxis2=dict(title='Sizing', overlaying='y', side='right', showgrid=False)
    )

    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
