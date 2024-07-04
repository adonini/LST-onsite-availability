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
from dash_mantine_components import MantineProvider
import dash_mantine_components as dmc

# to be compatible with mantine components
os.environ["REACT_VERSION"] = "18.2.0"

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
                external_stylesheets=[dbc.themes.LUX, dbc.icons.BOOTSTRAP, dbc.icons.FONT_AWESOME, "https://unpkg.com/@mantine/dates@7/styles.css"],
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
        events.append(event)
    return events


# Initial load of events
initial_events = load_events_from_db()

##########
# Layout
#########
# navbar = dbc.Navbar(
#     dbc.Container(
#         [html.H1("LST Onsite availability", style={'color': 'white', 'text-align': 'center', 'margin': 'auto', 'font-weight': 'bold'})],
#     ),
#     color='dark',
#     dark=True,
#     className='d-flex justify-content-center mb-4'
# )
navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col(
                dbc.Nav([
                    dbc.NavItem(
                        dbc.Button("Add Entry", id="add-event-button",  className="me-4 fs-4 btn-sm", color='info', style={'border': '2px solid white'}))],
                        className="me-4"),
                xs=2, lg=4,
            ),
            dbc.Col(
                html.H1("LST Onsite availability", style={'color': 'white', 'text-align': 'center', 'font-weight': 'bold'}),
                width="auto",
                className="position-absolute top-40 start-50 translate-middle-x"
            ),
        ],
        align="center")],
    fluid=True),
    color="dark",
    #dark=True,
    className="d-flex justify-content-center mb-4",
)


today = datetime.now()
formatted_date = today.strftime("%Y-%m-%d")  # Format the date

app.layout = MantineProvider(
    dbc.Container([
        dcc.Location(id='url', refresh=True),
        navbar,
        dcc.Interval(
            id='interval-component',
            interval=10 * 1000,  # Update every 10 seconds
            n_intervals=0
        ),
        dbc.Alert(id='success-alert', color='success', dismissable=True, duration=3000, is_open=False),
        dbc.Alert(id='error-alert', color='danger', dismissable=True, duration=3000, is_open=False),
        dbc.Row([
            dbc.Col(
                fcc.FullCalendarComponent(
                    id='full-calendar',
                    initialDate=f'{formatted_date}',
                    initialView='dayGridMonth',
                    editable=True,
                    selectable=True,
                    headerToolbar={
                        'start': 'dayGridMonth timeGridWeek',
                        'center': 'title',
                        'end': 'prev today next'
                    },
                    views={
                        'dayGridMonth': {
                            'fixedWeekCount': False
                        },
                        'timeGridWeek': {
                            'type': 'timeGrid',
                            'slotMinTime': '06:00:00',  # Minimum time on the axis (6 AM)
                            'slotMaxTime': '21:00:00',  # Maximum time on the axis (9 PM)
                        },
                    },
                    events=initial_events,
                ),
                xs=12,
                lg=10,
                className="mx-auto mb-4",
            )
        ]),
        html.Div(id='event-details'),
        dbc.Modal(
            id='modal-add-event',
            children=[dbc.Card([
                dbc.CardHeader("New Entry"),
                dbc.CardBody(
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Person's Name"),
                                dbc.Input(id='person-name-input', type='text', required=True, className="mb-3"),
                                dbc.FormFeedback("Please provide your name.", type="invalid"),
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label('Start Date'),
                                dmc.DatePicker(
                                    id='start-date-picker',
                                    #label='Start Date',
                                    value=datetime.now().date(),
                                    placeholder='Select a date',
                                    valueFormat='DD-MM-YYYY',
                                    className="mb-3",
                                    popoverProps={'zIndex': 10000, 'withinPortal': True},
                                ),
                            ], width=6),
                            dbc.Col([
                                dbc.Label('End Date'),
                                dmc.DatePicker(
                                    id='end-date-picker',
                                    #label='End Date',
                                    value=datetime.now().date(),
                                    placeholder='Select a date',
                                    valueFormat='DD-MM-YYYY',
                                    className="mb-3",
                                    popoverProps={'zIndex': 10000, 'withinPortal': True},
                                ),
                            ], width=6),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Checkbox(
                                    id='full-day-checkbox',
                                    label='Full Day',
                                    value=True,
                                    className="mb-3"
                                ),
                            ])
                        ]),
                        dbc.Row(
                            id='time-picker-row',
                            children=[
                                dbc.Col([
                                    dbc.Label('Start Time'),
                                    dmc.TimeInput(id='start-time-picker', className="mb-3"),
                                ]),
                                dbc.Col([
                                    dbc.Label('End Time'),
                                    dmc.TimeInput(id='end-time-picker', className="mb-3"),
                                ]),
                            ],
                            style={'display': 'none'}
                        ),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label('Location'),
                                dcc.Dropdown(
                                    id='event-type-dropdown',
                                    options=[
                                        {'label': 'CALP', 'value': 'calp'},
                                        {'label': 'ORM', 'value': 'orm'},
                                        {'label': 'Remote', 'value': 'remote'}
                                    ],
                                    value='calp',
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
            ])
        ]),
        dbc.Modal(
            id='event-modal',
            size='lg',
            children=[
                dbc.ModalHeader(id='event-modal-header'),
                dbc.ModalBody(id='event-modal-body'),
                dbc.ModalFooter([
                    dbc.Button('Delete', id='delete-event-modal-button', color='danger'),
                    dbc.Button('Close', id='close-event-modal-button', className='ml-auto'),
                ]),
            ]
        ),
    ], fluid=True)
)


