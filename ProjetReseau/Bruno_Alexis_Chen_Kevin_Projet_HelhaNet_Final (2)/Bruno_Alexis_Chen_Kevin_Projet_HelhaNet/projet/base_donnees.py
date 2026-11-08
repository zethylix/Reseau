"""

Règles du client :
- Chaque ligne garde le numéro de l'employé qui l'a créée (cree_par).
- F1 (tableau CIDR) : on garde aussi le résultat (ligne_tableau_cidr).
- F2 à F6 : on garde seulement les saisies, les résultats se recalculent.
- F5 et F6 : on garde aussi le dernier employé qui a modifié la ligne (modifie_par).
- Les découpes en sous-réseaux sont stockées avec leurs sous-réseaux.
"""
import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "helhanet.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateur (
    numero_employe TEXT PRIMARY KEY,
    nom            TEXT NOT NULL UNIQUE,
    hash           TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    must_change    INTEGER NOT NULL DEFAULT 0,   -- 1 = doit changer son MDP à la connexion
    actif          INTEGER NOT NULL DEFAULT 1,   -- 0 = compte bloqué par un admin
    cree_par       TEXT REFERENCES utilisateur(numero_employe),
    cree_le        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modifie_par    TEXT REFERENCES utilisateur(numero_employe),
    modifie_le     TEXT
);

-- Bouton de sécurité : une demande d'un admin, confirmée par un AUTRE admin.
CREATE TABLE IF NOT EXISTS demande_reinit_mdp (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    demande_par  TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    demande_le   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirme_par TEXT REFERENCES utilisateur(numero_employe),
    confirme_le  TEXT,
    CHECK (confirme_par IS NULL OR confirme_par <> demande_par)
);

