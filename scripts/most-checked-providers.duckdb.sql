-- This SQL is designed to be run with duckdb 
-- to provided aggregate stats on which providers we have receive the most checks



CREATE OR REPLACE TABLE hosting_providers AS SELECT * FROM './data/hostingproviders.tsv';

CREATE OR REPLACE TABLE domain_counts AS (
    SELECT id_hp as provider_id, count(id) as counted
    FROM read_parquet('data/parquet/*.parquet') 
    GROUP BY provider_id
    ORDER BY counted DESC
);

COPY
    (SELECT 
    naam as name, provider_id, counted as checks
    FROM
    hosting_providers
RIGHT JOIN 
    domain_counts
ON 
    domain_counts.provider_id = hosting_providers.id
ORDER BY checks DESC
    )
TO
    'named_domain_popularity.csv' WITH (HEADER 1, DELIMITER ',');