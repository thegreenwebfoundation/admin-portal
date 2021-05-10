counts_by_day = [
    ("2021-04-01", 5613124,),
    ("2021-04-02", 4939316,),
    ("2021-04-03", 3178513,),
    ("2021-04-04", 3324663,),
    ("2021-04-05", 4599095,),
    ("2021-04-06", 6619976,),
    ("2021-04-07", 6259709,),
    ("2021-04-08", 6506998,),
    ("2021-04-09", 6299486,),
    ("2021-04-10", 3876472,),
    ("2021-04-11", 3690221,),
    ("2021-04-12", 4617246,),
    ("2021-04-13", 4401462,),
    ("2021-04-14", 4679025,),
    ("2021-04-15", 4319828,),
    ("2021-04-16", 4156878,),
    ("2021-04-17", 3109650,),
    ("2021-04-18", 3552393,),
    ("2021-04-19", 4591834,),
    ("2021-04-20", 4648998,),
    ("2021-04-21", 1044820,),
    ("2021-04-23", 5359446,),
    ("2021-04-24", 8162426,),
    ("2021-04-25", 4122289,),
    ("2021-04-26", 6145970,),
    ("2021-04-27", 5992501,),
    ("2021-04-28", 5589077,),
    ("2021-04-29", 6324849,),
    ("2021-04-30", 5310190,),
    ("2021-05-01", 3530141,),
    ("2021-05-02", 4240298,),
    ("2021-05-03", 4226524,),
    ("2021-05-04", 4238094,),
    ("2021-05-05", 2852760,),
]




day_total, day_green, day_grey = [5613124, 2113134, 3499990]

day_totals = {
    "day_total": day_total,
    "day_green": day_green,
    "day_grey": day_grey,
}

top_green_hosters = [
    {"hoster_id": 595, "count": 5343854},
    {"hoster_id": 779, "count": 1511123},
    {"hoster_id": 793, "count": 827239},
    {"hoster_id": 475, "count": 658133},
    {"hoster_id": 698, "count": 341040},
    {"hoster_id": 131, "count": 183759},
    {"hoster_id": 697, "count": 158123},
    {"hoster_id": 696, "count": 68853},
    {"hoster_id": 564, "count": 55754},
    {"hoster_id": 821, "count": 33126},
]

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

top_green_domains = [ 
    {"domain": "www.youtube.com", "count": 1062410, "hosted_by": "hosting.site.com" },
    {"domain": "www.google.com", "count": 622153, "hosted_by": "hosting.site.com" },
    {"domain": "i.ytimg.com", "count": 224544, "hosted_by": "hosting.site.com" },
    {"domain": "play.google.com", "count": 202459, "hosted_by": "hosting.site.com" },
    {"domain": "www.facebook.com", "count": 202263, "hosted_by": "hosting.site.com" },
    {"domain": "www.google.fr", "count": 186672, "hosted_by": "hosting.site.com" },
    {"domain": "www.gstatic.com", "count": 167688, "hosted_by": "hosting.site.com" },
    {"domain": "docs.google.com", "count": 137244, "hosted_by": "hosting.site.com" },
    {"domain": "ssl.gstatic.com", "count": 133650, "hosted_by": "hosting.site.com" },
    {"domain": "fonts.gstatic.com", "count": 122881, "hosted_by": "google.com"},
]


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