-- F1 : tableau des masques (résultat stocké)
CREATE TABLE IF NOT EXISTS tableau_cidr (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    cree_par TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    cree_le  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ligne_tableau_cidr (
    id_tableau     INTEGER NOT NULL REFERENCES tableau_cidr(id) ON DELETE CASCADE,
    prefixe        INTEGER NOT NULL,
    masque_binaire TEXT NOT NULL,
    masque_decimal TEXT NOT NULL,
    PRIMARY KEY (id_tableau, prefixe)
);

-- F2 : vérification du format d'une IP (saisie brute, même invalide)
CREATE TABLE IF NOT EXISTS verification_ip (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_saisie TEXT NOT NULL,
    cree_par  TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    cree_le   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- F3 : classe d'une IP
CREATE TABLE IF NOT EXISTS classe_ip (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ip       TEXT NOT NULL,
    cree_par TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    cree_le  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- F4 : masque de classe d'une IP
CREATE TABLE IF NOT EXISTS masque_classe (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ip       TEXT NOT NULL,
    cree_par TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    cree_le  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- F5 : réseau et sous-réseau (classful) — modifiable
CREATE TABLE IF NOT EXISTS reseau_classfull (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ip          TEXT NOT NULL,
    masque      TEXT NOT NULL,
    cree_par    TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    cree_le     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modifie_par TEXT REFERENCES utilisateur(numero_employe),
    modifie_le  TEXT
);

-- F6 : deux IP dans le même réseau ? — modifiable
CREATE TABLE IF NOT EXISTS comparaison_ip (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ip1         TEXT NOT NULL,
    masque1     TEXT NOT NULL,
    ip2         TEXT NOT NULL,
    masque2     TEXT NOT NULL,
    cree_par    TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    cree_le     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modifie_par TEXT REFERENCES utilisateur(numero_employe),
    modifie_le  TEXT
);

-- Nouvelle fonctionnalité : découpe selon le nombre de sous-réseaux
CREATE TABLE IF NOT EXISTS decoupe (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ip             TEXT NOT NULL,
    masque         TEXT NOT NULL,
    nb_sr_demandes INTEGER NOT NULL,
    nouveau_masque TEXT NOT NULL,
    cree_par       TEXT NOT NULL REFERENCES utilisateur(numero_employe),
    cree_le        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sous_reseau (
    id_decoupe     INTEGER NOT NULL REFERENCES decoupe(id) ON DELETE CASCADE,
    numero         INTEGER NOT NULL,
    adresse_reseau TEXT NOT NULL,
    premiere_hote  TEXT NOT NULL,
    derniere_hote  TEXT NOT NULL,
    broadcast      TEXT NOT NULL,
    PRIMARY KEY (id_decoupe, numero)
);
"""

# Tables qu'on peut remplir avec inserer() / modifier() / lister().
# Les noms viennent du code, jamais de l'utilisateur.
TABLES_HISTORIQUE = {"verification_ip", "classe_ip", "masque_classe",
                     "reseau_classfull", "comparaison_ip"}
TABLES_MODIFIABLES = {"reseau_classfull", "comparaison_ip"}


@contextmanager
def ouvrir():
    """Ouvre la base (créée au besoin), valide à la sortie, annule en cas d'erreur."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA)
        with con:
            yield con
    finally:
        con.close()


def inserer(table: str, numero_employe: str, **valeurs) -> int:
    """Ajoute une ligne taggée par l'employé ; retourne son id."""
    assert table in TABLES_HISTORIQUE
    colonnes = ", ".join(list(valeurs) + ["cree_par"])
    marques  = ", ".join("?" * (len(valeurs) + 1))
    with ouvrir() as con:
        cur = con.execute(f"INSERT INTO {table} ({colonnes}) VALUES ({marques})",
                          (*valeurs.values(), numero_employe))
        return cur.lastrowid


def modifier(table: str, id_ligne: int, numero_employe: str, **valeurs) -> bool:
    """Modifie une ligne de F5/F6 et retient qui l'a modifiée en dernier."""
    assert table in TABLES_MODIFIABLES
    affectations = ", ".join(f"{c} = ?" for c in valeurs)
    with ouvrir() as con:
        cur = con.execute(
            f"UPDATE {table} SET {affectations}, modifie_par = ?, modifie_le = CURRENT_TIMESTAMP "
            f"WHERE id = ?", (*valeurs.values(), numero_employe, id_ligne))
        return cur.rowcount == 1


def lister(table: str, limite: int = 50) -> list:
    """Dernières lignes d'une table d'historique (plus récentes d'abord)."""
    assert table in TABLES_HISTORIQUE
    with ouvrir() as con:
        return [dict(r) for r in con.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limite,))]


def enregistrer_tableau_cidr(numero_employe: str, lignes: list) -> int:
    """F1 : enregistre le tableau affiché (résultat compris)."""
    with ouvrir() as con:
        id_tableau = con.execute("INSERT INTO tableau_cidr (cree_par) VALUES (?)",
                                 (numero_employe,)).lastrowid
        con.executemany(
            "INSERT INTO ligne_tableau_cidr VALUES (?, ?, ?, ?)",
            [(id_tableau, int(cidr.lstrip("/")), binaire, decimal) for cidr, binaire, decimal in lignes])
        return id_tableau


def enregistrer_decoupe(numero_employe: str, ip: str, masque: str, nb_sr: int, resultat: dict) -> int:
    """Enregistre une découpe et ses sous-réseaux."""
    with ouvrir() as con:
        id_decoupe = con.execute(
            "INSERT INTO decoupe (ip, masque, nb_sr_demandes, nouveau_masque, cree_par) "
            "VALUES (?, ?, ?, ?, ?)",
            (ip, masque, nb_sr, resultat["nouveau_masque"], numero_employe)).lastrowid
        con.executemany(
            "INSERT INTO sous_reseau VALUES (?, ?, ?, ?, ?, ?)",
            [(id_decoupe, sr["numero"], sr["reseau"], sr["premiere_hote"], sr["derniere_hote"], sr["broadcast"])
             for sr in resultat["sous_reseaux"]])
        return id_decoupe
