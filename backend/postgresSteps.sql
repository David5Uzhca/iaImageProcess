/*
CREATE TABLE IF NOT EXISTS images (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    labels TEXT[] NOT NULL
);

*/
SELECT * FROM images
--DELETE FROM images

--CAMBIO DE TXT[] A JSON
--ALTER TABLE images ADD COLUMN labels_temp JSONB;
--UPDATE images SET labels_temp = to_jsonb(labels);
--ALTER TABLE images DROP COLUMN labels;
--ALTER TABLE images RENAME COLUMN labels_temp TO labels;
