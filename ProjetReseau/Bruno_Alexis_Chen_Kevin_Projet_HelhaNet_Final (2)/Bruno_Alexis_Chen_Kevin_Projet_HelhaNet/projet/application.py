import bcrypt
import secrets
import string

import base_donnees as bd

# Les comptes sont dans la base SQLite (table utilisateur, voir base_donnees.py).
# must_change : 1 = doit changer son MDP à la prochaine connexion
# actif       : 1 = actif, 0 = désactivé (gardé en base)
# Chaque modification est taggée par le numéro d'employé de son auteur.


# ─────────────────────────────────────────────
#  MOT DE PASSE
# ─────────────────────────────────────────────
def hash_mdp(mdp: str) -> bytes:
    return bcrypt.hashpw(mdp.encode(), bcrypt.gensalt(rounds=12))

def verifier_mdp(mdp: str, hash_stocke: str) -> bool:
    return bcrypt.checkpw(mdp.encode(), hash_stocke.encode())

def generer_mdp_temporaire() -> str:
    """MDP simple lisible 8 chars — affiché une seule fois à l'admin."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))

def verifier_robustesse_mdp(mdp: str):
    """Retourne None si le MDP est assez fort, sinon le message d'erreur."""
    if len(mdp) < 8 or " " in mdp \
            or not any(c.islower() for c in mdp) \
            or not any(c.isupper() for c in mdp) \
            or not any(c.isdigit() for c in mdp) \
            or all(c.isalnum() for c in mdp):
        return ("Le mot de passe doit faire au moins 8 caractères, sans espace, avec "
                "une majuscule, une minuscule, un chiffre et un caractère spécial.")
    return None


# ─────────────────────────────────────────────
#  VALIDATION DES SAISIES
# ─────────────────────────────────────────────
def verifier_nom(nom: str):
    if not nom:
        return "Le nom d'utilisateur est obligatoire."
    if len(nom) > 30:
        return "Le nom d'utilisateur fait au maximum 30 caractères."
    return None

def verifier_numero_employe(numero: str):
    if not (numero.isascii() and numero.isdigit() and 1 <= len(numero) <= 10):
        return "Le numéro d'employé doit contenir uniquement des chiffres (10 maximum)."
    return None


# ─────────────────────────────────────────────
#  GESTION UTILISATEURS
# ─────────────────────────────────────────────
def lire_utilisateurs() -> list:
    with bd.ouvrir() as con:
        return [dict(r) for r in con.execute(
            "SELECT numero_employe, nom, role, must_change, actif FROM utilisateur ORDER BY nom")]

def infos_utilisateur(nom: str):
    """État actuel d'un compte (relu en base à chaque appel), ou None."""
    with bd.ouvrir() as con:
        r = con.execute("SELECT numero_employe, nom, role, must_change, actif "
                        "FROM utilisateur WHERE nom = ?", (nom,)).fetchone()
        return dict(r) if r else None

def utilisateur_existe(nom: str) -> bool:
    return infos_utilisateur(nom) is not None

def creer_utilisateur(nom: str, numero_employe: str, role: str, nom_createur: str):
    """
    Crée un utilisateur avec MDP temporaire auto-généré.
    Retourne (True, mdp_en_clair) ou (False, message_erreur).
    must_change=1 force le changement à la première connexion.
    """
    nom, numero_employe = nom.strip(), numero_employe.strip()
    erreur = verifier_nom(nom) or verifier_numero_employe(numero_employe)
    if erreur:
        return False, erreur
    if role not in ("admin", "user"):
        return False, "Rôle invalide."
    mdp_tmp = generer_mdp_temporaire()
    with bd.ouvrir() as con:
        if con.execute("SELECT 1 FROM utilisateur WHERE nom = ?", (nom,)).fetchone():
            return False, f"L'utilisateur « {nom} » existe déjà."
        if con.execute("SELECT 1 FROM utilisateur WHERE numero_employe = ?", (numero_employe,)).fetchone():
            return False, f"Le numéro d'employé {numero_employe} est déjà utilisé."
        con.execute(
            "INSERT INTO utilisateur (numero_employe, nom, hash, role, must_change, cree_par) "
            "VALUES (?, ?, ?, ?, 1, (SELECT numero_employe FROM utilisateur WHERE nom = ?))",
            (numero_employe, nom, hash_mdp(mdp_tmp).decode(), role, nom_createur))
    return True, mdp_tmp

