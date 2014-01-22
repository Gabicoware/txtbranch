staging_folder = ../txtbranch-staging

prep:
	mkdir -p ${staging_folder}
	
install-staging: install-base
	cp -r tests ${staging_folder}

install-base: prep
	cp *.* ${staging_folder}
	cp -r httplib2 ${staging_folder}
	cp -r oauth2 ${staging_folder}
	cp -r simpleauth ${staging_folder}
	cp -r assets ${staging_folder}
