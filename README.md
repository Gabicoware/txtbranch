
Runs on google app engine.

Dependencies:

  - [simpleauth][1]. An implementation of OAuth for google app engine
  - [python-oauth2][2]. (as a dependency of simpleauth)
  - [httplib2][3]. (as a dependency of python-oauth2)

Links:

  - App: http://txtbranch.gabicoware.com
  - Source code: https://github.com/gabicoware/txtbranch
  - iPhone Application: https://itunes.apple.com/nz/app/txtbranch/id880449244?mt=8

To setup:

  - copy secrets.template.py to secrets.py and modify as needed
  - copy config.template.json to config.json and modify as needed
  - copy app.template.yaml to app.yaml and modify as needed

Environments:

  - The makefile allows you to to have multiple environments.
  - To setup, copy app.yaml, config.json, and secrets.py to versions that begin with {environment}-, such as production-config.json
  - Usage: make install name="production" dest_folder="../txtbranch-production"
  - To deploy with tests: make install name="staging" dest_folder="../txtbranch-staging" test=1

[1]: https://github.com/crhym3/simpleauth
[2]: https://github.com/simplegeo/python-oauth2
[3]: http://code.google.com/p/httplib2/