#############
# Callbacks
############

# Toggle time pickers based on checkbox value
@app.callback(
    Output('time-picker-row', 'style'),
    [Input('full-day-checkbox', 'value')]
)
def toggle_time_pickers(is_full_day):
    if is_full_day:
        return {'display': 'none'}
    return {'display': 'flex'}


@app.callback(
    [Output('modal-add-event', 'is_open'),
     Output('person-name-input', 'invalid'),
     Output('start-time-picker', 'error'),
     Output('end-time-picker', 'error'),
     Output('person-name-input', 'value'),
     Output('start-date-picker', 'value'),
     Output('end-date-picker', 'value'),
     Output('start-time-picker', 'value'),
     Output('end-time-picker', 'value'),
     Output('full-day-checkbox', 'value'),
     Output('event-type-dropdown', 'value'),],
    [Input('add-event-button', 'n_clicks'),
     Input('close-add-event-modal-button', 'n_clicks'),
     Input('submit-event-button', 'n_clicks')],
    [State('modal-add-event', 'is_open'),
     State('person-name-input', 'value'),
     State('start-date-picker', 'value'),
     State('end-date-picker', 'value'),
     State('start-time-picker', 'value'),
     State('end-time-picker', 'value'),
     State('full-day-checkbox', 'value'),
     State('event-type-dropdown', 'value')]
)
def toggle_modal_add_event(add_event_btn_clicks, close_btn_clicks, submit_btn_clicks, is_open, person_name, start_date, end_date, start_time, end_time, is_full_day, type):
    ctx = callback_context
    reset_input_values = [None, datetime.now().date(), datetime.now().date(), None, None, True, 'calp']
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if button_id == 'add-event-button':
            return [True, False, False, False] + reset_input_values  # Open modal and reset all inputs

        elif button_id == 'close-add-event-modal-button':
            return [False, False, False, False] + reset_input_values  # Close modal and reset all inputs

        elif button_id == 'submit-event-button':
            person_name_invalid = False
            start_time_error = False
            end_time_error = False

            if not person_name:
                person_name_invalid = True  # Highlight input for missing name

            # Check for time errors only if it's not a full-day event
            if not is_full_day:
                if not start_time or not end_time:
                    start_time_error = "Plese provide a time"
                    end_time_error = "Plese provide a time"

            # If all validations pass, close the modal
            if not person_name_invalid and not start_time_error and not end_time_error:
                return [False, False, False, False] + reset_input_values  # Close modal and reset all validation

            return is_open, person_name_invalid, start_time_error, end_time_error, person_name, start_date, end_date, start_time, end_time, is_full_day, type

    return [is_open, False, False, False] + reset_input_values


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


@app.callback(
    [Output('event-modal-header', 'children'),
     Output('event-modal-body', 'children')],
    [Input('full-calendar', 'clickedEvent')])
