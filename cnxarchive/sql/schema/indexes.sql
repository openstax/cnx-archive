CREATE INDEX modules_moduleid_idx on modules (moduleid);
CREATE INDEX modules_upmodid_idx ON modules  (upper(moduleid));
CREATE INDEX modules_upname_idx ON modules  (upper(name));
CREATE INDEX modules_portal_type_idx on modules (portal_type);
CREATE INDEX modules_uuid_idx on modules (uuid);
CREATE INDEX modules_uuid_txt_version_idx on
    modules (CAST(uuid as text), module_version(major_version, minor_version));
CREATE INDEX modules_short_id_idx on modules (short_id(uuid));

CREATE INDEX latest_modules_upmodid_idx ON latest_modules  (upper(moduleid));
CREATE INDEX latest_modules_upname_idx ON latest_modules  (upper(name));
CREATE INDEX latest_modules_moduleid_idx on latest_modules (moduleid);
CREATE INDEX latest_modules_module_ident_idx on latest_modules (module_ident);
CREATE INDEX latest_modules_portal_type_idx on latest_modules (portal_type);
CREATE UNIQUE INDEX lastest_modules_uuid_idx on latest_modules (uuid);
CREATE INDEX latest_modules_uuid_text_version_idx on
    latest_modules (cast(uuid as text), module_version(major_version, minor_version));
CREATE UNIQUE INDEX lastest_modules_short_id_idx on latest_modules (short_id(uuid));

CREATE INDEX fti_idx ON modulefti USING gist (module_idx);
CREATE INDEX collated_fti_idx ON collated_fti USING gist (module_idx);

CREATE INDEX modulefti_lexemes_module_ident on modulefti_lexemes (module_ident);

CREATE INDEX keywords_upword_idx ON keywords  (upper(word));
CREATE INDEX keywords_word_idx ON keywords  (word);

CREATE INDEX modulekeywords_module_ident_idx ON modulekeywords (module_ident );
CREATE INDEX modulekeywords_keywordid_idx ON modulekeywords (keywordid);
CREATE UNIQUE INDEX modulekeywords_module_ident_keywordid_idx ON
    modulekeywords (module_ident, keywordid );

CREATE INDEX files_md5_idx on files (md5);
CREATE INDEX files_sha1_idx ON files (sha1);

CREATE UNIQUE INDEX module_files_idx ON module_files (module_ident, filename);

CREATE UNIQUE INDEX similarities_objectid_version_idx ON similarities (objectid, version);

create index latest_modules_title_idx on latest_modules (upper(title_order(name)));

CREATE INDEX modules_strip_html_name_trgm_gin ON modules USING gin(strip_html(name) gin_trgm_ops);
