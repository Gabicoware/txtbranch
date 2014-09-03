TESTING := $(test)

install:
	
	mkdir -p ${dest_folder}
	
ifeq ($(TESTING), 1)
	cp -r test ${dest_folder}
	cp gaeunit.py ${dest_folder}
endif

ifneq ($(custom), 1)
	cp -r templates ${dest_folder}
	cp ${name}-app.yaml ${dest_folder}/app.yaml
	cp ${name}-secrets.py ${dest_folder}/secrets.py
	cp ${name}-config.json ${dest_folder}/config.json
endif
	
	cp -r httplib2 ${dest_folder}
	cp -r oauth2 ${dest_folder}
	cp -r simpleauth ${dest_folder}
	cp -r assets ${dest_folder}
	cp api.py ${dest_folder}
	cp base.py ${dest_folder}
	cp branch-engine.py ${dest_folder}
	cp controllers.py ${dest_folder}
	cp defaulttext.py ${dest_folder}
	cp handlers.py ${dest_folder}
	cp index.yaml ${dest_folder}
	cp messages.json ${dest_folder}
	cp models.py ${dest_folder}
	
