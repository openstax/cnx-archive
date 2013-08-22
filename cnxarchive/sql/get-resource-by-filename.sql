-- arguments: id:string; filename:string
SELECT f.file
FROM module_files as mf
  LEFT JOIN files f on mf.fileid = f.fileid
  LEFT JOIN modules m on mf.module_ident = m.module_ident
WHERE m.uuid = %(id)s AND mf.filename = %(filename)s;
