-- arguments: id:string; filename:string
SELECT file
FROM module_files as mf
LEFT JOIN files f on mf.fileid = f.fileid
WHERE mf.uuid = %(id)s AND mf.filename = %(filename)s;
