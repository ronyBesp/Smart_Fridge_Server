# SmartFridge_Server
Django Python server for Smart Fridge Project.

By default, both the iOS App and Pi repo's are configured to point to the live server.
This repo contains the Django Python code of the server and can be configured to run locally.


Other repos for the project are:


**Pi**:

**App**:


To run install the following frameworks:
- pip install django
- pip install djangorestframework

Additional frameworks to install are detailed in the Final Report document.


By default the code included runs on the server. The server URL is seen in the code.

This can be changed to run locally but if it is to run locally the local server URL must be put in place of the current server URL.


## If running locally (must change server path everywhere throughout code):
Before running locally you need to create a local SQLite database.


This can be created by cd'ing into the smartfridge folder and running:
```
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

This will create the local SQLite database.


To run the local server cd into smartfridge and run 'python manage.py runserver'
The local server will be accessible through 127.0.0.1:8000

Debug is on so you will see debug information throughout the server

Configured Endpoints:
- 127.0.0.1:8000/admin -> can use to log in as admin and manage the API
- 127.0.0.1:8000/api -> Fridge Contents API configured here

Images will be uploaded to to uploads folder -> all images under the user folder
