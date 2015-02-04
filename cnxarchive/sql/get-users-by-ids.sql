-- ###
-- ###
SELECT row_to_json(user_row) 
FROM   (SELECT username                           AS id, 
               first_name                         AS firstname, 
               last_name                          AS surname, 
               full_name                          AS fullname, 
               title                              AS title, 
               (SELECT ARRAY_AGG(value)
                FROM   contact_infos AS ci 
                WHERE  ci.user_id = u.id 
                       AND type = 'EmailAddress') AS emails, 
               NULL                               AS suffix, 
               NULL                               AS website, 
               NULL                               AS othername 
        FROM   users AS u 
        WHERE  u.username = %s ) AS user_row
