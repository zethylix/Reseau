import os
import sqlite3
import tkinter as tk
import traceback
from tkinter import messagebox, ttk
import application
import base_donnees as bd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FOND   = "#DDE1E6"
ROUGE  = "#C24141"
VERT   = "#2E8B57"
GRIS   = "#4B5563"
NOIR   = "#1F2937"

MSG_IP_INVALIDE = "✘  IP invalide : 4 nombres de 0 à 255 séparés par des points"


class AppHelha:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.report_callback_exception = self._erreur_inattendue
        self.root.title("HELHA.net")
        self.root.geometry("1000x680")
        # E1 : fenêtre redimensionnable, ouverte en grand
        # (660 px de haut minimum : le menu admin compte 8 entrées depuis B15)
        self.root.minsize(900, 660)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass
        self.root.configure(bg="#E9ECEF")

        try:
            self.logo_img  = tk.PhotoImage(file=os.path.join(BASE_DIR, "logo.png"))
            self.logoMenu2 = tk.PhotoImage(file=os.path.join(BASE_DIR, "logoMenu2.png"))
        except Exception:
            self.logo_img  = None
            self.logoMenu2 = None

        try:
            self.root.iconbitmap(os.path.join(BASE_DIR, "icone.ico"))
        except Exception:
            pass

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#E9ECEF", fieldbackground="#E9ECEF",
                        rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background="#1F4E8C", foreground="white",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview",
                  background=[("selected", "#1F4E8C")],
                  foreground=[("selected", "#FFFFFF")])

        self.user_nom    = None
        self.user_role   = None
        self.user_numero = None   # sert à tagger chaque enregistrement en base
        self._afficher_demarrage()


    #  UTILITAIRES UI
    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def _clear_zone(self):
        for w in self.zone.winfo_children():
            w.destroy()

    def _panel_gauche(self, texte=""):
        side = tk.Frame(self.root, bg="#0F1B2D", width=420)
        side.pack(side="left", fill="both")
        side.pack_propagate(False)
        if self.logo_img:
            tk.Label(side, image=self.logo_img, bg="#0F1B2D").pack(anchor="w", padx=40, pady=(60, 16))
        else:
            tk.Label(side, text="HELHA", fg="white", bg="#0F1B2D",
                     font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=40, pady=(60, 16))
        tk.Frame(side, bg="white", width=60, height=3).pack(anchor="w", padx=40)
        if texte:
            tk.Label(side, text=texte, fg="white", bg="#0F1B2D",
                     justify="left", font=("Segoe UI", 11)).pack(anchor="w", padx=40, pady=30)
        return side

    def _formulaire(self, titre, taille=22):
        """Partie droite des écrans de connexion / création du premier admin."""
        form = tk.Frame(self.root, bg="#E9ECEF", width=480)
        form.pack(side="right", fill="both", expand=True)
        form.pack_propagate(False)
        tk.Label(form, text=titre, fg=NOIR, bg="#E9ECEF",
                 font=("Segoe UI", taille, "bold")).pack(anchor="w", padx=50, pady=(70, 24))
        return form

    @staticmethod
    def _btn(parent, texte, cmd, couleur="#1F4E8C", **kw):
        return tk.Button(parent, text=texte, bg=couleur, fg="white",
                         font=("Segoe UI", 11, "bold"), relief="flat",
                         activebackground="#183E70", activeforeground="white",
                         cursor="hand2", command=cmd, **kw)

    @staticmethod
    def _champ(parent, show=None, width=None):
        """
        Champ de saisie VISIBLE sur Windows.
        Retourne (frame_a_packer, entry).
        Le Frame gris sert de bordure ; le Entry blanc est dedans.
        """
        kw = {}
        if show   is not None: kw["show"]  = show
        if width  is not None: kw["width"] = width

        border = tk.Frame(parent, bg="#94A3B8", padx=2, pady=2)
        inner  = tk.Frame(border, bg="#E9ECEF")
        inner.pack(fill="both", expand=True)
        entry  = tk.Entry(inner, bg="#E9ECEF", fg="#111827",
                          insertbackground="#111827",
                          relief="flat", font=("Segoe UI", 12),
                          highlightthickness=0, bd=0, **kw)
        entry.pack(fill="both", expand=True, padx=6, pady=6)

        def focus_in(e):  border.config(bg="#3B6DB0")
        def focus_out(e): border.config(bg="#94A3B8")
        entry.bind("<FocusIn>",  focus_in)
        entry.bind("<FocusOut>", focus_out)

        return border, entry

    @staticmethod
    def _lbl(parent, texte, bg="#E9ECEF"):
        tk.Label(parent, text=texte, bg=bg, fg=GRIS,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=50)

    @staticmethod
    def _valider_avec_entree(entrees, action):
        """E2 : la touche Entrée valide depuis n'importe quel champ."""
        for e in entrees:
            e.bind("<Return>", lambda ev: action())

    def _titre(self, texte):
        tk.Label(self.zone, text=texte, font=("Segoe UI", 18, "bold"),
                 bg=FOND, fg=NOIR).pack(anchor="w", pady=(0, 12))

    def _ligne(self, parent, label, exemple, largeur_label=12):
        """Libellé + champ + exemple de saisie à droite (E2). Retourne l'Entry."""
        f = tk.Frame(parent, bg=FOND); f.pack(fill="x", pady=4)
        tk.Label(f, text=label, width=largeur_label, anchor="w", bg=FOND,
                 font=("Segoe UI", 11)).pack(side="left")
        fb, e = self._champ(f, width=20)
        fb.pack(side="left")
        tk.Label(f, text=exemple, bg=FOND, fg="#6B7280",
                 font=("Segoe UI", 9, "italic")).pack(side="left", padx=10)
        return e

    @staticmethod
    def _tableau(parent, colonnes, height=10, etirer=True):
        """
        Treeview + barre de défilement (E1). colonnes = [(id, titre, largeur)].
        etirer=False : le tableau garde sa hauteur (height lignes) au lieu de
        remplir l'écran, utile quand un écran contient deux tableaux.
        """
        cadre = tk.Frame(parent, bg=FOND)
        cadre.pack(fill="both" if etirer else "x", expand=etirer)
        tree = ttk.Treeview(cadre, columns=[c[0] for c in colonnes], show="headings", height=height)
        for ident, titre, largeur in colonnes:
            # minwidth : sur un petit écran, la colonne n'est plus écrasée, on fait défiler
            tree.column(ident, width=largeur, minwidth=largeur, anchor="center")
            tree.heading(ident, text=titre)
        barre = ttk.Scrollbar(cadre, orient="vertical", command=tree.yview)
        barre_h = ttk.Scrollbar(cadre, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=barre.set, xscrollcommand=barre_h.set)
        barre.pack(side="right", fill="y")
        barre_h.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)
        return tree

    @staticmethod
    def _resultats(parent, infos, largeur=22):
        """Affiche une liste (libellé, valeur) ; ("", "") = séparateur."""
        for w in parent.winfo_children():
            w.destroy()
        for label, valeur in infos:
            if label == "":
                tk.Frame(parent, bg="#D3D8DE", height=1).pack(fill="x", pady=4)
                continue
            row = tk.Frame(parent, bg=FOND); row.pack(anchor="w", pady=1)
            tk.Label(row, text=f"• {label}", bg=FOND, fg=GRIS,
                     font=("Segoe UI", 10), width=largeur, anchor="w").pack(side="left")
            tk.Label(row, text=valeur, bg=FOND, fg=NOIR,
                     font=("Segoe UI", 10, "bold")).pack(side="left")


    #  AUTHENTIFICATION
    def _afficher_demarrage(self):
        if application.est_premier_lancement():
            self._afficher_setup()
            return
        self._clear()
        self._panel_gauche("Cette application permet de gérer\nvos configurations réseaux\nde manière simplifiée et sécurisée.")
        form = self._formulaire("Identifiez-vous.")

        self._lbl(form, "Nom d'utilisateur")
        f1, self.ent_nom = self._champ(form)
        f1.pack(fill="x", padx=50, pady=(4, 16))

        self._lbl(form, "Mot de passe")
        f2, self.ent_mdp = self._champ(form, show="*")
        f2.pack(fill="x", padx=50, pady=(4, 28))

        self._btn(form, "Se connecter", self._connexion).pack(padx=50, fill="x", ipady=10)
        self._valider_avec_entree([self.ent_nom, self.ent_mdp], self._connexion)
        self.ent_nom.focus_set()

    def _afficher_setup(self):
        self._clear()
        self._panel_gauche("Premier lancement détecté.\nVeuillez créer le compte\nadministrateur principal.")
        form = self._formulaire("Créez votre compte administrateur")

        self._lbl(form, "Nom d'utilisateur Admin")
        f1, self.ent_setup_nom = self._champ(form)
        f1.pack(fill="x", padx=50, pady=(4, 12))

        self._lbl(form, "Numéro d'employé (chiffres)")
        f3, self.ent_setup_num = self._champ(form)
        f3.pack(fill="x", padx=50, pady=(4, 12))

        self._lbl(form, "Mot de passe (8 car. min., maj., min., chiffre, spécial)")
        f2, self.ent_setup_mdp = self._champ(form, show="*")
        f2.pack(fill="x", padx=50, pady=(4, 24))

        self._btn(form, "Activer le système", self._finaliser_setup).pack(padx=50, fill="x", ipady=10)
        self._valider_avec_entree([self.ent_setup_nom, self.ent_setup_num, self.ent_setup_mdp],
                                  self._finaliser_setup)

    def _finaliser_setup(self):
        ok, msg = application.sauvegarde_admin_initial(
            self.ent_setup_nom.get(), self.ent_setup_num.get(), self.ent_setup_mdp.get())
        if not ok:
            messagebox.showwarning("Erreur", msg)
            return
        messagebox.showinfo("Succès", msg)
        self._afficher_demarrage()

    def _connexion(self):
        nom = self.ent_nom.get().strip()
        statut, role, must_change = application.connexion(nom, self.ent_mdp.get())
        if statut == "ok":
            self.user_nom    = nom
            self.user_role   = role
            self.user_numero = application.infos_utilisateur(nom)["numero_employe"]
            if must_change:
                self._afficher_changement_mdp_force()
            else:
                self._afficher_menu()
        elif statut == "inactif":
            messagebox.showerror("Compte désactivé",
                                 "Votre compte a été désactivé.\nContactez un administrateur.")
        else:
            messagebox.showerror("Erreur", "Identifiants invalides.")

    def _erreur_inattendue(self, type_err, err, tb):
        """
        Toute erreur dans un bouton s'affiche au lieu de passer inaperçue (avant : rien
        ne se passait à l'écran). Cas connu : helhanet.db supprimé pendant que
        l'application tourne — la base est recréée vide, le compte connecté n'existe
        plus et la base refuse d'enregistrer avec son numéro d'employé.
        """
        traceback.print_exception(type_err, err, tb)
        if isinstance(err, sqlite3.IntegrityError) and "FOREIGN KEY" in str(err) \
                and self.user_nom and not application.infos_utilisateur(self.user_nom):
            messagebox.showerror("Session", "Votre compte n'existe plus dans la base "
                                 "(fichier helhanet.db supprimé ou remplacé ?).\nVous allez être déconnecté.")
            self._deconnexion()
        else:
            messagebox.showerror("Erreur inattendue", f"L'action n'a pas pu aboutir :\n{err}")

    def _deconnexion(self):
        self.user_nom    = None
        self.user_role   = None
        self.user_numero = None
        self._afficher_demarrage()

    def _verifier_session(self, prevenir=True) -> bool:
        """
        Relit le compte en base avant chaque action : un rôle changé, un compte
        désactivé ou un changement de MDP imposé s'appliquent tout de suite,
        et l'action en cours est annulée (B10).
        """
        infos = application.infos_utilisateur(self.user_nom)
        if not infos:
            messagebox.showerror("Session", "Votre compte n'existe plus dans la base "
                                 "(fichier helhanet.db supprimé ou remplacé ?).")
            self._deconnexion()
            return False
        if not infos["actif"]:
            messagebox.showerror("Session", "Votre compte a été désactivé.")
            self._deconnexion()
            return False
        if infos["must_change"]:
            messagebox.showwarning("Sécurité", "Vous devez définir un nouveau mot de passe.")
            self._afficher_changement_mdp_force()
            return False
        if infos["role"] != self.user_role:
            # Avant : le menu était redessiné mais l'action continuait, donc un admin
            # rétrogradé pouvait encore créer un compte ou réinitialiser un MDP.
            self.user_role = infos["role"]
            self._afficher_menu()
            if prevenir:
                messagebox.showinfo("Session", f"Votre rôle a été modifié ({self.user_role}).\n"
                                               "Le menu a été mis à jour.")
            return False
        return True

    def _afficher_changement_mdp_force(self):
        self._clear()
        self._panel_gauche("Vous devez définir un nouveau\nmot de passe personnel\n"
                           "(première connexion, réinitialisation\nou mesure de sécurité).")
        form = self._formulaire("Nouveau mot de passe.", taille=20)
        tk.Label(form, text="8 caractères minimum, sans espace, avec majuscule, minuscule,\n"
                            "chiffre et caractère spécial. Différent de l'ancien.",
                 fg=GRIS, bg="#E9ECEF", justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=50, pady=(0, 20))

        self._lbl(form, "Nouveau mot de passe")
        f1, ent1 = self._champ(form, show="*")
        f1.pack(fill="x", padx=50, pady=(4, 16))

        self._lbl(form, "Confirmer le mot de passe")
        f2, ent2 = self._champ(form, show="*")
        f2.pack(fill="x", padx=50, pady=(4, 28))

        def valider():
            if ent1.get() != ent2.get():
                messagebox.showwarning("Erreur", "Les mots de passe ne correspondent pas.")
                return
            ok, msg = application.changer_mdp(self.user_nom, ent1.get())
            if ok:
                messagebox.showinfo("Succès", "Mot de passe mis à jour. Bienvenue !")
                self._afficher_menu()
            else:
                messagebox.showwarning("Erreur", msg)

        self._btn(form, "Valider", valider).pack(padx=50, fill="x", ipady=10)
        tk.Button(form, text="Annuler et se déconnecter", bg="#E9ECEF", fg=GRIS, relief="flat",
                  cursor="hand2", command=self._deconnexion).pack(padx=50, pady=8)
        self._valider_avec_entree([ent1, ent2], valider)
        ent1.focus_set()


    #  SHELL PRINCIPAL
    def _afficher_menu(self):
        self._clear()
        sidebar = tk.Frame(self.root, bg="#0F1B2D", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        if self.logoMenu2:
            tk.Label(sidebar, image=self.logoMenu2, bg="#0F1B2D").pack(pady=20)
        else:
            tk.Label(sidebar, text="HELHA.net", fg="white", bg="#0F1B2D",
                     font=("Segoe UI", 14, "bold")).pack(pady=20)

        tk.Frame(sidebar, bg="#E9ECEF", height=1, width=180).pack(padx=20, pady=(0, 10))

        self.boutons_nav = {}

        def ouvrir(label, cmd):
            if not self._verifier_session():
                return
            # E3 : la rubrique ouverte reste en surbrillance
            for nom, b in self.boutons_nav.items():
                b.config(bg="#1C2E4A" if nom == label else "#0F1B2D")
            cmd()

        def nav(label, cmd):
            b = tk.Button(sidebar, text=label, bg="#0F1B2D", fg="white",
                          relief="flat", anchor="w", padx=16, pady=10,
                          font=("Segoe UI", 10), activebackground="#1C2E4A",
                          cursor="hand2", command=lambda: ouvrir(label, cmd))
            b.pack(fill="x")
            self.boutons_nav[label] = b

        nav("Tableau CIDR",          self._ouvrir_cidr)
        nav("Format IP",             self._ouvrir_format_ip)
        nav("Classe IP",             self._ouvrir_classe_ip)
        nav("Masque de classe",      self._ouvrir_masque_classe)
        nav("Réseau / Sous-réseau",  self._ouvrir_classfull)
        nav("Même réseau ?",         self._ouvrir_meme_reseau)
        nav("Découpe en sous-réseaux", self._ouvrir_decoupe)

        if self.user_role == "admin":
            tk.Frame(sidebar, bg="#E9ECEF", height=1, width=180).pack(padx=20, pady=10)
            nav("👥  Utilisateurs", self._ouvrir_gestion_users)

        bottom = tk.Frame(sidebar, bg="#0F1B2D")
        bottom.pack(side="bottom", fill="x", pady=16)
        tk.Label(bottom, text=f"@{self.user_nom}  (n° {self.user_numero})", fg="#D5DBE1", bg="#0F1B2D",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=16)
        tk.Label(bottom, text=self.user_role.upper(), fg="#9AA5B1", bg="#0F1B2D",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=16)
        tk.Button(bottom, text="Se déconnecter", bg="#0F1B2D", fg="#FCA5A5",
                  relief="flat", anchor="w", padx=16, pady=8,
                  font=("Segoe UI", 10, "bold"), cursor="hand2",
                  command=self._deconnexion).pack(fill="x")

        self.zone = tk.Frame(self.root, bg=FOND, padx=36, pady=28)
        self.zone.pack(side="right", fill="both", expand=True)
        tk.Label(self.zone, text="Bienvenue 👋",
                 font=("Segoe UI", 22, "bold"), bg=FOND, fg=NOIR).pack(anchor="w")
        tk.Label(self.zone, text=f"Connecté en tant que {self.user_nom} ({self.user_role})",
                 font=("Segoe UI", 11), bg=FOND, fg=GRIS).pack(anchor="w", pady=(6, 0))


    #  OUTIL 1 — TABLEAU CIDR (le résultat est enregistré en base)
    def _ouvrir_cidr(self):
        self._clear_zone()
        self._titre("Tableau des Masques CIDR")
        donnees = application.generer_donnees_cidr()
        bd.enregistrer_tableau_cidr(self.user_numero, donnees)
        tab = self._tableau(self.zone, [("cidr", "CIDR", 60), ("binaire", "Masque Binaire", 320),
                                        ("decimal", "Décimal Pointé", 160)], height=23)
        for row in donnees:
            tab.insert("", "end", values=row)


    #  OUTILS 2, 3, 4 — un écran par fonctionnalité, comme le demande l'énoncé
    #  (avant : un seul écran « Analyse IP » qui enregistrait dans les 3 tables à chaque clic)
    def _ecran_ip(self, titre, analyser, verifier_format=True):
        """
        Écran commun à F2, F3 et F4 : un champ IP, un bouton, une zone de résultat.
        analyser(ip, lbl_status, resultat) enregistre la saisie et affiche le résultat.
        Avec verifier_format=True, une IP mal formée est refusée avant l'appel.
        """
        self._clear_zone()
        self._titre(titre)

        f, ent = self._champ(self.zone, width=30)
        f.pack(anchor="w", pady=(0, 2))
        tk.Label(self.zone, text="Exemple : 192.168.1.10", bg=FOND, fg="#6B7280",
                 font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(0, 10))

        lbl_status = tk.Label(self.zone, text="", bg=FOND, font=("Segoe UI", 12, "bold"))
        resultat = tk.Frame(self.zone, bg=FOND)

        def check():
            for w in resultat.winfo_children():
                w.destroy()
            lbl_status.config(text="")
            ip = ent.get().strip()
            if not ip:
                lbl_status.config(text="Saisissez une adresse IP.", fg=ROUGE); return
            if verifier_format and not application.verifier_format_ip(ip):
                lbl_status.config(text=MSG_IP_INVALIDE, fg=ROUGE); return
            analyser(ip, lbl_status, resultat)

        self._btn(self.zone, "Analyser", check).pack(anchor="w", pady=(4, 10), ipadx=20, ipady=6)
        lbl_status.pack(anchor="w")
        resultat.pack(anchor="w", pady=8)
        ent.bind("<Return>", lambda e: check())
        ent.focus_set()

    @staticmethod
    def _lignes_couleur(parent, lignes):
        """Affiche une liste (texte, couleur), une ligne par élément."""
        for texte, couleur in lignes:
            tk.Label(parent, text=texte, bg=FOND, fg=couleur,
                     font=("Segoe UI", 11)).pack(anchor="w", pady=2)

    #  OUTIL 2 — FORMAT D'UNE IP (la saisie est enregistrée, même invalide)
    def _ouvrir_format_ip(self):
        def analyser(ip, lbl_status, resultat):
            valide = application.verifier_format_ip(ip)
            bd.inserer("verification_ip", self.user_numero, ip_saisie=ip, valide=int(valide))
            if valide:
                lbl_status.config(text="✔  IP valide", fg=VERT)
            else:
                lbl_status.config(text=MSG_IP_INVALIDE, fg=ROUGE)
        self._ecran_ip("Format d'une adresse IP", analyser, verifier_format=False)

    #  OUTIL 3 — CLASSE D'UNE IP (privée, publique ou usage particulier)
    def _ouvrir_classe_ip(self):
        def analyser(ip, lbl_status, resultat):
            bd.inserer("classe_ip", self.user_numero, ip=ip)
            type_ip = application.type_adresse(ip)
            reservee, type_res = application.is_ip_reservee(ip)
            lignes = [
                (f"• Classe            : {application.definir_classe(ip)[0]}", NOIR),
                (f"• Type              : {type_ip}",
                 {"Adresse Privée": "#D97706", "Adresse Publique": "#1F4E8C"}.get(type_ip, GRIS)),
                (f"• Usage particulier : {'Oui — ' + type_res if reservee else 'Non'}",
                 ROUGE if reservee else "#4B5563"),
            ]
            role = application.role_avec_masque_classe(ip)
            if role:
                lignes.append((f"• Avec le masque de classe : {role}", NOIR))
            self._lignes_couleur(resultat, lignes)
        self._ecran_ip("Classe d'une adresse IP", analyser)

    #  OUTIL 4 — MASQUE DE CLASSE D'UNE IP
    def _ouvrir_masque_classe(self):
        def analyser(ip, lbl_status, resultat):
            bd.inserer("masque_classe", self.user_numero, ip=ip)
            classe, masque = application.definir_classe(ip)
            prefixe = application.prefixe_classe(ip)
            self._lignes_couleur(resultat, [
                (f"• Masque de classe : {masque}" + (f"  (/{prefixe})" if prefixe else ""), NOIR),
                (f"• Classe           : {classe}", GRIS),
            ])
        self._ecran_ip("Masque de classe d'une adresse IP", analyser)

    def _historique(self, table, colonnes, recharger, bouton_modif=None, etirer=True):
        """
        Derniers enregistrements d'une table (F6, découpe). Un clic recharge la saisie.
        Retourne (fonction de rafraîchissement, état de sélection).
        Avec un bouton de modification (F6) : il reste grisé tant qu'aucune ligne
        n'est choisie, puis affiche le numéro de la ligne qui sera remplacée.
        """
        texte = "Historique — cliquez une ligne pour la recharger"
        if bouton_modif:
            texte += ", puis « Enregistrer comme modification »"
        tk.Label(self.zone, text=texte,
                 bg=FOND, fg=GRIS, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 4))
        tree = self._tableau(self.zone, colonnes, height=5, etirer=etirer)
        etat = {"id": None, "lignes": {}}

        def maj_bouton():
            if bouton_modif is None:
                return
            if etat["id"] is None:
                bouton_modif.config(state="disabled", bg="#AFBBCF",
                                    text="Enregistrer comme modification (choisir une ligne)")
            else:
                bouton_modif.config(state="normal", bg="#5A7299",
                                    text=f"Enregistrer comme modification du n° {etat['id']}")

        def rafraichir(selection=None):
            """Recharge l'historique ; selection = ligne visée par la prochaine modification."""
            etat["id"] = selection
            maj_bouton()
            tree.delete(*tree.get_children())
            etat["lignes"] = {}
            for r in bd.lister(table):
                etat["lignes"][str(r["id"])] = r
                tree.insert("", "end", iid=str(r["id"]), values=[
                    application.date_locale(r[c]) if c.endswith("_le")
                    else (r[c] if r[c] is not None else "") for c, _, _ in colonnes])

        def choisir(_):
            sel = tree.selection()
            if sel:
                etat["id"] = int(sel[0])
                maj_bouton()
                recharger(etat["lignes"][sel[0]])

        tree.bind("<<TreeviewSelect>>", choisir)
        rafraichir()
        return rafraichir, etat

    #  OUTIL 5 — RÉSEAU / SOUS-RÉSEAU (classful)
    def _ouvrir_classfull(self):
        self._clear_zone()
        self._titre("Réseau & Sous-réseau (Classful)")

        ent_ip     = self._ligne(self.zone, "IP :",     "ex. 192.168.2.166")
        ent_masque = self._ligne(self.zone, "Masque :", "ex. 255.255.255.128 ou /25")

        lbl_err   = tk.Label(self.zone, text="", bg=FOND, font=("Segoe UI", 11, "bold"))
        lbl_err.pack(anchor="w", pady=(6, 0))

        boutons = tk.Frame(self.zone, bg=FOND); boutons.pack(anchor="w", pady=4)
        res_frame = tk.Frame(self.zone, bg=FOND); res_frame.pack(anchor="w", pady=4)

        def lire_saisie():
            """Retourne (ip, masque décimal) si la saisie est correcte, sinon None."""
            for w in res_frame.winfo_children(): w.destroy()
            lbl_err.config(text="")
            ip   = ent_ip.get().strip()
            cidr = application.lire_masque(ent_masque.get())
            if not application.verifier_format_ip(ip):
                lbl_err.config(text="✘  IP invalide (ex. 192.168.2.166)", fg=ROUGE); return None
            if cidr is None:
                lbl_err.config(text="✘  Masque invalide (ex. 255.255.255.0 ou /24)", fg=ROUGE); return None
            masque = application.masque_cidr_vers_decimal(cidr)
            erreur = application.verifier_classfull(ip, masque)
            if erreur:
                lbl_err.config(text="✘  " + erreur, fg=ROUGE); return None
            r = application.calculer_reseau_classfull(ip, masque)
            self._resultats(res_frame, [
                ("Classe",           r["classe"]),
                ("Masque de classe", r["masque_classe"]),
                ("Réseau",           r["reseau_classe"]),
                ("",                 ""),
                ("Masque appliqué",  f"{r['masque']}  (/{r['cidr']})"),
                ("Sous-réseau",      r["reseau"]),
                ("Broadcast",        r["broadcast"]),
                ("1ère hôte",        r["premiere_hote"]),
                ("Dernière hôte",    r["derniere_hote"]),
                ("Nb hôtes",         str(r["nb_hotes"])),
            ])
            return ip, masque

        def calc():
            saisie = lire_saisie()
            if saisie:
                # Pas d'historique à l'écran pour cette fonctionnalité : la saisie est
                # seulement enregistrée en base (taggée par l'employé).
                bd.inserer("reseau_classfull", self.user_numero, ip=saisie[0], masque=saisie[1])
                lbl_err.config(text="✔  Calcul enregistré", fg=VERT)

        self._btn(boutons, "Calculer", calc).pack(side="left", ipadx=20, ipady=6)
        self._valider_avec_entree([ent_ip, ent_masque], calc)
        ent_ip.focus_set()

    #  OUTIL 6 — MÊME RÉSEAU ? (un masque par machine, vérification bilatérale)
    def _ouvrir_meme_reseau(self):
        self._clear_zone()
        self._titre("Deux IP dans le même réseau ?")

        colonnes = tk.Frame(self.zone, bg=FOND); colonnes.pack(fill="x")
        entrees = []
        for i, exemple in [(1, "192.168.1.129"), (2, "192.168.1.5")]:
            col = tk.Frame(colonnes, bg=FOND); col.pack(side="left", padx=(0, 30), anchor="n")
            tk.Label(col, text=f"Machine {i}", bg=FOND, fg="#1F4E8C",
                     font=("Segoe UI", 12, "bold")).pack(anchor="w")
            entrees.append(self._ligne(col, "IP :", f"ex. {exemple}", 8))
            entrees.append(self._ligne(col, "Masque :", "ex. 255.255.255.0 ou /24", 8))
        ent_ip1, ent_m1, ent_ip2, ent_m2 = entrees

        lbl_res = tk.Label(self.zone, text="", font=("Segoe UI", 13, "bold"), bg=FOND)
        lbl_res.pack(anchor="w", pady=(10, 4))
        boutons = tk.Frame(self.zone, bg=FOND); boutons.pack(anchor="w", pady=4)
        vues = tk.Frame(self.zone, bg=FOND); vues.pack(anchor="w")

        def lire_saisie():
            for w in vues.winfo_children(): w.destroy()
            ip1, ip2 = ent_ip1.get().strip(), ent_ip2.get().strip()
            c1, c2 = application.lire_masque(ent_m1.get()), application.lire_masque(ent_m2.get())
            for ok, msg in [(application.verifier_format_ip(ip1), "IP 1 invalide"),
                            (c1 is not None, "Masque 1 invalide (ex. 255.255.255.0 ou /24)"),
                            (application.verifier_format_ip(ip2), "IP 2 invalide"),
                            (c2 is not None, "Masque 2 invalide (ex. 255.255.255.0 ou /24)")]:
                if not ok:
                    lbl_res.config(text="✘  " + msg, fg=ROUGE); return None

            r = application.comparer_bilateral(ip1, c1, ip2, c2)
            classe = {True: "✔  Même réseau de classe", False: "✘  Réseaux de classe différents",
                      None: "Réseau de classe : non applicable (classe D/E)"}[r["meme_reseau_classe"]]
            lbl_res.config(text=classe, fg={True: VERT, False: ROUGE}.get(r["meme_reseau_classe"], GRIS))

            # E3 : un point de vue par colonne
            for titre, vue, cidr, autre in [("Vue de la machine 1", r["vue_ip1"], c1, "la machine 2"),
                                            ("Vue de la machine 2", r["vue_ip2"], c2, "la machine 1")]:
                col = tk.Frame(vues, bg=FOND); col.pack(side="left", padx=(0, 30), anchor="n")
                tk.Label(col, text=f"{titre}  (/{cidr})", bg=FOND, fg="#1F4E8C",
                         font=("Segoe UI", 11, "bold")).pack(anchor="w")
                verdict = (f"✔  {autre} est dans mon sous-réseau" if vue["meme_reseau"]
                           else f"✘  {autre} n'est pas dans mon sous-réseau")
                tk.Label(col, text=verdict, bg=FOND, fg=VERT if vue["meme_reseau"] else ROUGE,
                         font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
                details = tk.Frame(col, bg=FOND); details.pack(anchor="w")
                self._resultats(details, [("Masque", vue["masque"]),
                                          ("Mon sous-réseau", vue["reseau_ip1"]),
                                          ("Sous-réseau de l'autre", vue["reseau_ip2"]),
                                          ("Broadcast", vue["broadcast"])], largeur=20)
            return dict(ip1=ip1, masque1=application.masque_cidr_vers_decimal(c1),
                        ip2=ip2, masque2=application.masque_cidr_vers_decimal(c2))

        def calc():
            saisie = lire_saisie()
            if saisie:
                bd.inserer("comparaison_ip", self.user_numero, **saisie)
                rafraichir()

        def modifier():
            if etat["id"] is None:
                messagebox.showwarning("Sélection", "Cliquez d'abord une ligne de l'historique."); return
            saisie = lire_saisie()
            if saisie:
                ancien = etat["id"]
                nouveau = bd.modifier("comparaison_ip", ancien, self.user_numero, **saisie)
                rafraichir(nouveau)
                messagebox.showinfo("Modification", f"Nouvelle version n° {nouveau} enregistrée "
                                                    f"(remplace n° {ancien}, conservé).")

        def recharger(ligne):
            for e, cle in zip(entrees, ["ip1", "masque1", "ip2", "masque2"]):
                e.delete(0, "end"); e.insert(0, ligne[cle])
            lire_saisie()

        self._btn(boutons, "Comparer", calc).pack(side="left", ipadx=20, ipady=6)
        btn_modif = self._btn(boutons, "", modifier, couleur="#5A7299", disabledforeground="white")
        btn_modif.pack(side="left", padx=8, ipadx=10, ipady=6)
        rafraichir, etat = self._historique("comparaison_ip", [
            ("id", "N°", 45), ("ip1", "IP 1", 115), ("masque1", "Masque 1", 115),
            ("ip2", "IP 2", 115), ("masque2", "Masque 2", 115),
            ("cree_par", "Créé par", 75), ("modifie_par", "Modifié par", 85),
            ("cree_le", "Date (heure belge)", 190), ("modifie_depuis", "Remplace n°", 85)],
            recharger, btn_modif)
        self._valider_avec_entree(entrees, calc)
        ent_ip1.focus_set()


    #  OUTIL 7 — DÉCOUPE EN SOUS-RÉSEAUX (nombre de SR souhaités)
    def _ouvrir_decoupe(self):
        self._clear_zone()
        self._titre("Découpe en sous-réseaux")

        ent_ip     = self._ligne(self.zone, "Réseau :",    "ex. 192.168.1.0")
        ent_masque = self._ligne(self.zone, "Masque :",    "ex. 255.255.255.0 ou /24 — vide = masque de classe")
        ent_nb     = self._ligne(self.zone, "Nb de SR :",  "ex. 3")
        ent_hotes  = self._ligne(self.zone, "Nb d'hôtes :", "ex. 50 par sous-réseau — vide = pas de contrainte")

        boutons = tk.Frame(self.zone, bg=FOND); boutons.pack(anchor="w", pady=(10, 4))
        lbl = tk.Label(self.zone, text="", bg=FOND, font=("Segoe UI", 11, "bold"), justify="left")
        lbl.pack(anchor="w", pady=(4, 6))
        tab = self._tableau(self.zone, [("numero", "N°", 50), ("reseau", "Sous-réseau", 140),
                                        ("premiere", "1ère hôte", 140), ("derniere", "Dernière hôte", 140),
                                        ("broadcast", "Broadcast", 140)], height=4, etirer=False)

        def afficher(ip, cidr, r, sous_reseaux, message):
            """Résumé de la découpe + tableau des sous-réseaux."""
            hotes = r["nb_hotes_demandes"]
            lbl.config(fg=NOIR, text=(
                f"Réseau de départ : {ip} /{cidr}   •   {r['nb_sr_demandes']} sous-réseau(x) demandé(s)"
                + (f"   •   {hotes} hôtes demandés" if hotes else "") + "\n"
                f"Nouveau masque : {r['nouveau_masque']}   •   "
                f"nombre d'hôtes max par sous-réseau : {r['hotes_par_sr']}\n" + message))
            tab.delete(*tab.get_children())
            tab.configure(height=min(max(len(sous_reseaux), 2), 10))   # hauteur adaptée, défilement au-delà
            for sr in sous_reseaux:
                tab.insert("", "end", values=(sr["numero"], sr["adresse_reseau"], sr["premiere_hote"],
                                              sr["derniere_hote"], sr["broadcast"]))

        def recharger(ligne):
            """Ligne de l'historique : on remet la saisie et on relit les sous-réseaux en base."""
            for e, v in [(ent_ip, ligne["ip"]), (ent_masque, ligne["masque"]),
                         (ent_nb, ligne["nb_sr_demandes"]), (ent_hotes, ligne["nb_hotes_demandes"] or "")]:
                e.delete(0, "end"); e.insert(0, v)
            cidr = application.lire_masque(ligne["masque"])
            afficher(ligne["ip"], cidr, ligne, bd.sous_reseaux(ligne["id"]),
                     f"Découpe n° {ligne['id']} rechargée depuis l'historique")

        def decouper():
            tab.delete(*tab.get_children())
            ip = ent_ip.get().strip()
            if not application.verifier_format_ip(ip):
                lbl.config(text="✘  Réseau invalide (ex. 192.168.1.0)", fg=ROUGE); return
            if ent_masque.get().strip():
                cidr = application.lire_masque(ent_masque.get())
            else:
                cidr = application.prefixe_classe(ip)
            if cidr is None:
                lbl.config(text="✘  Masque invalide (une adresse D/E n'a pas de masque de classe)",
                           fg=ROUGE); return
            nb = ent_nb.get().strip()
            if not (nb.isascii() and nb.isdigit()):
                lbl.config(text="✘  Le nombre de sous-réseaux doit être un entier", fg=ROUGE); return
            hotes = ent_hotes.get().strip()
            if hotes and not (hotes.isascii() and hotes.isdigit()):
                lbl.config(text="✘  Le nombre d'hôtes doit être un entier (ou vide)", fg=ROUGE); return

            ok, r = application.decouper_reseau(ip, cidr, int(nb), int(hotes) if hotes else None)
            if not ok:
                lbl.config(text="✘  " + r, fg=ROUGE); return
            masque = application.masque_cidr_vers_decimal(cidr)
            id_decoupe = bd.enregistrer_decoupe(self.user_numero, ip, masque, int(nb), r)
            rafraichir()
            afficher(r["reseau"], cidr,
                     dict(r, nb_sr_demandes=int(nb), nouveau_masque=f"{r['nouveau_masque']} (/{r['nouveau_cidr']})"),
                     bd.sous_reseaux(id_decoupe),
                     f"{r['bits_empruntes']} bit(s) emprunté(s)   •   {r['nb_sr_possibles']} sous-réseaux possibles"
                     f"   •   ✔  Découpe n° {id_decoupe} enregistrée")

        self._btn(boutons, "Découper", decouper).pack(side="left", ipadx=20, ipady=6)
        rafraichir, _ = self._historique("decoupe", [
            ("id", "N°", 45), ("ip", "Réseau", 120), ("masque", "Masque", 120),
            ("nb_sr_demandes", "Nb SR", 60), ("nb_hotes_demandes", "Hôtes demandés", 110),
            ("cree_par", "Créé par", 75), ("cree_le", "Date (heure belge)", 190)], recharger, etirer=False)
        self._valider_avec_entree([ent_ip, ent_masque, ent_nb, ent_hotes], decouper)
        ent_ip.focus_set()


    #  GESTION UTILISATEURS (admin)
    def _ouvrir_gestion_users(self):
        if self.user_role != "admin":
            return
        self._clear_zone()

        hdr = tk.Frame(self.zone, bg=FOND); hdr.pack(fill="x", pady=(0, 12))
        tk.Label(hdr, text="Gestion des utilisateurs",
                 font=("Segoe UI", 18, "bold"), bg=FOND, fg=NOIR).pack(side="left")
        self._btn(hdr, "+ Créer", self._popup_creer_user,
                  couleur=VERT).pack(side="right", ipadx=10, ipady=4)

        self.tree = self._tableau(self.zone, [("numero", "N° employé", 100), ("nom", "Nom d'utilisateur", 200),
                                              ("role", "Rôle", 100), ("etat", "État", 120)], height=12)
        self.tree.tag_configure("inactif", foreground="#6B7280")
        self.tree.tag_configure("admin",   foreground="#1F4E8C")

        act = tk.Frame(self.zone, bg=FOND); act.pack(fill="x", pady=(10, 0))
        self._btn(act, "🔄 Changer rôle",        self._changer_role,
                  couleur="#5A7299").pack(side="left", padx=(0, 6), ipadx=8, ipady=4)
        self._btn(act, "⏸ Activer / Désactiver", self._basculer,
                  couleur="#F59E0B").pack(side="left", padx=6, ipadx=8, ipady=4)
        self._btn(act, "🔑 Réinitialiser MDP",   self._reinitialiser,
                  couleur="#4A6278").pack(side="left", padx=6, ipadx=8, ipady=4)

        secu = tk.Frame(self.zone, bg=FOND); secu.pack(fill="x", pady=(16, 0))
        self._btn(secu, "🔒 Sécurité : forcer le changement de TOUS les mots de passe",
                  self._bouton_securite, couleur="#B91C1C").pack(side="left", ipadx=8, ipady=4)
        tk.Label(secu, text="En cas de vol de la base. Doit être confirmé par un 2e administrateur.",
                 bg=FOND, fg=GRIS, font=("Segoe UI", 9)).pack(side="left", padx=10)

        self._rafraichir_users()

    def _rafraichir_users(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for u in application.lire_utilisateurs():
            etat = "✔ Actif" if u["actif"] else "✘ Désactivé"
            if u["must_change"]:
                etat += " (MDP à changer)"
            tag  = "inactif" if not u["actif"] else ("admin" if u["role"] == "admin" else "")
            self.tree.insert("", "end", iid=u["nom"],
                             values=(u["numero_employe"], u["nom"], u["role"], etat), tags=(tag,))

    def _selection(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Sélectionnez un utilisateur dans le tableau.")
            return None
        return sel[0]   # l'iid de la ligne est le nom d'utilisateur

    def _popup_creer_user(self):
        win = tk.Toplevel(self.root)
        win.title("Créer un utilisateur")
        win.geometry("400x360")
        win.configure(bg="#E9ECEF")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Créer un utilisateur",
                 font=("Segoe UI", 15, "bold"), bg="#E9ECEF", fg=NOIR).pack(padx=30, pady=(24, 12), anchor="w")
        tk.Label(win, text="Nom d'utilisateur", bg="#E9ECEF", fg=GRIS,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=30)
        fb, ent_nom = self._champ(win)
        fb.pack(fill="x", padx=30, pady=(4, 12))

        tk.Label(win, text="Numéro d'employé (chiffres)", bg="#E9ECEF", fg=GRIS,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=30)
        fb2, ent_num = self._champ(win)
        fb2.pack(fill="x", padx=30, pady=(4, 12))

        tk.Label(win, text="Rôle", bg="#E9ECEF", fg=GRIS,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=30)
        role_var = tk.StringVar(value="user")
        fr = tk.Frame(win, bg="#E9ECEF"); fr.pack(anchor="w", padx=30, pady=(4, 16))
        tk.Radiobutton(fr, text="Utilisateur", variable=role_var, value="user",
                       bg="#E9ECEF", font=("Segoe UI", 10)).pack(side="left", padx=(0, 16))
        tk.Radiobutton(fr, text="Admin", variable=role_var, value="admin",
                       bg="#E9ECEF", font=("Segoe UI", 10)).pack(side="left")

        def valider():
            if not self._verifier_session():
                win.destroy(); return
            ok, resultat = application.creer_utilisateur(ent_nom.get(), ent_num.get(),
                                                         role_var.get(), self.user_nom)
            if ok:
                self._popup_mdp_oneshot(ent_nom.get().strip(), resultat, win)
            else:
                messagebox.showwarning("Erreur", resultat, parent=win)

        self._btn(win, "Créer & générer MDP", valider).pack(padx=30, fill="x", ipady=8)
        self._valider_avec_entree([ent_nom, ent_num], valider)
        ent_nom.focus_set()

    def _popup_mdp_oneshot(self, nom, mdp_tmp, parent=None):
        win = tk.Toplevel(self.root)
        win.title("Mot de passe temporaire")
        win.geometry("400x280")
        win.configure(bg="#E9ECEF")
        win.resizable(False, False)
        win.grab_set()
        if parent:
            try: parent.destroy()
            except Exception: pass

        tk.Label(win, text="⚠  Mot de passe temporaire",
                 font=("Segoe UI", 13, "bold"), bg="#E9ECEF", fg="#D97706").pack(pady=(28, 6))
        tk.Label(win, text=f"Compte : {nom}",
                 bg="#E9ECEF", fg=GRIS, font=("Segoe UI", 10)).pack()
        tk.Label(win, text="Transmettez-le à l'utilisateur.\nIl devra le changer à la première connexion.",
                 bg="#E9ECEF", fg=GRIS, font=("Segoe UI", 9), justify="center").pack(pady=(4, 10))
        box = tk.Frame(win, bg="#D3D8DE", padx=16, pady=10)
        box.pack(padx=40, fill="x")
        # Champ en lecture seule plutôt qu'un Label : le MDP se sélectionne et se copie (B16)
        champ = tk.Entry(box, font=("Courier", 16, "bold"), justify="center", width=10,
                         relief="flat", bd=0, fg=NOIR, readonlybackground="#D3D8DE")
        champ.insert(0, mdp_tmp)
        champ.config(state="readonly")
        champ.pack(side="left", fill="x", expand=True)
        champ.select_range(0, "end")
        champ.focus_set()

        def copier():
            self.root.clipboard_clear()
            self.root.clipboard_append(mdp_tmp)
            btn_copier.config(text="✔ Copié")

        btn_copier = self._btn(box, "📋 Copier", copier, couleur="#5A7299")
        btn_copier.pack(side="left", padx=(8, 0), ipadx=6)

        def fermer():
            win.destroy()
            self._rafraichir_users()

        self._btn(win, "J'ai noté, fermer", fermer).pack(pady=14, ipadx=20, ipady=6)

    def _changer_role(self):
        nom = self._selection()
        if not nom or not self._verifier_session(): return
        role_actuel  = application.infos_utilisateur(nom)["role"]
        nouveau      = "user" if role_actuel == "admin" else "admin"
        if not messagebox.askyesno("Confirmation",
                                   f"Changer le rôle de « {nom} » : {role_actuel} → {nouveau} ?"):
            return
        ok, msg = application.changer_role(nom, nouveau, self.user_nom)
        if not ok:
            messagebox.showerror("Erreur", msg); return
        messagebox.showinfo("Succès", msg)
        if nom == self.user_nom:
            # on vient de se rétrograder : le menu admin disparaît (message déjà affiché)
            self._verifier_session(prevenir=False)
        else:
            self._rafraichir_users()

    def _basculer(self):
        nom = self._selection()
        if not nom or not self._verifier_session(): return
        etat_actuel  = application.infos_utilisateur(nom)["actif"]
        verbe        = "désactiver" if etat_actuel else "réactiver"
        if not messagebox.askyesno("Confirmation",
                                   f"Voulez-vous {verbe} le compte « {nom} » ?\n"
                                   "Le compte sera conservé en base de données."):
            return
        ok, msg = application.basculer_activation(nom, self.user_nom)
        if ok: messagebox.showinfo("Succès", msg); self._rafraichir_users()
        else:  messagebox.showerror("Erreur", msg)

    def _reinitialiser(self):
        nom = self._selection()
        if not nom or not self._verifier_session(): return
        if not messagebox.askyesno("Confirmation",
                                   f"Générer un nouveau mot de passe temporaire pour « {nom} » ?"):
            return
        ok, resultat = application.reinitialiser_mdp(nom, self.user_nom)
        if ok: self._popup_mdp_oneshot(nom, resultat)
        else:  messagebox.showerror("Erreur", resultat)

    def _bouton_securite(self):
        if not self._verifier_session(): return
        if not messagebox.askyesno(
                "Sécurité — vol de la base de données",
                "Tous les utilisateurs devront choisir un nouveau mot de passe à leur prochaine "
                "connexion (les comptes ne sont PAS bloqués).\n\n"
                "Cette action doit être demandée par un administrateur puis confirmée par un "
                "AUTRE administrateur dans les 15 minutes.\n\nContinuer ?", icon="warning"):
            return
        ok, msg = application.demander_reinit_globale(self.user_nom)
        (messagebox.showinfo if ok else messagebox.showerror)("Sécurité", msg)
        if self._verifier_session():   # si l'action est lancée, l'admin aussi doit changer son MDP
            self._rafraichir_users()


if __name__ == "__main__":
    root = tk.Tk()
    AppHelha(root)
    root.mainloop()
