CREATE VIEW all_modules as
	SELECT module_ident, uuid, portal_type, moduleid, version, name,
			created, revised, abstractid, stateid, doctype, licenseid,
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors, google_analytics,
			buylink, major_version, minor_version, print_style
	FROM modules
	UNION ALL
	SELECT module_ident, uuid, portal_type, moduleid, 'latest', name,
			created, revised, abstractid, stateid, doctype, licenseid,
			submitter, submitlog, parent, language,
			authors, maintainers, licensors, parentauthors, google_analytics,
			buylink, major_version, minor_version, print_style
	FROM latest_modules;

CREATE VIEW current_modules AS
       SELECT * FROM modules m
	      WHERE module_ident =
		    (SELECT max(module_ident) FROM modules
			    WHERE m.moduleid = moduleid );
