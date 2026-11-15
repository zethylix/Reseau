HELHA.net - Phase 2
===================

Logiciel de gestion de réseau IP (Python, interface Tkinter, base SQLite 3).
Projet de phase 1 repris de Bruno Alexis et Chen Kevin, puis corrigé et complété
en phase 2 par Demaret Mateo et Nayo Noah.


INSTALLATION
------------

Il faut Python 3 (testé avec Python 3.11). Tkinter et SQLite sont fournis avec
Python sous Windows. La seule bibliothèque à installer est bcrypt (hachage des
mots de passe) :

    pip install -r requirements.txt


LANCEMENT
---------

    python interface.py


PREMIER LANCEMENT
-----------------

Au premier lancement, aucun compte n'existe : l'application crée la base
helhanet.db dans ce dossier et demande de créer le compte administrateur
(nom, numéro d'employé, mot de passe).

Le mot de passe doit faire au moins 8 caractères, sans espace, avec une
majuscule, une minuscule, un chiffre et un caractère spécial.

Aucune base n'est livrée avec le projet : il n'y a donc pas de compte dont le
mot de passe serait inconnu.


COMPTES
-------

- Créer un compte (administrateurs uniquement) : menu Utilisateurs, puis
  "+ Créer". Un mot de passe temporaire s'affiche une seule fois (bouton
  Copier). L'utilisateur le change à sa première connexion.
- Gérer les comptes : changer le rôle, activer ou désactiver, réinitialiser
  le mot de passe.
- Bouton de sécurité (en cas de vol de la base) : un administrateur le
  demande, un AUTRE administrateur le confirme dans les 15 minutes. Tous les
  utilisateurs devront alors choisir un nouveau mot de passe, sans que leur
  compte soit bloqué.


FONCTIONNALITÉS
---------------

  Tableau CIDR             F1 : masques de /8 à /30 (CIDR, binaire, décimal)
  Format IP                F2 : vérifie qu'une adresse IP est bien écrite
  Classe IP                F3 : classe, privée / publique / usage particulier
  Masque de classe         F4 : masque de classe de l'adresse
  Réseau / Sous-réseau     F5 : réseau de classe et sous-réseau (historique
                                modifiable)
  Même réseau ?            F6 : deux IP avec chacune leur masque, vérification
                                dans les deux sens (historique modifiable)
  Découpe en sous-réseaux  découpe selon le nombre de sous-réseaux voulu
                           (nombre d'hôtes facultatif), avec un historique

Les masques s'écrivent au choix 255.255.255.0, /24 ou 24. Chaque utilisation
est enregistrée dans la base avec le numéro d'employé de la personne connectée.


TESTS AUTOMATIQUES
------------------

    python -m unittest test_application -v

23 tests : cas T01 à T20 de la fiche de recette, bugs corrigés, droits des
administrateurs, dates, découpe et base de données. Les tests utilisent une
base temporaire et ne touchent pas à helhanet.db.


FICHIERS
--------

  interface.py         interface graphique (fichier à lancer)
  application.py       calculs réseau, comptes et mots de passe
  base_donnees.py      schéma SQLite et enregistrements
  test_application.py  tests automatiques
  requirements.txt     bibliothèque à installer (bcrypt)
  helhanet.db          base créée au premier lancement (à sauvegarder, à ne
                       pas partager)

Si helhanet.db est supprimé, l'application repasse en mode "premier
lancement". Pensez à sauvegarder ce fichier et à limiter les droits Windows
sur le dossier.
