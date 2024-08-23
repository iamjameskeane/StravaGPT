import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def create_route_plot(lnglat_data, mapbox_access_token, zoom, output_file='route_map.jpg'):
    """
    Plot a route based on a stream of longitude and latitude data.
    
    Parameters:
    lnglat_data: list of tuples
        A list of (latitude, longitude) tuples.
    mapbox_access_token: str
        Your Mapbox access token.
    output_file: str
        The path and file name to save the output image.
    """
    
    # Check if the data is empty
    if not lnglat_data:
        raise ValueError("The lnglat_data list is empty.")
    
    coords = lnglat_data.data

    # Convert the input data to a DataFrame
    df = pd.DataFrame(coords, columns=['lat', 'lng'])
    
    # Create the Plotly map
    fig = px.line_mapbox(
        df,
        lat='lat',
        lon='lng',
        zoom=zoom,
        center={'lat': df['lat'].mean(), 'lon': df['lng'].mean()},
    )
    
    fig.update_layout(mapbox_style="streets", mapbox_accesstoken=mapbox_access_token)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    
    # Save the map as a static image
    fig.write_image(output_file, format='png')
    
    return output_file

def plot_heart_rate_and_altitude(time_stream, heart_rate_stream, altitude_stream=None, output_file='heart_rate_altitude_plot.jpg'):
    """
    Plot heart rate and altitude data based on separate streams of timestamp, heart rate, and optionally altitude data.
    
    Parameters:
    time_stream: Stream Object
        A Stream object containing timestamps in seconds.
    heart_rate_stream: Stream Object
        A Stream object containing heart rate values.
    altitude_stream: Stream Object, optional
        A Stream object containing altitude values.
    output_file: str
        The path and file name to save the output image.
    """
    
    # Check if data streams are all of the same length
    if altitude_stream is not None and not (len(time_stream.data) == len(heart_rate_stream.data) == len(altitude_stream.data)):
        raise ValueError("All data streams must be of the same length.")
    
    # Convert time to timedelta for better flexibility
    df = pd.DataFrame({
        'time': pd.to_timedelta(time_stream.data, unit='s'),
        'heart_rate': heart_rate_stream.data
    })
    
    if altitude_stream is not None:
        df['altitude'] = altitude_stream.data

    # Create the Plotly figure
    fig = go.Figure()

    # Add altitude data as a filled area plot if provided
    if altitude_stream is not None:
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['altitude'],
            fill='tozeroy',
            name='Altitude',
            mode='none',
            fillcolor='rgba(173, 216, 230, 0.5)',  # Light blue color with transparency
            yaxis='y2'
        ))

    # Add heart rate data as a line plot
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['heart_rate'],
        mode='lines',
        name='Heart Rate',
        line=dict(color='red')
    ))

    # Update layout for the figure
    layout_updates = {
        'title': 'Heart Rate Over Time' if altitude_stream is None else 'Heart Rate and Altitude Over Time',
        'xaxis_title': 'Time',
        'yaxis_title': 'Heart Rate (bpm)',
        'template': 'plotly_white',
        'legend': dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.8)')
    }
    
    if altitude_stream is not None:
        layout_updates['yaxis2'] = dict(
            title='Altitude (m)',
            overlaying='y',
            side='right'
        )
        
    fig.update_layout(**layout_updates)

    # Save the plot as a static image
    fig.write_image(output_file, format='png')

    return output_file