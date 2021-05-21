# select id_hp, checks from greencheck_2021 WHERE datum > "2021-05-01" AND green = 'yes' GROUP BY id_hp ORDER BY 2 DESC LIMIT 10;
# +-------+-----------+
# | id_hp | checks |
# +-------+-----------+
# | 595   | 5343854   |
# | 779   | 1511123   |
# | 793   | 827239    |
# | 475   | 658133    |
# | 698   | 341040    |
# | 131   | 183759    |
# | 697   | 158123    |
# | 696   | 68853     |
# | 564   | 55754     |
# | 821   | 33126     |
# +-------+-----------+


# select url , count(id) as popularity from greencheck_2021 WHERE datum > "2021-05-01" AND green = 'yes' GROUP BY url ORDER BY popularity DESC LIMIT 10;
# +-------------------+------------+
# | url               | popularity |
# +-------------------+------------+
# | www.youtube.com   | 1062410    |
# | www.google.com    | 622153     |
# | i.ytimg.com       | 224544     |
# | play.google.com   | 202459     |
# | www.facebook.com  | 202263     |
# | www.google.fr     | 186672     |
# | www.gstatic.com   | 167688     |
# | docs.google.com   | 137244     |
# | ssl.gstatic.com   | 133650     |
# | fonts.gstatic.com | 122881     |
# +-------------------+------------+
