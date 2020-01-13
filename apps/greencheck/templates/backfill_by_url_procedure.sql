
-- then for each url, we run a query to get the latest result from
-- greencheck using the date index, and if it is green
-- load that into the green_presenting table

DROP PROCEDURE IF EXISTS backfill_by_url;

CREATE PROCEDURE backfill_by_url()

BEGIN
  -- we need a way to check so we can exit the loop
  DECLARE done INT(1) DEFAULT FALSE;

  -- declare the types we'd fetch from the cursor
  DECLARE url                VARCHAR(255);

  -- set up our cursor, so we have a list of urls to loop through
  DECLARE cur CURSOR FOR
  SELECT url FROM green_presenting;

  -- set the end state: handle the not found case by setting done to true
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

  -- open our cursor to start listing through all the urls
  OPEN cur;

  REPEAT
    FETCH cur INTO url;
    CALL add_latest_check_for_url(url);

  UNTIL done END REPEAT;

  CLOSE cur;
END;
