-- a temporary table to facilitate the creation of the green urls table
CREATE TABLE urls (
  url VARCHAR(255),
  PRIMARY KEY (url)
);

-- LOAD DATA
--   INFILE 'all_domains_outfile.txt'
-- INTO TABLE
--   urls
-- FIELDS TERMINATED BY ','
-- ENCLOSED BY ''
-- LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS;
