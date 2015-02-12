-- ###
-- ###
SELECT row_to_json(user_row) 
FROM   (SELECT username                           AS id, 
               first_name                         AS firstname, 
               last_name                          AS surname, 
               full_name                          AS fullname, 
               title                              AS title,
               suffix                             AS suffix
        FROM   users AS u 
        WHERE  u.username = %s ) AS user_row
