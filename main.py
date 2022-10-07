
from fastapi import FastAPI, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import MetaData, Table, update, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine, text, func, or_

from pydantic import BaseModel
from typing import List, Union, Set, Optional
import json
import pytz
from datetime import datetime


# ENGINES/DBs DECLARATIONS
engine1 = create_engine("postgresql://collectorusr:usrtocollect@localhost/collectors", pool_pre_ping=True)
#engine1 = ........


metadata_obj = MetaData()

# TABLEs DECLARATIONS
computers1 = Table("computers", metadata_obj, autoload_with=engine1)
#computers2 = .....


engines_dic = {
    "collectors" : {
                        "engine": engine1,
                        "table": computers1
                    },
    # "collector2" : {
    #                     "engine": engine2,
    #                     "table": computers2
    #                 },              
}



class ColumnIn(BaseModel):
    name: Union[str, None] = None
    value : Union[str, None] = None

class ItemIn(BaseModel):
    db_name: Union[str, None] = "collector1"
    table_name: Union[str, None] = "computers1"
    other: List[ColumnIn]
    constraint_col: Union[str, None] = None

class ItemInUpdate(BaseModel):
    db_name: Union[str, None] = None
    table_name: Union[str, None] = None
    ref_col: str # name of the column to update
    ref_value: str # name of the value on this column (condition for the WHERE clause)
    other: List[ColumnIn]
    created_time: str

class ItemDel(BaseModel):
    db_name: Union[str, None] = None
    table_name: Union[str, None] = None
    comp_id : Union[str, None] = None



app = FastAPI()






async def get_computers_both(db_name: str, table_name: str, q: str = "essai", skip: int = 0, limit: str = "100"):
    table = engines_dic[db_name]["table"]
    list_of_columns = [c for c in table.columns]
    try:
        with engines_dic[db_name]["engine"].connect() as conn:
            result = conn.execute(select(table).filter(
                    or_(*[col.contains(q) for col in list_of_columns[1:]])
            ).limit(limit))
            return result
    except Exception as e:
        print(e)
        return False




async def get_columns_names(db_name: str, table_name: str):
    try:
        with engines_dic[db_name]["engine"].connect() as conn:
            result = conn.execute(text("select column_name from INFORMATION_SCHEMA.COLUMNS where table_schema='public' AND TABLE_NAME='"+table_name+"';"))
            return result.fetchall()
    except Exception as e:
        print(e)
        return False


async def get_nb_computers(db_name: str, table_name: str):
    try:
        with engines_dic[db_name]["engine"].connect() as conn:
            result = conn.execute(text("SELECT COUNT(id) FROM "+table_name+";"))
            return result.fetchone()[0]
    except Exception as e:
        print(e)
        return False



templates = Jinja2Templates(directory="templates")



@app.get("/computers/{db_name}/{table_name}", response_class=HTMLResponse)
async def read_computers(db_name: str, table_name: str, request: Request, q: str = "", nb: str = "", hx_request: Optional[str] = Header(None)):
    results = None
    if q != "" and nb == "":
        results = await get_computers_both(db_name, table_name, q, 0, 99999)
    elif nb != "" and q == "":
        results = await get_computers_both(db_name, table_name, "", 0, nb)
    elif nb != "" and q != "":
        results = await get_computers_both(db_name, table_name, q, 0, nb)
    else:
        results = await get_computers_both(db_name, table_name, q, "", 99999)


    nb_computers = await get_nb_computers(db_name, table_name)
    columnnames = await get_columns_names(db_name, table_name)
    context = {"request": request, "nb_computers": nb_computers, "computers": results, \
                "columnnames": columnnames, "db_name": db_name, "table_name": table_name}

    if hx_request:
        return templates.TemplateResponse("table.html", context)
    return templates.TemplateResponse("computers.html", context)



@app.post("/computers/")
async def create_computer(item: ItemIn):

    dico = { it.name: it.value for it in item.other }
    dico["created_time"] = str(datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone("Europe/Paris")))
    try:
        with engines_dic[item.db_name]["engine"].connect() as conn:

            result = conn.execute(
                insert(engines_dic[item.db_name]["table"]).values(dico).on_conflict_do_update(
                    #constraint=engines_dic[item.db_name]["table"].UniqueConstraint,
                    index_elements=[item.constraint_col],
                    set_ = dico
                )
            )
            return item
    except Exception as e:
        print(e)
        return item




@app.delete("/computers/")
async def delete_computer(item: ItemDel):
    try:
        with engines_dic[item.db_name]["engine"].connect() as conn:
            result = conn.execute(
                delete(engines_dic[item.db_name]["table"]).where(engines_dic[item.db_name]["table"].c.id == item.comp_id)
            )
            return item
    except Exception as e:
        print(e)
        return item
