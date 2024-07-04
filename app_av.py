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
import dash_mantine_components as dmc


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
                        dbc.Button("Add Entry", id="add-event-button",  className="me-4", color='info', style={'border': '2px solid white'}))],
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
                                ]),
                                dbc.Col([
                                    dbc.Label('End Date', className="me-1"),
                                    dcc.DatePickerSingle(id='end-date-picker', date=datetime.now().date(), placeholder='Select a date',
                                                         display_format='YYYY-MM-DD', className="mb-3"),
                                ]),
                            ]),
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
], fluid=True)


#############
# Callbacks
############

@app.callback(
    [Output('modal-add-event', 'is_open'),
     Output('person-name-input', 'invalid')],
    [Input('add-event-button', 'n_clicks'),
     Input('close-add-event-modal-button', 'n_clicks'),
     Input('submit-event-button', 'n_clicks')],
    [State('modal-add-event', 'is_open'),
     State('person-name-input', 'value')]
)
def toggle_modal_add_event(add_event_btn_clicks, close_btn_clicks, submit_btn_clicks, is_open, person_name):
    ctx = callback_context
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'add-event-button':
            return True, False  # Open modal and reset validation
        elif button_id in ['close-add-event-modal-button', 'submit-event-button']:
            if button_id == 'submit-event-button' and not person_name:
                return is_open, True  # Keep modal open and highlight input for missing name
            return False, False  # Close modal and reset validation
    return is_open, False


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
        if end_date != 'No End Date':
            end_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        place = clicked_event.get('extendedProps', {}).get('context', 'No Place').upper()

        header = f"Event Details: {event_title}"
        body = [
            html.P(f"Start: {start_date}"),
            html.P(f"End: {end_date}"),
            html.P(f"Place: {place}"),
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
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date'),
     State('event-type-dropdown', 'value'),
     State('full-calendar', 'events'),
     State('full-calendar', 'clickedEvent')])
def manage_events(url, submit_btn_clicks, delete_btn_clicks, n_intervals, person_name, start_date, end_date, event_type, current_events, clicked_event):
    ctx = callback_context
    events_from_db = current_events or []  # Initialize events_from_db with current events or empty list

    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            if button_id == 'submit-event-button':
                if not person_name:
                    #return events_from_db, False, "", True, "Please enter a person's name."
                    # Do nothing if person_name is empty since the error is raised in the modal
                    return events_from_db, False, "", False, ""

                if person_name and start_date and event_type:
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

                events_from_db = load_events_from_db()  # load events
                #Show success alert, hide error alert
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
                #Show success alert, hide error alert
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
