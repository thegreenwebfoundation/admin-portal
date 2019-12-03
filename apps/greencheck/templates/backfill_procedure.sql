DROP PROCEDURE IF EXISTS backfill;

CREATE PROCEDURE backfill()
BEGIN
  DECLARE done INT DEFAULT FALSE;

  DECLARE gdatum DATETIME;
  DECLARE ggreen TINYINT(2);
  DECLARE gid_hp INT(11);
  DECLARE gurl VARCHAR(255);
  DECLARE cur CURSOR FOR SELECT datum, green, id_hp, url FROM greencheck where id_hp > 0;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

  OPEN cur;

  read_loop: LOOP
    FETCH cur INTO gdatum, ggreen, gid_hp, gurl;
    IF done THEN
      LEAVE read_loop;
    END IF;
    call insert_urls(gurl, ggreen, gid_hp, gdatum);
  END LOOP read_loop;

  CLOSE cur;
END;
