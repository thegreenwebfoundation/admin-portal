
-- then for each url, we run a query to get the latest result from
-- greencheck using the date index, and if it is green
-- load that into the green_presenting table

DROP PROCEDURE IF EXISTS backfill_by_url;

CREATE PROCEDURE backfill_by_url()

BEGIN
  -- we need a way to check so we can exit the loop
  DECLARE done INT(8) DEFAULT FALSE;
  DECLARE counter INT(8) DEFAULT FALSE;

  -- declare the types we'd fetch from the cursor
  DECLARE fetched_url                VARCHAR(255);

  -- set up our cursor, so we have a list of urls to loop through
  DECLARE cur CURSOR FOR
  SELECT url FROM urls;

  -- set the end state: handle the not found case by setting done to true
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

  -- open our cursor to start listing through all the urls
  OPEN cur;

  read_loop: LOOP
    FETCH cur INTO fetched_url;
    -- SELECT concat('** ', fetched_url) AS '** DEBUG:';

    CALL add_latest_check_for_url(fetched_url);

    SET counter = counter + 1;

    -- counter added to show progress
    -- IF mod(counter, 100) = 0 THEN
    --   SELECT concat('** progress ', counter) AS '** DEBUG:';
    -- END IF;


    IF DONE THEN
      SELECT concat('** ENDING - nothing left to iterate through ', fetched_url) AS '** DEBUG:';
      LEAVE read_loop;
    END IF;
  END LOOP;


  CLOSE cur;
END;
