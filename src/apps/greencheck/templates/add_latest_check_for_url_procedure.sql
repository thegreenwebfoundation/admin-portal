DROP PROCEDURE IF EXISTS add_latest_check_for_url;

-- define our procedure, that accepts the url param, as a VarChar
CREATE PROCEDURE add_latest_check_for_url(IN purl VarChar(255))

BEGIN


  -- declare the types we'd fetch from the cursor
  DECLARE g_id            BIGINT(20);
  DECLARE g_id_hp         INT(11);
  DECLARE g_id_greencheck INT(11);
  DECLARE g_type          ENUM('url','whois','ip','none','as');
  DECLARE g_url           VARCHAR(255);
  DECLARE g_ip            DECIMAL(39,0);
  DECLARE g_datum         TIMESTAMP;
  DECLARE g_green         ENUM('yes','no','old');
  DECLARE g_tld           VARCHAR(64);

  -- declare the other types for the next query
  DECLARE h_hostname        VARCHAR(255);
  DECLARE h_hostpartner     VARCHAR(255);
  DECLARE h_hostwebsite     VARCHAR(255);


  -- SELECT concat('** checking for: ', purl) AS '** DEBUG:';

  DECLARE CONTINUE HANDLER FOR NOT FOUND
    BEGIN
      -- SELECT concat('** NO RESULT FOR: ', purl) AS '** DEBUG:';
      -- SELECT concat('** BUT WE SHOULD NOT BUBBLE THE EXCEPTION UP: ', '') AS '** DEBUG:';
    END;



  -- fetch the latest result for this url, using the index
  SELECT id, id_hp, id_greencheck, type, url, ip, datum, green, tld
  FROM greencheck
  WHERE url = purl
  ORDER BY datum DESC
  LIMIT 1
  INTO g_id, g_id_hp, g_id_greencheck, g_type, g_url, g_ip, g_datum, g_green, g_tld;


   -- now get our hosting providers

  SELECT naam, partner, website INTO h_hostname, h_hostpartner, h_hostwebsite
  FROM hostingproviders WHERE id = g_id_hp;

    -- check
    IF g_green = 'yes' THEN

      START TRANSACTION;
      -- SELECT concat('** GREEN: ', purl) AS '** DEBUG:';
      INSERT INTO green_presenting
      (
        `id`,
        `modified`, `green`, `hosted_by`,
        `hosted_by_id`, `hosted_by_website`,
        `partner`, `url`
      )
      VALUES (
        g_id,
        g_datum, 1, h_hostname,
        g_id_hp, h_hostwebsite,
        h_hostpartner, g_url
      )
      -- we need an upsert
      ON DUPLICATE KEY UPDATE
        `id` = g_id,
        `modified` = g_datum,
        `green` = g_green,
        `hosted_by` = h_hostname,
        `hosted_by_id` = g_id_hp,
        `hosted_by_website` = h_hostwebsite,
        `partner` = h_hostpartner;

      COMMIT;

    END IF;
END
