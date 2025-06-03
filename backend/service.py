import base64
from flask import flash, current_app
import pandas as pd
import utils
from models import Project, User, db
import pymysql
from sqlalchemy import text
import os
from dotenv import load_dotenv
from datetime import datetime
import math

load_dotenv()

DISCOUNTS_FILE_NAME = os.getenv('DISCOUNTS_FILE_NAME', 'project_discounts.xlsx')
PROJECT_NAME_COLUMN = os.getenv('PROJECT_NAME_COLUMN', 'Project Name')
# --- Use the column for the single relevant discount ---
DISCOUNT_COLUMN = os.getenv('DISCOUNT_FULL_COLUMN', 'Discount Rate') # Or rename env var if desired
DISCOUNTS_SHEET_NAME = os.getenv('DISCOUNTS_SHEET_NAME', 0) # Читаем имя листа, по умолчанию 0 (первый лист)
# --- ---
DB_TYPE=os.getenv('DB_TYPE', '')
DB_USER=os.getenv('DB_USER', '')
DB_PASSWORD=os.getenv('DB_PASSWORD', '')
DB_HOST=os.getenv('DB_HOST', '')
DB_PORT=os.getenv('DB_PORT', '')
DB_NAME=os.getenv('DB_NAME', '')
DOLLAR=float(os.getenv('DOLLAR', ''))
DO_KADASTRA_COLUMN=os.getenv('DO_KADASTRA_COLUMN', 'Do Kadastra')
PLAN_SHEET_NAME=os.getenv('PLAN_SHEET_NAME', 'Plan') # Имя листа для плана

