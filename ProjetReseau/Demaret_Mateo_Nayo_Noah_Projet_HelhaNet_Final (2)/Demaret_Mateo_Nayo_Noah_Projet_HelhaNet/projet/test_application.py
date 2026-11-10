"""
Tests automatiques — lancer avec :  python -m unittest test_application -v
Reprennent les cas T01 à T20 de la fiche de recette, les bugs B1 à B6,
la découpe en sous-réseaux et la base SQLite (sur une base temporaire).
"""
import os
import shutil
import tempfile
import unittest

import application as app
import base_donnees as bd


class TestReseau(unittest.TestCase):

    # Dates : stockées en UTC, affichées avec le décalage de la saison
    def test_date_locale(self):
        from datetime import timedelta, timezone
        hiver, ete = timezone(timedelta(hours=1)), timezone(timedelta(hours=2))
        self.assertEqual(app.date_locale("2026-11-09 10:05:00", hiver), "2026-11-09 11:05:00 (UTC+1)")
        self.assertEqual(app.date_locale("2026-07-01 23:30:00", ete), "2026-07-02 01:30:00 (UTC+2)")
        self.assertEqual(app.date_locale(None), "")

    # T01 — tableau CIDR
    def test_t01_tableau_cidr(self):
        lignes = app.generer_donnees_cidr()
        self.assertEqual(len(lignes), 23)
        self.assertEqual(lignes[0], ("/8", "11111111.00000000.00000000.00000000", "255.0.0.0"))
        self.assertEqual(lignes[-1], ("/30", "11111111.11111111.11111111.11111100", "255.255.255.252"))

    # T02-T06 + B2 — format IPv4
    def test_t02_t06_b2_ip_invalides(self):
        for ip in ["a.b.c.d", "256.0.0.0", "-1.1.1.1", "192.168.12.0.1", "192.168.12",
                   "+1.2.3.4", "1. 2.3.4", "1..2.3", "", "١.2.3.4"]:
            self.assertFalse(app.verifier_format_ip(ip), ip)
        for ip in ["192.168.1.1", " 10.0.0.1 ", "0.0.0.0", "255.255.255.255"]:
            self.assertTrue(app.verifier_format_ip(ip), ip)

    # T07-T10 + B5 — classe et type
    def test_t07_t10_b5_classe_et_type(self):
        self.assertEqual(app.definir_classe("5.5.5.5")[0], "A")
        self.assertEqual(app.type_adresse("5.5.5.5"), "Adresse Publique")
        self.assertEqual(app.definir_classe("192.168.1.0")[0], "C")
        self.assertEqual(app.type_adresse("192.168.1.0"), "Adresse Privée")
        self.assertIn("A", app.definir_classe("127.0.0.1")[0])
        self.assertTrue(app.is_ip_reservee("127.0.0.1")[0])
        self.assertNotIn("Publique", app.type_adresse("127.0.0.1"))
        self.assertEqual(app.definir_classe("225.1.4.3")[0], "D")
        self.assertNotIn("Publique", app.type_adresse("225.1.4.3"))
        self.assertIn("A", app.definir_classe("0.1.2.3")[0])   # 0.x n'est pas de classe E

    # T11-T14 — masque de classe
    def test_t11_t14_masque_classe(self):
        self.assertEqual(app.definir_classe("5.5.5.5")[1], "255.0.0.0")
        self.assertEqual(app.definir_classe("128.2.3.4")[1], "255.255.0.0")
        self.assertEqual(app.definir_classe("192.168.1.0")[1], "255.255.255.0")
        self.assertIn("Non applicable", app.definir_classe("225.1.4.3")[1])

    # B6 — rôle de l'adresse avec le masque de classe
    def test_b6_role_masque_classe(self):
        self.assertEqual(app.role_avec_masque_classe("192.168.1.0"), "Adresse réseau")
        self.assertEqual(app.role_avec_masque_classe("192.168.1.255"), "Adresse de broadcast")
        self.assertEqual(app.role_avec_masque_classe("192.168.1.7"), "Adresse d'hôte")
        self.assertIsNone(app.role_avec_masque_classe("225.1.4.3"))

    # T15-T17 — réseau et sous-réseau classful
    def test_t15_t17_classfull(self):
        for ip, masque, reseau, sous_reseau in [
            ("5.5.5.5",       "255.255.0.0",     "5.0.0.0",     "5.5.0.0"),
            ("192.168.2.166", "255.255.255.128", "192.168.2.0", "192.168.2.128"),
            ("192.168.1.126", "255.255.255.0",   "192.168.1.0", "192.168.1.0"),
        ]:
            r = app.calculer_reseau_classfull(ip, masque)
            self.assertEqual(r["reseau_classe"], reseau)
            self.assertEqual(r["reseau"], sous_reseau)

    def test_classfull_127_reste_classe_a(self):
        self.assertIn("A", app.calculer_reseau_classfull("127.0.0.1", "255.0.0.0")["classe"])

    # B3/B4 — /31 et /32 : plus de plage inversée
    def test_b3_b4_pas_de_plage_inversee(self):
        for masque in ["255.255.255.254", "255.255.255.255"]:
            r = app.calculer_reseau_classfull("192.168.1.10", masque)
            self.assertEqual(r["nb_hotes"], 0)
            self.assertNotIn(".", r["premiere_hote"])
            self.assertNotIn(".", r["derniere_hote"])

    def test_classfull_refus(self):
        self.assertIsNotNone(app.verifier_classfull("225.1.4.3", "255.255.255.0"))
        self.assertIsNotNone(app.verifier_classfull("192.168.1.1", "255.255.0.0"))
        self.assertIsNone(app.verifier_classfull("192.168.1.1", "255.255.255.128"))

    # T18-T20 + B1 — comparaison bilatérale avec un masque par machine
    def test_t18_t20_b1_bilateral(self):
        r = app.comparer_bilateral("192.168.1.10", 24, "192.168.1.5", 24)
        self.assertTrue(r["meme_reseau_classe"])
        self.assertTrue(r["vue_ip1"]["meme_reseau"])
        self.assertTrue(r["vue_ip2"]["meme_reseau"])

        r = app.comparer_bilateral("192.168.1.129", 25, "192.168.1.5", 24)
        self.assertTrue(r["meme_reseau_classe"])
        self.assertFalse(r["vue_ip1"]["meme_reseau"])
        self.assertTrue(r["vue_ip2"]["meme_reseau"])

        r = app.comparer_bilateral("192.168.1.10", 24, "192.168.1.130", 25)
        self.assertTrue(r["vue_ip1"]["meme_reseau"])
        self.assertFalse(r["vue_ip2"]["meme_reseau"])

        r = app.comparer_bilateral("10.0.0.1", 8, "11.0.0.1", 8)
        self.assertFalse(r["meme_reseau_classe"])

    def test_lire_masque(self):
        self.assertEqual(app.lire_masque("255.255.255.0"), 24)
        self.assertEqual(app.lire_masque("/25"), 25)
        self.assertEqual(app.lire_masque("16"), 16)
        for mauvais in ["255.0.255.0", "33", "abc", "", "-1"]:
            self.assertIsNone(app.lire_masque(mauvais), mauvais)

    # Nouvelle fonctionnalité — découpe selon le nombre de SR
    def test_decoupe_classe_c(self):
        ok, r = app.decouper_reseau("192.168.1.0", 24, 3)
        self.assertTrue(ok)
        self.assertEqual(r["bits_empruntes"], 2)
        self.assertEqual(r["nouveau_masque"], "255.255.255.192")
        self.assertEqual(r["nb_sr_possibles"], 4)
        self.assertEqual(r["hotes_par_sr"], 62)
        self.assertEqual(len(r["sous_reseaux"]), 3)
        sr3 = r["sous_reseaux"][2]
        self.assertEqual((sr3["reseau"], sr3["premiere_hote"], sr3["derniere_hote"], sr3["broadcast"]),
                         ("192.168.1.128", "192.168.1.129", "192.168.1.190", "192.168.1.191"))

    def test_decoupe_classe_a_ip_quelconque(self):
        ok, r = app.decouper_reseau("10.20.30.40", 8, 5)
        self.assertTrue(ok)
        self.assertEqual(r["reseau"], "10.0.0.0")
        self.assertEqual(r["nouveau_cidr"], 11)
        self.assertEqual(r["sous_reseaux"][1]["reseau"], "10.32.0.0")

    def test_decoupe_impossible(self):
        self.assertFalse(app.decouper_reseau("192.168.1.0", 24, 100)[0])
        self.assertFalse(app.decouper_reseau("192.168.1.0", 24, 0)[0])

    def test_decoupe_nombre_hotes(self):
        # /24 en 3 SR -> /26 : 62 hôtes max par sous-réseau
        ok, r = app.decouper_reseau("192.168.1.0", 24, 3)            # vide : pas de contrainte
        self.assertTrue(ok); self.assertIsNone(r["nb_hotes_demandes"]); self.assertEqual(r["hotes_par_sr"], 62)
        ok, r = app.decouper_reseau("192.168.1.0", 24, 3, 62)        # limite exacte
        self.assertTrue(ok); self.assertEqual(r["nb_hotes_demandes"], 62)
        ok, msg = app.decouper_reseau("192.168.1.0", 24, 3, 63)      # un de trop
        self.assertFalse(ok); self.assertIn("62", msg)
        self.assertFalse(app.decouper_reseau("192.168.1.0", 24, 3, 0)[0])


