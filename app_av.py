import dash
from dash import dcc, html, Input, Output, State, callback_context
import full_calendar_component as fcc
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
import flask
from pymongo import MongoClient
from bson import ObjectId
from waitress import serve
from dotenv import load_dotenv
import os
import logging


load_dotenv()
mongo_host = os.environ.get('DB_HOST', 'localhost')
mongo_port = os.environ.get('DB_PORT')
mongo_db = os.environ.get('DB_NAME')
mongo_coll = os.environ.get('DB_COLL')
mongo_url = "mongodb://" + mongo_host + ":" + mongo_port

# Configure logging
logging.basicConfig(filename='av_logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mongo stuff
client = MongoClient(mongo_url)
db = client[mongo_db]
collection = db[mongo_coll]


server = flask.Flask(__name__)
app = dash.Dash(server=server, title='LST Onsite availability',
                update_title=None,
                suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.LUX, dbc.icons.BOOTSTRAP, dbc.icons.FONT_AWESOME],
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0, maximum-scale=1.5, minimum-scale=0.5'}],
                )


############
# Functions
############
def get_event_color(event_type):
    color_map = {
        'calp': '#002642',
        'orm': '#840032',
        'remote': '#e59500'
    }
    return color_map.get(event_type)


# Function to load events from MongoDB
def load_events_from_db():
    events = []
    for event in collection.find():
        event['_id'] = str(event['_id'])  # Convert ObjectId to string
        event['color'] = get_event_color(event['context'])  # Assign color based on context
        event['end'] = (datetime.strptime(event['end'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')  # Adjust end date for display, fullcalendar end date is exclusive!
        events.append(event)
    return events


# Initial load of events
initial_events = load_events_from_db()

##########
# Layout
#########
navbar = dbc.Navbar(
    dbc.Container(
        [html.H1("LST Onsite availability", style={'color': 'white', 'text-align': 'center', 'margin': 'auto', 'font-weight': 'bold'})],
    ),
    color='dark',
    dark=True,
    className='d-flex justify-content-center mb-4'
)

today = datetime.now()
formatted_date = today.strftime("%Y-%m-%d")  # Format the date

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=True),  # Hidden location component to detect page load
    navbar,
    dbc.Row([
        dbc.Col(
            fcc.FullCalendarComponent(
                id='full-calendar',
                initialDate=f'{formatted_date}',
                initialView='dayGridMonth',
                editable=True,
                selectable=True,
                headerToolbar={
                    'start': 'dayGridMonth dayGridWeek',
                    'center': 'title',  # Center-align the title in the header
                    'end': 'prev today next'
                },
                views={
                    'dayGridMonth': {
                        #'showNonCurrentDates': ,  # Hide/show the days of the previous and next month
                        'fixedWeekCount': False  # Display only the weeks in the current month
                    }
                },
                events=initial_events,  # Load initial events
            ),
            width=8,  # Adjust the width as needed
            className="mx-auto mb-4",  # Center the column and add bottom margin
        )
    ]),
    dbc.Row([
        dbc.Col(dbc.Button("Add Entry", id="add-event-button", color="primary"), width=8, className="mx-auto mb-4 justify-content-end")
    ], className="mb-4"),
    html.Div(id='event-details'),
    dbc.Modal(
        id='modal-add-event',
        #size='lg',
        children=[
            dbc.Card(
                [
                    dbc.CardHeader("New Entry"),
                    dbc.CardBody(
                        dbc.Form([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label('Person\'s Name'),
                                    dbc.Input(id='person-name-input', type='text', required=True, className="mb-3"),
                                ])
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label('Start Date', className="me-1"),
                                    dcc.DatePickerSingle(id='start-date-picker', date=datetime.now().date(), placeholder='Select a date',
                                                         display_format='YYYY-MM-DD', className="mb-3"),
                                ]),
                                dbc.Col([
                                    dbc.Label('End Date', className="me-1"),
                                    dcc.DatePickerSingle(id='end-date-picker', date=datetime.now().date(), placeholder='Select a date',
                                                         display_format='YYYY-MM-DD', className="mb-3"),
                                ]),
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label('Event Type'),
                                    dcc.Dropdown(
                                        id='event-type-dropdown',
                                        options=[
                                            {'label': 'CALP', 'value': 'calp'},
                                            {'label': 'ORM', 'value': 'orm'},
                                            {'label': 'Remote', 'value': 'remote'}
                                        ],
                                        value='calp',  # Default to Calp
                                        clearable=False,
                                        className="mb-3"
                                    ),
                                ])
                            ]),
                        ])
                    ),
                    dbc.CardFooter([
                        dbc.Button('Submit', id='submit-event-button', size='sm', color='primary', className='me-2'),
                        dbc.Button('Close', id='close-add-event-modal-button', size='sm', color='danger', className=''),
                    ], className='d-flex justify-content-end'),
                ]
            )
        ],
    ),
    dbc.Modal(
        id='event-modal',
        size='lg',
        children=[
            dbc.ModalHeader(id='event-modal-header'),
            dbc.ModalBody(id='event-modal-body'),
            dbc.ModalFooter([
                #dbc.Button('Edit', id='edit-event-modal-button', color='primary'),
                dbc.Button('Delete', id='delete-event-modal-button', color='danger'),
                dbc.Button('Close', id='close-event-modal-button', className='ml-auto'),
            ]),
        ]
    ),
    dbc.Alert(id='error-alert', color='danger', is_open=False),
], fluid=True)


