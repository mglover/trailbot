#TrailBot
##A Flask app 

TrailBot provides social features (status updates, chat, dms)
and access to various API and databases (weather, driving directions, 
dictionary, etc.) over SMS.

This code is currently operating via the Twilio Messaging API.

User documentation is at http://oldskooltrailgoods.com/trailbot.

### Files

config.py: local settings
core.py: library functions
dispatch.py: routing of commands and help requests
tb.py; main loop, authentication

netsource.py: base class for all internet API 
user.py: user database and user-attached storage aPI

runtests.py, tests/: unit test runner, test directory

group, help, location, nav, userui, word, wx: command implementations