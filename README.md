# LST-onsite-availability

The repo contains two application to store and show onsite availability of people.
The first application is in dash and stores the info in a Mongo Database.

The second is a Djano app and has implemented a login system.

## Django app



## Dash app

### MongoDB

To start the container: `docker-compose up -d`

To stop the container: `docker-compose down`

The option `-d` detach the docker-compose, so that the container is being run in the background.

To list the running containers: `docker ps`.

To enter inside the Mongo container and run an interactive shell: `docker exec -it mongodb-av bash`.

### Logs

In the log file of the dash app is possible to find records of any delete/add action on the calendar.