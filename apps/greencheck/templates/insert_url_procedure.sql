DROP PROCEDURE IF EXISTS insert_urls;

CREATE PROCEDURE insert_urls(IN url VarChar(255), IN green TinyInt(2), IN id_hp INT(11), IN datum datetime)
BEGIN
    DECLARE hostname VARCHAR(255);
    DECLARE hostwebsite VARCHAR(255);
    DECLARE hostpartner VARCHAR(255);

    SELECT naam, partner, website INTO hostname, hostpartner, hostwebsite
    FROM hostingproviders WHERE id = id_hp;

    IF (green = 0) THEN
        DELETE FROM green_presenting WHERE url = url;
    ELSE
        IF (hostname IS NOT NULL) THEN
            INSERT INTO green_presenting
            (`modified`, `green`, `hosted_by`, `hosted_by_id`, `hosted_by_website`, `partner`, `url`)
            VALUES (datum, green, hostname, id_hp, hostwebsite, hostpartner, url)
            ON DUPLICATE KEY UPDATE
            modified = datum;
        END IF;
    END IF;
END