#############
# Callbacks
############

@app.callback(Output('modal-add-event', 'is_open'),
              [Input('add-event-button', 'n_clicks'),
              Input('close-add-event-modal-button', 'n_clicks'),
              Input('submit-event-button', 'n_clicks')],
              [State('modal-add-event', 'is_open')],)
def toggle_modal_add_event(add_event_btn_clicks, close_btn_clicks, submit_btn_clicks, is_open):
    ctx = callback_context
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'add-event-button':
            return True
        elif button_id in ['close-add-event-modal-button', 'submit-event-button']:
            return False
    return is_open


@app.callback(Output('event-modal', 'is_open'),
              [Input('full-calendar', 'clickedEvent'),
               #Input('edit-event-modal-button', 'n_clicks'),
               Input('delete-event-modal-button', 'n_clicks'),
               Input('close-event-modal-button', 'n_clicks')],
              [State('event-modal', 'is_open')])
def toggle_event_modal(clicked_event, delete_btn_clicks, close_btn_clicks, is_open):
    ctx = callback_context
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id in ['delete-event-modal-button', 'close-event-modal-button']:  # 'edit-event-modal-button',
            return False
        elif clicked_event:
            return True
    return False


@app.callback([Output('event-modal-header', 'children'),
               Output('event-modal-body', 'children')],
              [Input('full-calendar', 'clickedEvent')])
def display_event_details_modal(clicked_event):
    if clicked_event is not None:
        event_title = clicked_event.get('title', 'No Title')
        start_date = clicked_event.get('start', 'No Start Date')
        end_date = clicked_event.get('end', 'No End Date')
        place = clicked_event.get('extendedProps', {}).get('context', 'No Place').upper()

        header = f"Event Details: {event_title}"
        body = [
            html.P(f"Start: {start_date}"),
            html.P(f"End: {end_date}"),
            html.P(f"Place: {place}"),
        ]

        return header, body

    return '', None


@app.callback([Output('full-calendar', 'events'),
               Output('error-alert', 'children'),
               Output('error-alert', 'is_open')],
              [Input('url', 'pathname'),  # Trigger loading events on page load
               Input('submit-event-button', 'n_clicks'),
               #Input('edit-event-modal-button', 'n_clicks'),
               Input('delete-event-modal-button', 'n_clicks')],
              [State('person-name-input', 'value'),
               State('start-date-picker', 'date'),
               State('end-date-picker', 'date'),
               State('event-type-dropdown', 'value'),
               State('full-calendar', 'events'),
               State('full-calendar', 'clickedEvent')])
def manage_events(url, submit_btn_clicks, delete_btn_clicks, person_name, start_date, end_date, event_type, current_events, clicked_event):
    ctx = callback_context
    events_from_db = current_events or []  # Initialize events_from_db with current events or empty list

    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            if button_id == 'submit-event-button':
                if person_name and start_date and end_date and event_type:
                    # Adjust end date for storage to be inclusive
                    adjusted_end_date = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                    # Add new event
                    new_event = {
                        "title": f"{person_name} - {event_type.upper()}",
                        "start": start_date,
                        "end": adjusted_end_date,
                        "color": get_event_color(event_type),
                        "context": event_type,
                    }
                    # Send to MongoDB
                    collection.insert_one(new_event)
                    logging.info(f"Event added: {new_event}")
                else:
                    # Show an error message if person_name is empty
                    return events_from_db, "Please enter a person's name.", True
            elif button_id == 'delete-event-modal-button' and clicked_event:
                # Delete existing event from mongo and retrieve event details before deleting
                event_id = clicked_event['extendedProps']['_id']
                event_title = clicked_event['title']
                event_start = clicked_event['start']
                event_end = clicked_event.get('end', event_start)  # Use start date if end date is not set
                collection.delete_one({"_id": ObjectId(event_id)})
                logging.info(f"Event deleted: ID={event_id}, Title={event_title}, Start={event_start}, End={event_end}")

            # Retrieve updated events from MongoDB
            events_from_db = load_events_from_db()
            return events_from_db, "", False  # Clear the alert message and close the alert if successful

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            #return events_from_db, f"An error occurred: {str(e)}", True  # Show the error alert with the error message

    # Default return: Load events when URL changes (page load/refresh)
    events_from_db = load_events_from_db()
    return events_from_db, "", False


if __name__ == '__main__':
    serve(app.server, host='0.0.0.0', port=5016, threads=100, _quiet=True)
