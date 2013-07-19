-- arguments: id:string
SELECT filename, mimetype, file
FROM module_files as mf
LEFT JOIN files f on mf.fileid = f.fileid
WHERE mf.uuid = %(id)s;