def get_data(last_house_count=3):
    """
    Fetches project data, calculates metrics, and updates the Project table in the database.
    Returns a list of dictionaries containing the processed data.
    """

    projects_results = [] # Keep this to return the processed data

    try:

        connection = pymysql.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            proj_query = """
                SELECT DISTINCT complex_name
                FROM estate_houses"""
            # Выполняем запрос
            cursor.execute(proj_query) # Убрали параметры {}, т.к. их нет в этом запросе
            # Получаем результаты
            macro_project_rows = cursor.fetchall()

            discounts = get_discounts()
            kadastrs = get_kadastr()
            plan = get_plan()

            if not discounts:
                 current_app.logger.warning("Discount map is empty in get_data. All discounts will be 0.")

            processed_projects = [] # To store data before returning

            for current_project_row in macro_project_rows:
                current_project_name = current_project_row['complex_name']
                discount_full = discounts.get(current_project_name, 0.0)
                kadastr_value = kadastrs.get(current_project_name, 0)
                plan_value = plan.get(current_project_name, 0)

                leftovers_query = """
                    SELECT (es.estate_price - 3000000)/es.estate_area AS price
                    FROM macro_bi_cmp_528.estate_sells es
                    LEFT JOIN macro_bi_cmp_528.estate_houses eh ON es.house_id = eh.id
                    WHERE eh.complex_name = %(project_name)s AND es.estate_sell_status_name IN ('Маркетинговый резерв', 'Подбор') AND es.estate_sell_category = "flat"
                    """ # Используем %(key)s для именованных плейсхолдеров в pymysql
                # Выполняем запрос с параметрами
                cursor.execute(leftovers_query, {"project_name": current_project_name})
                leftovers_rows = cursor.fetchall()
                # Доступ по ключу 'price' (как указано в AS price)
                leftovers_sum = float(sum(row['price'] for row in leftovers_rows if row['price'] is not None))
                valid_leftovers_count = sum(1 for row in leftovers_rows if row['price'] is not None)
                avg_leftover_price = (leftovers_sum * (1 - discount_full)) / valid_leftovers_count if valid_leftovers_count > 0 else 0

                # --- Calculate avg_last_n_sells_100 ---
                cur_proj_last_sells_100 = """
                    SELECT ed.deal_sum/ed.deal_area as deal_sum, ed.id
                    FROM macro_bi_cmp_528.estate_deals ed
                    LEFT JOIN macro_bi_cmp_528.estate_houses eh ON ed.house_id = eh.id
                    LEFT JOIN macro_bi_cmp_528.estate_sells es ON ed.estate_sell_id = es.id
                    WHERE eh.complex_name = %(project_name)s AND               
                        (ed.deal_program_name = 'Ипотека' OR
                        ed.deal_program_name = 'Ипотека2' OR
                        ed.deal_program_name = 'Ипотека под 0%%' OR
                        ed.deal_program_name = 'Легкий старт' OR
                        ed.deal_program_name = 'Рассрочка+Ипотека' OR
                        ed.deal_program_name = 'ПВ15%%+ипотека+рассрочка' OR
                        ed.deal_program_name = 'Гибрид' OR
                        ed.deal_program_name = "100%% оплата") AND 
                        es.estate_sell_category = "flat"
                    ORDER BY ed.deal_date DESC, ed.date_modified DESC LIMIT %(count)s
                    """ # Используем %(key)s для именованных плейсхолдеров
                # Выполняем запрос с параметрами
            
                cursor.execute(cur_proj_last_sells_100, {"project_name": current_project_name, "count": last_house_count})
                last_n_sells_100_rows = cursor.fetchall()
                # Доступ по ключу 'deal_sum'
                print(f"Last N sells {current_project_name} rows: {sum(row['id'] for row in last_n_sells_100_rows if row['id'] is not None)}")
                last_n_sells_100_sum = sum(row['deal_sum'] for row in last_n_sells_100_rows if row['deal_sum'] is not None)
                count_100 = len(last_n_sells_100_rows)
                avg_last_n_sells_100 = last_n_sells_100_sum / count_100 if count_100 > 0 else 0
                
                fact_deals = """
                SELECT COUNT(ed.id)
                FROM macro_bi_cmp_528.estate_deals ed
                LEFT JOIN macro_bi_cmp_528.estate_houses eh ON ed.house_id = eh.id
                LEFT JOIN macro_bi_cmp_528.estate_sells es ON ed.estate_sell_id = es.id
                WHERE eh.complex_name = %(project_name)s AND               
                    (ed.deal_program_name = 'Ипотека' OR
                    ed.deal_program_name = 'Ипотека2' OR
                    ed.deal_program_name = 'Ипотека под 0%%' OR
                    ed.deal_program_name = 'Легкий старт' OR
                    ed.deal_program_name = 'Рассрочка+Ипотека' OR
                    ed.deal_program_name = 'ПВ15%%+ипотека+рассрочка' OR
                    ed.deal_program_name = 'Гибрид' OR
                    ed.deal_program_name = "100%% оплата") AND 
                    es.estate_sell_category = "flat" AND
                    (ed.agreement_date BETWEEN %(date_from)s AND %(date_to)s ) AND
                    ed.agreement_date != %(date_to)s
                """
                this_month = ''.join(['0',str(datetime.now().month)]) if datetime.now().month < 10 else str(datetime.now().month)
                next_month = ''.join(['0',str(datetime.now().month+1)]) if datetime.now().month+1 < 10 else str(datetime.now().month+1)

                date_from = ''.join([str(datetime.now().year),'-',this_month,'-','01'])
                date_to = ''.join([str(datetime.now().year),'-',next_month,'-','01'])
                cursor.execute(fact_deals,
                                {"project_name": current_project_name,
                                 "date_from": date_from,
                                 "date_to": date_to})
                fact_deals_rows = cursor.fetchall()
                # --- Find or Create Project in DB ---
                project_entry = Project.query.filter_by(name=current_project_name).first()
                
                fact_deals_val=int(fact_deals_rows[0]['COUNT(ed.id)']) if fact_deals_rows else 0
                deviation= fact_deals_val/plan_value if plan_value > 0 else 0

                if project_entry:
                    # print("Update existing project")
                    current_app.logger.info(f"Updating project: {current_project_name}")
                    project_entry.max_discount_full=round(discount_full, 2)
                    project_entry.lowest_price_full=math.ceil(float(avg_leftover_price))
                    project_entry.average_price_full=math.ceil(float(avg_last_n_sells_100))
                    project_entry.do_kadastra=kadastr_value # Assuming do_kadastra is 0 by default
                    project_entry.lowest_price_full_dol=math.ceil(float(avg_leftover_price) / DOLLAR)
                    project_entry.average_price_full_dol=math.ceil(float(avg_last_n_sells_100) / DOLLAR)
                    project_entry.data_update=utils.month_name(datetime.now().month)
                    project_entry.fact_deals=fact_deals_val
                    project_entry.plan_deals=plan_value
                    project_entry.deviation=deviation
                    # project_entry.av=erage_price_ipoteka = avg_last_n_sells_ipoteka
                    # Update other fields if necessary
                    # project_entry.max_discount_full = discount_full # Example
                    # project_entry.last_updated = datetime.utcnow() # Example
                else:
                    # print('Create new project')
                    current_app.logger.info(f"Creating new project: {current_project_name}")
                    project_entry = Project(
                        name=current_project_name,
                        max_discount_full=round(discount_full, 2),
                        lowest_price_full=math.ceil(float(avg_leftover_price)),
                        lowest_price_full_dol=math.ceil(float(avg_leftover_price) / DOLLAR),
                        average_price_full=math.ceil(float(avg_last_n_sells_100)),
                        average_price_full_dol=math.ceil(float(avg_last_n_sells_100) / DOLLAR),
                        do_kadastra=kadastr_value, # Assuming do_kadastra is 0 by default
                        data_update=utils.month_name(datetime.now().month),
                        fact_deals=fact_deals_val,
                        plan_deals=plan_value,
                        deviation=deviation
                        # Add other fields if necessary
                        # max_discount_full=discount_full,
                    )
                    db.session.add(project_entry)

                # --- Store results for return value ---
                processed_data = {
                    "name": project_entry.name,
                    "lowest_price_full": project_entry.lowest_price_full,
                    "average_price_100": project_entry.average_price_full,
                    "lowest_price_full_dol" : project_entry.lowest_price_full_dol,
                    "average_price_full_dol" : project_entry.average_price_full_dol,
                    # "average_price_ipoteka": avg_last_n_sells_ipoteka/DOLLAR,
                    "discount_applied": project_entry.max_discount_full,
                    "do_kadastra": project_entry.do_kadastra, # Assuming do_kadastra is 0 by default
                    "data_update":project_entry.data_update,
                    "fact_deals":project_entry.fact_deals,
                    "plan_deals":project_entry.plan_deals,
                    "deviation":project_entry.deviation,
                    "db_action": "updated" if project_entry in db.session.dirty else "created" if project_entry in db.session.new else "unchanged"
                }
                processed_projects.append(processed_data)

            # --- Commit all changes after the loop ---
            db.session.commit()
            current_app.logger.info("Project data update complete. Changes committed.")
            # --- ---

            return processed_projects # Return the list of processed data

    except Exception as e:
        current_app.logger.error(f"An error occurred in get_data: {e}", exc_info=True)
        db.session.rollback() # Rollback on error
        current_app.logger.error("Database transaction rolled back due to error.")
        return [] # Return empty list on error
    
