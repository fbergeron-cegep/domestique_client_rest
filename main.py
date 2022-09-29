from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
import sqlite3
from passlib.context import CryptContext
from jose import jwt, JWTError


app = FastAPI()
con = sqlite3.connect("demo.db", check_same_thread=False)
cursor = con.cursor()
PWD_CONTEXTE = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = "jk53snkj598kj5tw8rnfcy4ntgwvn74 vjen954ygrevh98fy43t4ge94ffhbv4oe"
ALGO = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/connexion")


class TacheForm(BaseModel):
    nom_tache: str
    due_pour: str


class TacheBD(BaseModel):
    rowid: int
    nom_tache: str
    due_pour: str


class MembreBD(BaseModel):
    nom_utilisateur: str
    courriel: str
    passe_chiffre: str


class MembreInscription(BaseModel):
    nom_utilisateur: str
    courriel: str
    passe_clair: str


# les noms ici sont imposés par la norme Oauth2
class MembreConnexion(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    nom_utilisateur: Optional[str] = None


def valider_phrase_de_passe(passe_clair: str, passe_chiffre: str) -> bool:
    return PWD_CONTEXTE.verify(passe_clair, passe_chiffre)


def chiffrer_phrase_de_passe(passe: str) -> str:
    return PWD_CONTEXTE.hash(passe)


def authentifier(*, username: str, password: str) -> Optional[MembreBD]:
    reponse = cursor.execute("SELECT nom_utilisateur, courriel, passe_chiffre FROM membres WHERE nom_utilisateur = ?",
                             (username,))
    tuple_membre = reponse.fetchone()
    if not tuple_membre:
        return None
    if not valider_phrase_de_passe(password, tuple_membre[2]):
        return None

    membre: MembreBD = MembreBD(nom_utilisateur=tuple_membre[0],
                                courriel=tuple_membre[1],
                                passe_chiffre=tuple_membre[2])
    return membre


def creer_jeton_acces(*, sub: str) -> str:
    return _creer_jeton(
        token_type="access_token",
        lifetime=timedelta(minutes=10000),
        sub=sub,
    )


def _creer_jeton(token_type: str, lifetime: timedelta, sub: str) -> str:
    payload = {}
    expire = datetime.utcnow() + lifetime
    payload["type"] = token_type
    payload["exp"] = expire
    payload["iat"] = datetime.utcnow()
    payload["sub"] = str(sub)
    secret = SECRET

    return jwt.encode(payload, secret, algorithm=ALGO)


def recuperer_membre_courant(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Le token est invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[ALGO],
            options={"verify_aud": False},
        )
        nom_utilisateur: str = payload.get("sub")
        if nom_utilisateur is None:
            raise credentials_exception
        token_data = TokenData(nom_utilisateur=nom_utilisateur)
    except JWTError:
        raise credentials_exception

    reponse = cursor.execute(
        "SELECT nom_utilisateur, courriel, passe_chiffre FROM membres WHERE nom_utilisateur = ?",
        (token_data.nom_utilisateur,))
    tuple_membre = reponse.fetchone()

    if not tuple_membre:
        raise credentials_exception

    return MembreBD(nom_utilisateur=tuple_membre[0], courriel=tuple_membre[1], passe_chiffre=tuple_membre[2])


@app.on_event("startup")
def creer_bd():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS taches (
        nom text NOT NULL,
        due_pour text NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS membres (
        nom_utilisateur text NOT NULL,
        courriel text NOT NULL,
        passe_chiffre text NOT NULL
        );
        """)
    con.commit()


@app.post("/connexion")
def connexion(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authentifier(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur ou phrase de passe invalide")

    return {
        "access_token": creer_jeton_acces(sub=user.nom_utilisateur),
        "token_type": "bearer",
    }


@app.post("/inscription", response_model=MembreBD, status_code=201)
def inscription(form_data: MembreInscription):
    reponse = cursor.execute("SELECT nom_utilisateur FROM membres WHERE nom_utilisateur = ?",
                             (form_data.nom_utilisateur,))
    membre_existant = reponse.fetchone()
    if membre_existant:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà existant")
    passe_chiffre = chiffrer_phrase_de_passe(form_data.passe_clair)
    cursor.execute("INSERT INTO membres(nom_utilisateur, courriel, passe_chiffre) VALUES (?,?,?)",
                   (form_data.nom_utilisateur, form_data.courriel, passe_chiffre))
    reponse = cursor.execute(
        "SELECT nom_utilisateur, courriel, passe_chiffre FROM membres WHERE nom_utilisateur = ?",
        (form_data.nom_utilisateur,))
    tuple_membre = reponse.fetchone()
    con.commit()

    if not tuple_membre:
        raise HTTPException(status_code=400, detail="Il y a eu un problème lors de la création du compte.")

    return MembreBD(nom_utilisateur=tuple_membre[0], courriel=tuple_membre[1], passe_chiffre=tuple_membre[2])


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


@app.get("/identite", response_model=MembreBD)
def me_voir(moi: MembreBD = Depends(recuperer_membre_courant)):
    return moi