class TestBase(unittest.TestCase):

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.ancien_chemin = bd.DB_PATH
        bd.DB_PATH = os.path.join(self.dossier, "test.db")

    def tearDown(self):
        bd.DB_PATH = self.ancien_chemin
        shutil.rmtree(self.dossier, ignore_errors=True)

    def _admin(self):
        ok, msg = app.sauvegarde_admin_initial("alice", "1001", "Secret#2026")
        self.assertTrue(ok, msg)

    def test_premier_lancement_et_connexion(self):
        self.assertTrue(app.est_premier_lancement())
        self.assertFalse(app.sauvegarde_admin_initial("alice", "1001", "faible")[0])
        self.assertFalse(app.sauvegarde_admin_initial("alice", "abc", "Secret#2026")[0])
        self._admin()
        self.assertFalse(app.est_premier_lancement())
        self.assertEqual(app.connexion("alice", "Secret#2026"), ("ok", "admin", False))
        self.assertEqual(app.connexion("alice", "mauvais")[0], "erreur")

    def test_creation_taggee_et_mdp(self):
        self._admin()
        ok, mdp_tmp = app.creer_utilisateur("bob", "2002", "user", "alice")
        self.assertTrue(ok)
        self.assertFalse(app.creer_utilisateur("bob", "2003", "user", "alice")[0])   # nom déjà pris
        self.assertFalse(app.creer_utilisateur("carl", "2002", "user", "alice")[0])  # numéro déjà pris
        self.assertEqual(app.connexion("bob", mdp_tmp), ("ok", "user", True))
        with bd.ouvrir() as con:
            self.assertEqual(con.execute("SELECT cree_par FROM utilisateur WHERE nom='bob'").fetchone()[0], "1001")
        self.assertFalse(app.changer_mdp("bob", "court")[0])
        self.assertFalse(app.changer_mdp("bob", mdp_tmp)[0])
        self.assertTrue(app.changer_mdp("bob", "Nouveau#2026")[0])
        self.assertFalse(app.changer_mdp("bob", "Nouveau#2026")[0])  # identique à l'ancien
        self.assertEqual(app.connexion("bob", "Nouveau#2026"), ("ok", "user", False))

    def test_role_rafraichi(self):
        self._admin()
        app.creer_utilisateur("bob", "2002", "admin", "alice")
        self.assertTrue(app.changer_role("alice", "user", "bob")[0])
        self.assertEqual(app.infos_utilisateur("alice")["role"], "user")
        self.assertFalse(app.changer_role("bob", "user", "bob")[0])  # dernier admin actif

    def test_admin_retrograde_ne_gere_plus_les_comptes(self):
        """B10 : les droits sont relus en base à chaque action, pas seulement à la connexion."""
        self._admin()
        app.creer_utilisateur("bob", "2002", "admin", "alice")
        _, mdp_carl = app.creer_utilisateur("carl", "3003", "user", "alice")
        self.assertTrue(app.changer_role("alice", "user", "bob")[0])   # bob rétrograde alice

        self.assertFalse(app.creer_utilisateur("eve", "4004", "admin", "alice")[0])
        self.assertFalse(app.reinitialiser_mdp("carl", "alice")[0])
        self.assertFalse(app.basculer_activation("carl", "alice")[0])
        self.assertFalse(app.changer_role("carl", "admin", "alice")[0])
        self.assertFalse(app.demander_reinit_globale("alice")[0])

        self.assertIsNone(app.infos_utilisateur("eve"))
        self.assertEqual(app.connexion("carl", mdp_carl)[0], "ok")      # MDP inchangé
        self.assertEqual(app.infos_utilisateur("carl")["role"], "user")
        self.assertTrue(app.infos_utilisateur("carl")["actif"])

    def test_bouton_securite_deux_admins(self):
        self._admin()
        self.assertFalse(app.demander_reinit_globale("alice")[0])  # un seul admin
        app.creer_utilisateur("bob", "2002", "admin", "alice")
        app.creer_utilisateur("carl", "3003", "user", "alice")
        app.changer_mdp("bob", "Bob#Pass2026")
        app.changer_mdp("carl", "Carl#Pass2026")
        app.basculer_activation("carl", "alice")  # carl désactivé
        self.assertFalse(app.demander_reinit_globale("carl")[0])  # pas admin

        self.assertTrue(app.demander_reinit_globale("alice")[0])
        self.assertFalse(app.demander_reinit_globale("alice")[0])  # même admin
        self.assertFalse(app.infos_utilisateur("bob")["must_change"])
        self.assertTrue(app.demander_reinit_globale("bob")[0])     # second admin confirme

        for nom in ["alice", "bob", "carl"]:
            self.assertTrue(app.infos_utilisateur(nom)["must_change"], nom)
        self.assertTrue(app.infos_utilisateur("bob")["actif"])     # pas bloqué
        self.assertFalse(app.infos_utilisateur("carl")["actif"])   # reste désactivé
        self.assertEqual(app.connexion("bob", "Bob#Pass2026"), ("ok", "admin", True))

    def test_historique_f1_a_f6(self):
        self._admin()
        app.creer_utilisateur("bob", "2002", "user", "alice")
        bd.enregistrer_tableau_cidr("1001", app.generer_donnees_cidr())
        bd.inserer("verification_ip", "1001", ip_saisie="a.b.c.d", valide=0)
        bd.inserer("verification_ip", "1001", ip_saisie="10.0.0.1", valide=1)
        bd.inserer("classe_ip", "1001", ip="5.5.5.5")
        bd.inserer("masque_classe", "1001", ip="5.5.5.5")
        id_f5 = bd.inserer("reseau_classfull", "1001", ip="5.5.5.5", masque="255.255.0.0")
        id_f5b = bd.modifier("reseau_classfull", id_f5, "2002", ip="5.5.5.6", masque="255.255.0.0")
        id_f6 = bd.inserer("comparaison_ip", "1001", ip1="192.168.1.10", masque1="255.255.255.0",
                           ip2="192.168.1.5", masque2="255.255.255.0")
        bd.modifier("comparaison_ip", id_f6, "2002", ip1="192.168.1.11", masque1="255.255.255.0",
                    ip2="192.168.1.5", masque2="255.255.255.0")
        self.assertIsNone(bd.modifier("reseau_classfull", 999, "2002", ip="1.1.1.1", masque="255.0.0.0"))
        with bd.ouvrir() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM ligne_tableau_cidr").fetchone()[0], 23)
            # F2 : le résultat est un booléen 0/1, toute autre valeur est refusée
            self.assertEqual([r[0] for r in con.execute("SELECT valide FROM verification_ip ORDER BY id")], [0, 1])
            with self.assertRaises(Exception):
                con.execute("INSERT INTO verification_ip (ip_saisie, valide, cree_par) VALUES ('x', 2, '1001')")
            # Une modification ajoute une version : l'originale reste intacte
            f5 = [tuple(r) for r in con.execute(
                "SELECT id, ip, cree_par, modifie_par, modifie_depuis FROM reseau_classfull ORDER BY id")]
            self.assertEqual(f5, [(id_f5, "5.5.5.5", "1001", None, None),
                                  (id_f5b, "5.5.5.6", "1001", "2002", id_f5)])
            f6 = [tuple(r) for r in con.execute(
                "SELECT ip1, cree_par, modifie_par FROM comparaison_ip ORDER BY id")]
            self.assertEqual(f6, [("192.168.1.10", "1001", None), ("192.168.1.11", "1001", "2002")])
        self.assertEqual(bd.lister("reseau_classfull")[0]["modifie_par"], "2002")

    def test_decoupe_enregistree(self):
        self._admin()
        ok, r = app.decouper_reseau("192.168.1.0", 24, 3, 50)
        id_decoupe = bd.enregistrer_decoupe("1001", "192.168.1.0", "255.255.255.0", 3, r)
        with bd.ouvrir() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sous_reseau").fetchone()[0], 3)
            self.assertEqual(tuple(con.execute(
                "SELECT nouveau_masque, nb_hotes_demandes, hotes_par_sr FROM decoupe").fetchone()),
                ("255.255.255.192", 50, 62))
        # Historique : la découpe et ses sous-réseaux se relisent depuis la base
        self.assertEqual(bd.lister("decoupe")[0]["id"], id_decoupe)
        self.assertEqual([s["adresse_reseau"] for s in bd.sous_reseaux(id_decoupe)],
                         ["192.168.1.0", "192.168.1.64", "192.168.1.128"])


if __name__ == "__main__":
    unittest.main()