def display_event_details_modal(clicked_event):
    if clicked_event is not None:
        event_title = clicked_event.get('title', 'No Title')
        start_date = clicked_event.get('start', 'No Start Date')
        end_date = clicked_event.get('end', 'No End Date')

        try:
            parsed_start_datetime = datetime.fromisoformat(start_date)
        except ValueError as e:
            logging.error(f"Error parsing start date: {e}")
            parsed_start_datetime = None
        try:
            parsed_end_datetime = datetime.fromisoformat(end_date) if end_date and end_date != 'No End Date' else parsed_start_datetime
            if parsed_end_datetime and 'T' not in end_date and parsed_end_datetime != parsed_start_datetime:
                adjusted_end_datetime = parsed_end_datetime - timedelta(days=1)
            else:
                adjusted_end_datetime = parsed_end_datetime
        except ValueError as e:
            logging.error(f"Error parsing end date: {e}")
            parsed_end_datetime = None
            adjusted_end_datetime = None

        is_full_day = 'T' not in start_date and (not end_date or 'T' not in end_date)  # Determine if it's a full-day event
        print(parsed_start_datetime)
        print(parsed_end_datetime)
        print(adjusted_end_datetime)
        place = clicked_event.get('extendedProps', {}).get('context', 'No Place').upper()
        header = f"Entry Details: {event_title}"

        if is_full_day:
            body = [
                html.P([html.B("Start: "), parsed_start_datetime.strftime('%Y-%m-%d')]),
                html.P([html.B("End: "), adjusted_end_datetime.strftime('%Y-%m-%d') if adjusted_end_datetime else "No End Date"]),
                html.P([html.B("Place: "), place])
            ]
        else:
            body = [
                html.P([html.B("Start: "), parsed_start_datetime.strftime('%Y-%m-%d %H:%M:%S')]),
                html.P([html.B("End: "), parsed_end_datetime.strftime('%Y-%m-%d %H:%M:%S') if parsed_end_datetime else "No End Date"]),
                html.P([html.B("Place: "), place])
            ]
        return header, body
    return '', None


@app.callback(
    [Output('full-calendar', 'events'),
     Output('success-alert', 'is_open'),
     Output('success-alert', 'children'),
     Output('error-alert', 'is_open'),
     Output('error-alert', 'children')],
    [Input('url', 'pathname'),  # Trigger loading events on page load
     Input('submit-event-button', 'n_clicks'),
     Input('delete-event-modal-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('person-name-input', 'value'),
     State('start-date-picker', 'value'),
     State('end-date-picker', 'value'),
     State('full-day-checkbox', 'value'),
     State('start-time-picker', 'value'),
     State('end-time-picker', 'value'),
     State('event-type-dropdown', 'value'),
     State('full-calendar', 'events'),
     State('full-calendar', 'clickedEvent')]
)
def manage_events(url, submit_btn_clicks, delete_btn_clicks, n_intervals, person_name, start_date, end_date, is_full_day, start_time, end_time, event_type, current_events, clicked_event):
    ctx = callback_context
    events_from_db = current_events or []  # Initialize events_from_db with current events or empty list
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            if button_id == 'submit-event-button':
                if not person_name:
                    # Do nothing if person_name is empty since the error is raised in the modal
                    return events_from_db, False, "", False, ""

                if person_name and start_date and event_type:
                    # Adjust end date for storage to be inclusive
                    adjusted_end_date = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                    if not is_full_day:
                        if start_time and end_time:
                            start_datetime = f"{start_date}T{start_time}"
                            end_datetime = f"{end_date}T{end_time}"
                        else:
                            # Handle cases where times are not provided
                            return events_from_db, False, "", False, ""
                    else:
                        start_datetime = start_date
                        end_datetime = adjusted_end_date

                    # Add new event
                    new_event = {
                        "title": f"{person_name} - {event_type.upper()}",
                        "start": start_datetime,
                        "end": end_datetime,
                        "color": get_event_color(event_type),
                        "context": event_type,
                    }
                    # Send to MongoDB
                    collection.insert_one(new_event)
                    logging.info(f"Event added: {new_event}")
                events_from_db = load_events_from_db()  # load events
                # Show success alert, hide error alert
                return events_from_db, True, "Entry added successfully.", False, ""

            elif button_id == 'delete-event-modal-button' and clicked_event:
                # Delete existing event from mongo and retrieve event details before deleting
                event_id = clicked_event['extendedProps']['_id']
                event_title = clicked_event['title']
                event_start = clicked_event['start']
                event_end = clicked_event.get('end', event_start)  # Use start date if end date is not set
                collection.delete_one({"_id": ObjectId(event_id)})
                logging.info(f"Event deleted: ID={event_id}, Title={event_title}, Start={event_start}, End={event_end}")

                events_from_db = load_events_from_db()  # load events
                # Show success alert, hide error alert
                return events_from_db, True, "Entry deleted successfully.", False, ""

            else:
                events_from_db = load_events_from_db()
                return events_from_db, False, "", False, ""

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            # Return events without updating if there is an error
            return events_from_db, False, "", True, "An error occurred."

    # Default return: Load events when URL changes (page load/refresh)
    events_from_db = load_events_from_db()
    return events_from_db, False, "", False, ""


if __name__ == '__main__':
    serve(app.server, host='0.0.0.0', port=5016, threads=100, _quiet=True)