def changer_mdp(nom: str, nouveau_mdp: str):
    erreur = verifier_robustesse_mdp(nouveau_mdp)
    if erreur:
        return False, erreur
    with bd.ouvrir() as con:
        r = con.execute("SELECT numero_employe, hash FROM utilisateur WHERE nom = ?", (nom,)).fetchone()
        if not r:
            return False, "Utilisateur introuvable."
        # Indispensable après le bouton de sécurité : l'ancien MDP a peut-être fuité.
        if verifier_mdp(nouveau_mdp, r["hash"]):
            return False, "Le nouveau mot de passe doit être différent de l'ancien."
        con.execute("UPDATE utilisateur SET hash = ?, must_change = 0, modifie_par = ?, "
                    "modifie_le = CURRENT_TIMESTAMP WHERE nom = ?",
                    (hash_mdp(nouveau_mdp).decode(), r["numero_employe"], nom))
    return True, "Mot de passe changé avec succès."

def basculer_activation(nom_cible: str, nom_actuel: str):
    """Active ou désactive un compte — le garde en base dans tous les cas."""
    if nom_cible == nom_actuel:
        return False, "Vous ne pouvez pas désactiver votre propre compte."
    with bd.ouvrir() as con:
        cur = con.execute(
            "UPDATE utilisateur SET actif = 1 - actif, modifie_le = CURRENT_TIMESTAMP, "
            "modifie_par = (SELECT numero_employe FROM utilisateur WHERE nom = ?) WHERE nom = ?",
            (nom_actuel, nom_cible))
        if cur.rowcount == 0:
            return False, "Utilisateur introuvable."
        actif = con.execute("SELECT actif FROM utilisateur WHERE nom = ?", (nom_cible,)).fetchone()[0]
    return True, f"Compte « {nom_cible} » {'activé' if actif else 'désactivé'}."

def changer_role(nom_cible: str, nouveau_role: str, nom_actuel: str):
    if nouveau_role not in ("admin", "user"):
        return False, "Rôle invalide."
    with bd.ouvrir() as con:
        cible = con.execute("SELECT role, actif FROM utilisateur WHERE nom = ?", (nom_cible,)).fetchone()
        if not cible:
            return False, "Utilisateur introuvable."
        nb_admins = con.execute(
            "SELECT COUNT(*) FROM utilisateur WHERE role = 'admin' AND actif = 1").fetchone()[0]
        if cible["role"] == "admin" and cible["actif"] and nb_admins == 1 and nouveau_role != "admin":
            return False, "Impossible : dernier administrateur actif."
        con.execute(
            "UPDATE utilisateur SET role = ?, modifie_le = CURRENT_TIMESTAMP, "
            "modifie_par = (SELECT numero_employe FROM utilisateur WHERE nom = ?) WHERE nom = ?",
            (nouveau_role, nom_actuel, nom_cible))
    return True, f"Rôle de « {nom_cible} » changé en {nouveau_role}."

def reinitialiser_mdp(nom_cible: str, nom_actuel: str):
    """Génère un nouveau MDP temporaire et force le changement à la prochaine connexion."""
    mdp_tmp = generer_mdp_temporaire()
    with bd.ouvrir() as con:
        cur = con.execute(
            "UPDATE utilisateur SET hash = ?, must_change = 1, modifie_le = CURRENT_TIMESTAMP, "
            "modifie_par = (SELECT numero_employe FROM utilisateur WHERE nom = ?) WHERE nom = ?",
            (hash_mdp(mdp_tmp).decode(), nom_actuel, nom_cible))
        if cur.rowcount == 0:
            return False, "Utilisateur introuvable."
    return True, mdp_tmp


# ─────────────────────────────────────────────
#  BOUTON DE SÉCURITÉ (vol de la base)
# ─────────────────────────────────────────────
# Ce n'est PAS un blocage : les comptes restent actifs, mais chaque utilisateur
# ne peut plus rien faire tant qu'il n'a pas choisi un nouveau MDP (différent de
# l'ancien). Il faut 2 administrateurs différents, à moins de 15 minutes d'écart.
DELAI_CONFIRMATION = "-15 minutes"

