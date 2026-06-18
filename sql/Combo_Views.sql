-- Combo_Views.sql
--
BEGIN;
-- "Combo food" views let you treat multiple ingredients as one logical food.
-- Name the combo_name in all caps and preface with a dash so it stands out and will be first in the list of foods. 
---------
-- Issue with these are that serving sizes are not provided. Must redo with serving sizes as a field.
CREATE OR REPLACE VIEW YGRT_PB_FRT_NT AS
select '-YGRT_PB_FRT_NT' AS Combo_Name, name,1 as Combo_id, food_id
from food where name ilike '%peanut butter%' or name ilike '%greek%' or name ilike '%pecans%' or name ilike '%pear sauce%';

CREATE OR REPLACE VIEW YGRT_RSN_NT AS
select '-YGRT_RSN_NT' AS Combo_Name, name,2 as Combo_id, food_id
from food where name ilike '%greek%' or name ilike '%raisin%' or name ilike '%pecan%';

CREATE OR REPLACE VIEW YGRT_DT_NT AS
select '-YGRT_DT_NT' AS Combo_Name, name,3 as Combo_id, food_id
from food where name ilike '%greek%' or name ilike '%date%' or name ilike '%pecan%' or name ilike '%pecan%';

COMMIT;