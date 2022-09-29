from typing import Any, List

from fastapi import FastAPI, Form, HTTPException
from pydantic import BaseModel
import sqlite3


app = FastAPI()
con = sqlite3.connect("demo.db", check_same_thread=False)
cursor = con.cursor()


class TacheForm(BaseModel):
    nom_tache: str
    due_pour: str


class TacheBD(BaseModel):
    rowid: int
    nom_tache: str
    due_pour: str

    # def __init__(self, r: int, n: str, d: str, **data: Any):
    #     super().__init__(**data)
    #     self.rowid = r
    #     self.nom_tache = n
    #     self.due_pour = d


@app.on_event("startup")
def creer_bd():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS taches (
    nom text NOT NULL,
    due_pour text NOT NULL
    );
    """)
    con.commit()


@app.get("/")
def root():
    return {"message": "Bienvenu au protocole domestique en REST"}

# response_model permet de spécifier le format de la réponse
# si je respecte pas le format, FastApi me donne une erreur
# validation à la sortie gratuite!
@app.post("/taches", status_code=201, response_model=TacheBD)
def ajouter_tache(tache: TacheForm):
    cursor.execute("INSERT INTO taches VALUES(?, ?)", (tache.nom_tache, tache.due_pour,))
    con.commit()
    return recuperer_tache(cursor.lastrowid)


@app.delete("/taches/{id_tache}", response_model=TacheBD)
def retirer_tache(id_tache: int):
    tache = recuperer_tache(id_tache)
    if tache is None:
        raise HTTPException(status_code=404, detail=f"Une tâche ayant l'identifiant {id_tache} n'a pu être trouvée")
    cursor.execute("DELETE FROM taches WHERE rowid = ?", (tache.rowid,))
    con.commit()
    return tache


@app.get("/taches", response_model=List[TacheBD])
def recuperer_taches():
    reponse = cursor.execute("SELECT rowid, nom, due_pour FROM taches")
    tuples_tache = reponse.fetchall()
    taches = [TacheBD(rowid=t[0], nom_tache=t[1], due_pour=t[2]) for t in tuples_tache]
    return taches


@app.get("/taches/{id_tache}", response_model=TacheBD)
def recuperer_tache(id_tache: int):
    reponse = cursor.execute("SELECT rowid, nom, due_pour FROM taches WHERE rowid = ?", (id_tache,))
    tuple_tache = reponse.fetchone()
    if tuple_tache is None:
        raise HTTPException(status_code=404, detail=f"Une tâche ayant l'identifiant {id_tache} n'a pu être trouvée")
    # fetchone retourne un tuple. FastAPI fait la conversion avant de lancer vers le client,
    # mais pas lorsque je l'appelle de l'interne. Donc je dois créer mon objet moi-même
    tache: TacheBD = TacheBD(rowid=tuple_tache[0], nom_tache=tuple_tache[1], due_pour=tuple_tache[2])
    return tache