def demander_reinit_globale(nom_admin: str):
    """
    1er appel : enregistre la demande. Appel d'un AUTRE admin dans les 15 min :
    tous les comptes doivent changer leur MDP. Retourne (ok, message).
    """
    with bd.ouvrir() as con:
        admin = con.execute("SELECT numero_employe FROM utilisateur "
                            "WHERE nom = ? AND role = 'admin' AND actif = 1", (nom_admin,)).fetchone()
        if not admin:
            return False, "Action réservée aux administrateurs."
        numero = admin[0]
        nb_admins = con.execute(
            "SELECT COUNT(*) FROM utilisateur WHERE role = 'admin' AND actif = 1").fetchone()[0]
        if nb_admins < 2:
            return False, "Il faut au moins 2 administrateurs actifs pour utiliser ce bouton."

        attente = con.execute(
            "SELECT id, demande_par FROM demande_reinit_mdp WHERE confirme_par IS NULL "
            "AND demande_le >= datetime('now', ?) ORDER BY id DESC LIMIT 1",
            (DELAI_CONFIRMATION,)).fetchone()
        if attente is None:
            con.execute("INSERT INTO demande_reinit_mdp (demande_par) VALUES (?)", (numero,))
            return True, ("Demande enregistrée (1/2).\nUn AUTRE administrateur doit cliquer "
                          "sur le bouton dans les 15 minutes pour lancer l'action.")
        if attente["demande_par"] == numero:
            return False, "Vous avez déjà fait la demande : un autre administrateur doit la confirmer."

        con.execute("UPDATE demande_reinit_mdp SET confirme_par = ?, confirme_le = CURRENT_TIMESTAMP "
                    "WHERE id = ?", (numero, attente["id"]))
        nb = con.execute("UPDATE utilisateur SET must_change = 1, modifie_par = ?, "
                         "modifie_le = CURRENT_TIMESTAMP", (numero,)).rowcount
    return True, (f"Action confirmée (2/2) : les {nb} comptes devront changer leur mot de passe "
                  "à la prochaine connexion.\nLes comptes ne sont pas bloqués.")


# ─────────────────────────────────────────────
#  AUTHENTIFICATION
# ─────────────────────────────────────────────
def connexion(nom: str, mdp: str):
    """
    Retourne (statut, role, must_change).
    statut : 'ok' | 'inactif' | 'erreur'
    """
    with bd.ouvrir() as con:
        u = con.execute("SELECT hash, role, must_change, actif FROM utilisateur WHERE nom = ?",
                        (nom.strip(),)).fetchone()
    if not u or not verifier_mdp(mdp, u["hash"]):
        return "erreur", None, False
    if not u["actif"]:
        return "inactif", None, False
    return "ok", u["role"], bool(u["must_change"])

def est_premier_lancement() -> bool:
    with bd.ouvrir() as con:
        return con.execute("SELECT COUNT(*) FROM utilisateur").fetchone()[0] == 0

def sauvegarde_admin_initial(nom: str, numero_employe: str, mdp: str):
    nom, numero_employe = nom.strip(), numero_employe.strip()
    erreur = verifier_nom(nom) or verifier_numero_employe(numero_employe) or verifier_robustesse_mdp(mdp)
    if erreur:
        return False, erreur
    if not est_premier_lancement():
        return False, "Un administrateur existe déjà."
    with bd.ouvrir() as con:
        con.execute("INSERT INTO utilisateur (numero_employe, nom, hash, role, cree_par) "
                    "VALUES (?, ?, ?, 'admin', ?)",
                    (numero_employe, nom, hash_mdp(mdp).decode(), numero_employe))
    return True, "Administrateur créé !"


# ─────────────────────────────────────────────
#  OUTILS RÉSEAU (calculs faits à la main, sans librairie IP)
# ─────────────────────────────────────────────
def ip_vers_entier(ip: str) -> int:
    o = [int(p) for p in ip.split('.')]
    return (o[0] << 24) | (o[1] << 16) | (o[2] << 8) | o[3]

def entier_vers_ip(n: int) -> str:
    return ".".join(str((n >> s) & 0xFF) for s in (24, 16, 8, 0))

