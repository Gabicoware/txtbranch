prep:
	mkdir -p ${dest_folder}
	
install-staging: install-base
	cp -r tests ${dest_folder}
	cp gaeunit.py ${dest_folder}
	cp staging-app.yaml ${dest_folder}/app.yaml

install-production: install-base
	cp production-app.yaml ${dest_folder}/app.yaml

install-base: prep
	cp *.* ${dest_folder}
	cp -r httplib2 ${dest_folder}
	cp -r oauth2 ${dest_folder}
	cp -r simpleauth ${dest_folder}
	cp -r assets ${dest_folder}
	cp -r templates ${dest_folder}
	cp admin.py ${dest_folder}
	cp api.py ${dest_folder}
	cp branch-engine.py ${dest_folder}
	cp controllers.py ${dest_folder}
	cp defaulttext.py ${dest_folder}
	cp handlers.py ${dest_folder}
	cp mock.py ${dest_folder}
	cp models.py ${dest_folder}
	cp index.yaml ${dest_folder}
	