def get_discounts():
    """
    Reads project discounts from a specific sheet in an Excel file.
    Returns a dictionary: {project_name: discount_rate}
    Rates are floats (0.0 to 1.0).
    """
    discounts_map = {}
    print(f"Reading discounts from {DISCOUNTS_FILE_NAME}")
    # Construct the absolute path if DISCOUNTS_FILE_PATH is relative
    if not os.path.isabs(DISCOUNTS_FILE_NAME):
        file_path = DISCOUNTS_FILE_NAME
    else:
        file_path = DISCOUNTS_FILE_NAME

    try:
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"Discount file not found at calculated path: {file_path}")

        # --- Используем имя листа при чтении ---
        df = pd.read_excel(file_path, sheet_name=DISCOUNTS_SHEET_NAME)
        # --- ---

        # Check if required columns exist
        required_columns = [PROJECT_NAME_COLUMN, DISCOUNT_COLUMN]
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise KeyError(f"Missing required columns ({missing}) in sheet '{DISCOUNTS_SHEET_NAME}' of discount file.")

        for index, row in df.iterrows():
            project_name_raw = row[PROJECT_NAME_COLUMN]

            if pd.notna(project_name_raw):
                project_name = str(project_name_raw).strip()
                discount_rate = _parse_discount_rate(row[DISCOUNT_COLUMN], project_name, DISCOUNT_COLUMN)
                discounts_map[project_name] = discount_rate
            else:
                current_app.logger.warning(f"Missing project name in row {index+2} on sheet '{DISCOUNTS_SHEET_NAME}'. Skipping.")

    except FileNotFoundError as fnf_err:
        current_app.logger.error(str(fnf_err))
    except KeyError as key_err:
         current_app.logger.error(f"Column name error reading discounts: {key_err}")
    except ValueError as val_err: # pandas может выдать ValueError, если имя листа не найдено
         current_app.logger.error(f"Error reading sheet '{DISCOUNTS_SHEET_NAME}' from Excel file: {val_err}. Check sheet name.")
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred reading discounts: {e}", exc_info=True)

    if not discounts_map:
         current_app.logger.warning(f"Discounts map is empty after attempting to read sheet '{DISCOUNTS_SHEET_NAME}'.")

    return discounts_map

