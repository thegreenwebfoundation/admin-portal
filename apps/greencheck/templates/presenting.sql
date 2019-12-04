CREATE TABLE IF NOT EXISTS `green_presenting` (
    `id` Int( 11 ) AUTO_INCREMENT NOT NULL,
    `url` VarChar( 255 ) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
    `hosted_by` VarChar( 255 ) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
    `hosted_by_website` VarChar( 255 ) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
    `partner` VarChar( 255 ) CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
    `green` TinyInt( 2 ) NOT NULL,
    `hosted_by_id` Int( 11 ) NOT NULL,
    `modified` DateTime NOT NULL,
    PRIMARY KEY ( `id` ),
    CONSTRAINT `unique_url` UNIQUE( `url` ) )
CHARACTER SET = utf8
COLLATE = utf8_general_ci
ENGINE = InnoDB;

-- CREATE INDEX "unique_url" -----------------------------------
CREATE UNIQUE INDEX `unique_url` USING BTREE ON `green_presenting`( `url` );
-- -------------------------------------------------------------