def masque_entier(cidr: int) -> int:
    return (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF

def masque_cidr_vers_decimal(cidr: int) -> str:
    return entier_vers_ip(masque_entier(cidr))

def masque_vers_cidr(masque: str) -> int:
    return bin(ip_vers_entier(masque)).count('1')

def generer_donnees_cidr() -> list:
    donnees = []
    for i in range(8, 31):
        bits = '1' * i + '0' * (32 - i)
        octets_bin = [bits[j:j+8] for j in range(0, 32, 8)]
        octets_dec = [str(int(o, 2)) for o in octets_bin]
        donnees.append((f"/{i}", ".".join(octets_bin), ".".join(octets_dec)))
    return donnees

def verifier_format_ip(ip: str) -> bool:
    # Uniquement des chiffres ASCII : refuse "+1", " 2", "-1" que int() acceptait (B2)
    parties = ip.strip().split('.')
    return len(parties) == 4 and all(
        p.isascii() and p.isdigit() and len(p) <= 3 and int(p) <= 255 for p in parties)

def verifier_format_masque(masque: str) -> bool:
    """Vérifie qu'un masque est valide (suite de 1 puis de 0 en binaire)."""
    if not verifier_format_ip(masque):
        return False
    bits = bin(ip_vers_entier(masque))[2:].zfill(32)
    # Un masque valide : tous les 1 sont avant tous les 0
    return '01' not in bits

def lire_masque(texte: str):
    """Accepte « 255.255.255.0 », « /24 » ou « 24 ». Retourne le CIDR ou None."""
    t = texte.strip()
    t = t[1:] if t.startswith('/') else t
    if t.isascii() and t.isdigit():
        return int(t) if int(t) <= 32 else None
    return masque_vers_cidr(t) if verifier_format_masque(t) else None

def prefixe_classe(ip: str):
    """8, 16 ou 24 pour les classes A, B, C ; None pour D et E."""
    premier = int(ip.split('.')[0])
    if premier <= 127: return 8
    if premier <= 191: return 16
    if premier <= 223: return 24
    return None

def definir_classe(ip: str):
    premier = int(ip.split('.')[0])
    if premier == 0:          return "A (réseau courant)", "255.0.0.0"
    if 1 <= premier <= 126:   return "A", "255.0.0.0"
    if premier == 127:        return "A (boucle locale)", "255.0.0.0"
    if 128 <= premier <= 191: return "B", "255.255.0.0"
    if 192 <= premier <= 223: return "C", "255.255.255.0"
    if 224 <= premier <= 239: return "D", "Non applicable (Multicast)"
    return "E", "Non applicable (Expérimental)"

def is_ip_privee(ip: str) -> bool:
    o = [int(p) for p in ip.split('.')]
    return (o[0] == 10) or \
           (o[0] == 172 and 16 <= o[1] <= 31) or \
           (o[0] == 192 and o[1] == 168)

def is_ip_reservee(ip: str):
    """Adresses à usage particulier (ni publiques, ni privées)."""
    o = [int(p) for p in ip.split('.')]
    if o[0] == 0:                       return True, "Réseau courant (This network)"
    if o[0] == 127:                     return True, "Boucle locale (Loopback)"
    if o[0] == 169 and o[1] == 254:     return True, "APIPA (Link-local)"
    if o == [255, 255, 255, 255]:       return True, "Broadcast global"
    if 224 <= o[0] <= 239:              return True, "Multicast (classe D)"
    if o[0] >= 240:                     return True, "Expérimental (classe E)"
    return False, ""

def type_adresse(ip: str) -> str:
    """Une adresse non privée n'est pas forcément publique (B5)."""
    if is_ip_privee(ip):
        return "Adresse Privée"
    if is_ip_reservee(ip)[0]:
        return "Usage particulier (ni publique, ni privée)"
    return "Adresse Publique"

def role_avec_masque_classe(ip: str):
    """Rôle de l'IP si on lui applique son masque de classe (B6). None pour D/E."""
    prefixe = prefixe_classe(ip)
    if prefixe is None:
        return None
    partie_hote = ip_vers_entier(ip) & ~masque_entier(prefixe) & 0xFFFFFFFF
    if partie_hote == 0:
        return "Adresse réseau"
    if partie_hote == (1 << (32 - prefixe)) - 1:
        return "Adresse de broadcast"
    return "Adresse d'hôte"

def meme_reseau(ip1: str, ip2: str, cidr: int) -> dict:
    """Vu avec le masque /cidr : les deux IP ont-elles la même adresse réseau ?"""
    masque_int  = masque_entier(cidr)
    reseau1_int = ip_vers_entier(ip1) & masque_int
    reseau2_int = ip_vers_entier(ip2) & masque_int
    broadcast_int = reseau1_int | (~masque_int & 0xFFFFFFFF)
    return {
        "masque":      masque_cidr_vers_decimal(cidr),
        "reseau_ip1":  entier_vers_ip(reseau1_int),
        "reseau_ip2":  entier_vers_ip(reseau2_int),
        "broadcast":   entier_vers_ip(broadcast_int),
        "meme_reseau": reseau1_int == reseau2_int,
    }

def comparer_bilateral(ip1: str, cidr1: int, ip2: str, cidr2: int) -> dict:
    """
    Chaque machine applique SON masque aux deux adresses (B1) :
    la machine 1 peut voir la 2 dans son sous-réseau sans que l'inverse soit vrai.
    """
    p1, p2 = prefixe_classe(ip1), prefixe_classe(ip2)
    meme_classe = None
    if p1 is not None and p1 == p2:
        meme_classe = meme_reseau(ip1, ip2, p1)["meme_reseau"]
    elif p1 is not None and p2 is not None:
        meme_classe = False
    return {
        "meme_reseau_classe": meme_classe,          # None si une IP est de classe D/E
        "vue_ip1": meme_reseau(ip1, ip2, cidr1),
        "vue_ip2": meme_reseau(ip2, ip1, cidr2),
    }

def verifier_classfull(ip: str, masque: str):
    """Retourne None si le calcul classful a du sens, sinon le message d'erreur."""
    prefixe = prefixe_classe(ip)
    if prefixe is None:
        return "Pas de réseau de classe pour une adresse de classe D ou E."
    if masque_vers_cidr(masque) < prefixe:
        return (f"Le masque est plus court que le masque de classe (/{prefixe}) : "
                "ce n'est pas un sous-réseau.")
    return None

def calculer_reseau_classfull(ip: str, masque: str) -> dict:
    ip_int     = ip_vers_entier(ip)
    masque_int = ip_vers_entier(masque)
    cidr       = masque_vers_cidr(masque)

    # Adresse réseau = IP AND masque
    reseau_int     = ip_int & masque_int
    # Broadcast = réseau OR (NOT masque)
    broadcast_int  = reseau_int | (~masque_int & 0xFFFFFFFF)

    # Masque de classe naturel (classfull)
    classe, masque_classe = definir_classe(ip)
    prefixe = prefixe_classe(ip)
    masque_classe_int = masque_entier(prefixe) if prefixe else masque_int

    # /31 et /32 : pas d'hôte utilisable, on n'affiche pas de plage inversée (B3, B4)
    if cidr >= 31:
        premiere = derniere = "Aucune (masque /31 ou /32)"
        nb_hotes = 0
    else:
        premiere = entier_vers_ip(reseau_int + 1)
        derniere = entier_vers_ip(broadcast_int - 1)
        nb_hotes = 2 ** (32 - cidr) - 2

    return {
        "ip":              ip,
        "masque":          masque,
        "cidr":            cidr,
        "classe":          classe,
        "masque_classe":   entier_vers_ip(masque_classe_int),
        "reseau_classe":   entier_vers_ip(ip_int & masque_classe_int),
        "reseau":          entier_vers_ip(reseau_int),
        "broadcast":       entier_vers_ip(broadcast_int),
        "premiere_hote":   premiere,
        "derniere_hote":   derniere,
        "nb_hotes":        nb_hotes,
    }


# ─────────────────────────────────────────────
#  DÉCOUPE EN SOUS-RÉSEAUX (nombre de SR souhaités)
# ─────────────────────────────────────────────
NB_SR_MAX = 1024   # au-delà, l'affichage et la base deviennent illisibles

def decouper_reseau(ip: str, cidr: int, nb_sr: int):
    """
    Découpe classique : on emprunte n bits à la partie hôte, avec 2^n >= nb_sr.
    Retourne (True, résultat) ou (False, message_erreur).
    """
    if not 1 <= nb_sr <= NB_SR_MAX:
        return False, f"Le nombre de sous-réseaux doit être entre 1 et {NB_SR_MAX}."
    bits = 0
    while (1 << bits) < nb_sr:
        bits += 1
    nouveau_cidr = cidr + bits
    if nouveau_cidr > 30:
        return False, (f"Impossible : il faudrait un masque /{nouveau_cidr}, "
                       "il ne resterait pas 2 hôtes par sous-réseau.")

    base   = ip_vers_entier(ip) & masque_entier(cidr)
    taille = 1 << (32 - nouveau_cidr)      # adresses par sous-réseau
    sous_reseaux = []
    for i in range(nb_sr):
        reseau = base + i * taille
        broadcast = reseau + taille - 1
        sous_reseaux.append({
            "numero":        i + 1,
            "reseau":        entier_vers_ip(reseau),
            "premiere_hote": entier_vers_ip(reseau + 1),
            "derniere_hote": entier_vers_ip(broadcast - 1),
            "broadcast":     entier_vers_ip(broadcast),
        })
    return True, {
        "reseau":          entier_vers_ip(base),
        "cidr":            cidr,
        "bits_empruntes":  bits,
        "nouveau_cidr":    nouveau_cidr,
        "nouveau_masque":  masque_cidr_vers_decimal(nouveau_cidr),
        "nb_sr_possibles": 1 << bits,
        "hotes_par_sr":    taille - 2,
        "sous_reseaux":    sous_reseaux,
    }