def get_kadastr():
    """
    Fetches kadastr data from the file in to a map"""

    kadastr_map = {}
    try:
        # Construct the absolute path if DISCOUNTS_FILE_PATH is relative

        file_path = DISCOUNTS_FILE_NAME

        if not os.path.exists(file_path):
             raise FileNotFoundError(f"Discount file not found at calculated path: {file_path}")

        df = pd.read_excel(file_path, sheet_name=DISCOUNTS_SHEET_NAME)

        # Check if required columns exist
        required_columns = [DO_KADASTRA_COLUMN]
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise KeyError(f"Missing required columns ({missing}) in sheet '{DISCOUNTS_SHEET_NAME}' of discount file.")

        for index, row in df.iterrows():
            project_name_raw = row[PROJECT_NAME_COLUMN]

            if pd.notna(project_name_raw):
                project_name = str(project_name_raw).strip()
                kadastr_value = row['Do Kadastra']
                kadastr_map[project_name] = kadastr_value
            else:
                current_app.logger.warning(f"Missing project name in row {index+2} on sheet '{DISCOUNTS_SHEET_NAME}'. Skipping.")

    except FileNotFoundError as fnf_err:
         current_app.logger.error(str(fnf_err))
    except KeyError as key_err:
         current_app.logger.error(f"Column name error reading discounts: {key_err}")
    except ValueError as val_err: # pandas может выдать ValueError, если имя листа не найдено
         current_app.logger.error(f"Error reading sheet '{DISCOUNTS_SHEET_NAME}' from Excel file: {val_err}. Check sheet name.")
    except Exception as e:
         current_app.logger.error(f"An unexpected error occurred reading discounts: {e}", exc_info=True)

    return kadastr_map

def _parse_discount_rate(rate_value, project_name, column_name):

    """Helper function to parse and validate a single discount rate."""
    if pd.isna(rate_value):
        current_app.logger.warning(f"Missing discount rate in column '{column_name}' for project '{project_name}'. Defaulting to 0.0.")
        return 0.0
    try:
        if isinstance(rate_value, str) and '%' in rate_value:
            rate = float(rate_value.strip('%')) / 100.0
        else:
            rate = float(rate_value)

        if 0.0 <= rate <= 1.0:
            return rate
        else:
            current_app.logger.warning(f"Discount rate {rate} from column '{column_name}' for project '{project_name}' is outside the expected range (0-1). Using 0.0.")
            return 0.0
    except (ValueError, TypeError):
        current_app.logger.warning(f"Could not convert discount rate '{rate_value}' from column '{column_name}' for project '{project_name}' to float. Using 0.0.")
        return 0.0

def get_plan(date=None):
    plan_map = {}

    stolb_name=''
    if date is not None:
        this_month = ''.join(['0',str(date.month)]) if date.month < 10 else str(date.month)
        stolb_name  =''.join(['01','.',this_month,'.',str(date.year)]) 
    else:
        this_month = ''.join(['0',str(datetime.now().month)]) if datetime.now().month < 10 else str(datetime.now().month)
        stolb_name  = ''.join(['01','.',this_month,'.',str(datetime.now().year)]) 
    file_path = DISCOUNTS_FILE_NAME

    try:
        # Construct the absolute path if DISCOUNTS_FILE_PATH is relative

        file_path = DISCOUNTS_FILE_NAME

        if not os.path.exists(file_path):
             raise FileNotFoundError(f"Discount file not found at calculated path: {file_path}")

        df = pd.read_excel(file_path, sheet_name=PLAN_SHEET_NAME)

        # Check if required columns exist
        required_columns = [stolb_name]
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise KeyError(f"Missing required columns ({missing}) in sheet '{PLAN_SHEET_NAME}' of discount file.")

        for index, row in df.iterrows():
            project_name_raw = row[PROJECT_NAME_COLUMN]

            if pd.notna(project_name_raw):
                project_name = str(project_name_raw).strip()
                plan_count = row[stolb_name]
                plan_map[project_name] = plan_count
            else:
                current_app.logger.warning(f"Missing project name in row {index+2} on sheet '{DISCOUNTS_SHEET_NAME}'. Skipping.")

    except FileNotFoundError as fnf_err:
         current_app.logger.error(str(fnf_err))
    except KeyError as key_err:
         current_app.logger.error(f"Column name error reading discounts: {key_err}")
    except ValueError as val_err: # pandas может выдать ValueError, если имя листа не найдено
         current_app.logger.error(f"Error reading sheet '{DISCOUNTS_SHEET_NAME}' from Excel file: {val_err}. Check sheet name.")
    except Exception as e:
         current_app.logger.error(f"An unexpected error occurred reading discounts: {e}", exc_info=True)

    return plan_map