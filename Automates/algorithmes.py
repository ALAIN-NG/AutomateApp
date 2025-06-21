from .models import Automate, Etat, Transition
from django.db import transaction
from collections import deque, defaultdict
import re
import collections


def faire_union(a1, a2):
    etapes = []
    with transaction.atomic():
        union_nom = f"{a1.nom}_UNION_{a2.nom}"
        alphabet = a1.alphabet  # supposons identique

        etapes.append("Étape 1 : Soient A1 et A2 deux AFN à unir.")
        etapes.append(f"A1 : Q1={list(a1.etats.values_list('nom', flat=True))}, Σ={a1.alphabet}")
        etapes.append(f"A2 : Q2={list(a2.etats.values_list('nom', flat=True))}, Σ={a2.alphabet}")

        union = Automate.objects.create(nom=union_nom, type="EFA", alphabet=alphabet)

        etat_map = {}
        for etat in a1.etats.all():
            nom = f"A_{etat.nom}"
            nouveau = Etat.objects.create(automate=union, nom=nom, est_final=etat.est_final)
            etat_map[f"A_{etat.nom}"] = nouveau
        for etat in a2.etats.all():
            nom = f"B_{etat.nom}"
            nouveau = Etat.objects.create(automate=union, nom=nom, est_final=etat.est_final)
            etat_map[f"B_{etat.nom}"] = nouveau

        etapes.append("Étape 2 : Création des états renommés A_q et B_q pour Q1 et Q2")

        for t in a1.transitions.all():
            Transition.objects.create(
                automate=union,
                source=etat_map[f"A_{t.source.nom}"],
                cible=etat_map[f"A_{t.cible.nom}"],
                symbole=t.symbole
            )
        for t in a2.transitions.all():
            Transition.objects.create(
                automate=union,
                source=etat_map[f"B_{t.source.nom}"],
                cible=etat_map[f"B_{t.cible.nom}"],
                symbole=t.symbole
            )

        etapes.append("Étape 3 : Copie des transitions de A1 et A2 vers l'automate d'union")

        initial_global = Etat.objects.create(automate=union, nom="q_init", est_initial=True)

        for e in a1.etats.filter(est_initial=True):
            Transition.objects.create(automate=union, source=initial_global, cible=etat_map[f"A_{e.nom}"], symbole='ε')
        for e in a2.etats.filter(est_initial=True):
            Transition.objects.create(automate=union, source=initial_global, cible=etat_map[f"B_{e.nom}"], symbole='ε')

        etapes.append("Étape 4 : Ajout d'un nouvel état initial q_init")
        etapes.append("Étape 5 : Ajout des transitions ε de q_init vers les états initiaux de A1 et A2")
        etapes.append("Étape 6 : Les états finaux sont ceux finaux de A1 et A2 (inchangés)")

    return etapes, union


def determiniser(afn):
    etapes = []
    with transaction.atomic():
        if afn.type != "NFA":
            raise ValueError("L'automate doit être non déterministe pour être déterminisé.")
        etapes.append("Étape 1 : Initialisation")
        sigma = [s.strip() for s in afn.alphabet.split(',')]
        etapes.append(f"Alphabet Σ = {sigma}")

        afd = Automate.objects.create(nom=f"{afn.nom}_DETERMINISÉ", type="DFA", alphabet=afn.alphabet)

        initiaux = list(afn.etats.filter(est_initial=True))
        if not initiaux:
            etapes.append("Erreur : aucun état initial trouvé dans l'AFN")
            return etapes, None

        etapes.append(f"États initiaux de l'AFN : {[e.nom for e in initiaux]}")

        file = []
        nouveaux_etats = {}
        noms_attribués = {}
        compteur_etats = 0

        def generer_nom():
            nonlocal compteur_etats
            nom = f"q{compteur_etats}"
            compteur_etats += 1
            return nom

        init_set = frozenset(initiaux)
        nom_init = generer_nom()
        e0 = Etat.objects.create(
            automate=afd,
            nom=nom_init,
            est_initial=True,
            est_final=any(e.est_final for e in initiaux)
        )
        nouveaux_etats[init_set] = e0
        noms_attribués[init_set] = nom_init
        file.append(init_set)

        etapes.append(f"Création de l'état initial déterministe : {nom_init}")

        while file:
            courant_set = file.pop(0)
            etat_source = nouveaux_etats[courant_set]
            nom_courant = noms_attribués[courant_set]
            etapes.append(f"\n🔄 Traitement de l'état déterministe {nom_courant}")

            for symbole in sigma:
                cible_set = set()
                for etat in courant_set:
                    transitions = Transition.objects.filter(automate=afn, source=etat, symbole=symbole)
                    for t in transitions:
                        cible_set.add(t.cible)

                if not cible_set:
                    continue

                cible_set_frozen = frozenset(cible_set)

                if cible_set_frozen not in nouveaux_etats:
                    nom_cible = generer_nom()
                    nouvel_etat = Etat.objects.create(
                        automate=afd,
                        nom=nom_cible,
                        est_initial=False,
                        est_final=any(e.est_final for e in cible_set)
                    )
                    nouveaux_etats[cible_set_frozen] = nouvel_etat
                    noms_attribués[cible_set_frozen] = nom_cible
                    file.append(cible_set_frozen)
                    etapes.append(f"Création du nouvel état déterministe : {nom_cible} représentant {[e.nom for e in cible_set]}")

                Transition.objects.create(
                    automate=afd,
                    source=etat_source,
                    cible=nouveaux_etats[cible_set_frozen],
                    symbole=symbole
                )
                etapes.append(f"Transition : {nom_courant} --{symbole}--> {noms_attribués[cible_set_frozen]}")

        etapes.append("\n✅ Déterminisation complétée avec renommage des états.")
        return etapes, afd



def faire_intersection(a1, a2):
    etapes = []
    with transaction.atomic():
        nom_union = f"{a1.nom}_INTER_{a2.nom}"
        automate = Automate.objects.create(
            nom=nom_union,
            type="DFA",  # L’intersection est déterministe
            alphabet=a1.alphabet  # On suppose alphabets égaux et compatibles
        )

        etapes.append("Étape 1 : Construction du produit cartésien des états des deux automates.")

        map_etats = {}
        for e1 in a1.etats.all():
            for e2 in a2.etats.all():
                nom_composite = f"{e1.nom}_{e2.nom}"
                est_initial = e1.est_initial and e2.est_initial
                est_final = e1.est_final and e2.est_final

                etat = Etat.objects.create(
                    automate=automate,
                    nom=nom_composite,
                    est_initial=est_initial,
                    est_final=est_final
                )
                map_etats[(e1.nom, e2.nom)] = etat

        etapes.append(f"{len(map_etats)} états ont été créés dans le produit.")

        etapes.append("Étape 2 : Définition des transitions de l’automate produit.")
        for (e1_nom, e2_nom), etat_prod in map_etats.items():
            for symbole in a1.alphabet.split(','):
                symbole = symbole.strip()
                t1 = a1.transitions.filter(source__nom=e1_nom, symbole=symbole).first()
                t2 = a2.transitions.filter(source__nom=e2_nom, symbole=symbole).first()

                if t1 and t2:
                    cible_nom = f"{t1.cible.nom}_{t2.cible.nom}"
                    cible_prod = map_etats.get((t1.cible.nom, t2.cible.nom))
                    if cible_prod:
                        Transition.objects.create(
                            automate=automate,
                            source=etat_prod,
                            cible=cible_prod,
                            symbole=symbole
                        )

        etapes.append("Toutes les transitions ont été ajoutées en respectant la règle du produit cartésien.")
        etapes.append("Étape 3 : Finalisation de l’automate d’intersection.")

    return etapes, automate


def faire_complementaire(automate_orig):
    etapes = []
    with transaction.atomic():
        if automate_orig.type != 'DFA':
            raise ValueError("L'automate doit être déterministe pour calculer le complémentaire.")

        etapes.append("Étape 1 : Vérification que l'automate est déterministe (DFA).")

        nom_complement = f"{automate_orig.nom}_COMPL"
        automate = Automate.objects.create(
            nom=nom_complement,
            type='DFA',
            alphabet=automate_orig.alphabet
        )
        etapes.append(f"Étape 2 : Création d’un nouvel automate nommé '{nom_complement}'.")

        etats_map = {}
        for e in automate_orig.etats.all():
            est_initial = e.est_initial
            est_final = not e.est_final # inversion ici

            new_e = Etat.objects.create(
                automate=automate,
                nom=e.nom,
                est_initial=est_initial,
                est_final=est_final
            )
            etats_map[e.nom] = new_e

        etapes.append("Étape 3 : Inversion des états finaux et création des états.")

        for t in automate_orig.transitions.all():
            Transition.objects.create(
                automate=automate,
                source=etats_map[t.source.nom],
                cible=etats_map[t.cible.nom],
                symbole=t.symbole
            )

        etapes.append("Étape 4 : Copie des transitions.")
        etapes.append("L’automate complémentaire a été construit avec succès.")

    return etapes, automate



def concatenation(a1, a2):
    etapes = []

    if a1.alphabet != a2.alphabet:
        raise ValueError("Les deux automates doivent avoir le même alphabet.")

    with transaction.atomic():
        etapes.append("✅ Création de l'automate résultant par concaténation.")
        
        automate_concat = Automate.objects.create(
            nom=f"{a1.nom}_{a2.nom}_concat",
            type='AFN',
            alphabet=a1.alphabet
        )

        etapes.append("📌 Duplication des états et transitions de A1.")
        map_etat_a1 = {}
        for e in a1.etats.all():
            nouveau = Etat.objects.create(
                automate=automate_concat,
                nom=f"{e.nom}_1",
                est_initial=e.est_initial,
                est_final=False  # on retirera les fins pour le moment
            )
            map_etat_a1[e.id] = nouveau

        for t in a1.transitions.all():
            Transition.objects.create(
                automate=automate_concat,
                source=map_etat_a1[t.source.id],
                cible=map_etat_a1[t.cible.id],
                symbole=t.symbole
            )

        etapes.append("📌 Duplication des états et transitions de A2.")
        map_etat_a2 = {}
        for e in a2.etats.all():
            nouveau = Etat.objects.create(
                automate=automate_concat,
                nom=f"{e.nom}_2",
                est_initial=False,  # tous les états de a2 ne seront initialisés que par ε-transition
                est_final=e.est_final
            )
            map_etat_a2[e.id] = nouveau

        for t in a2.transitions.all():
            Transition.objects.create(
                automate=automate_concat,
                source=map_etat_a2[t.source.id],
                cible=map_etat_a2[t.cible.id],
                symbole=t.symbole
            )

        etapes.append("🔗 Ajout des ε-transitions entre les fins de A1 et les débuts de A2.")
        for f in a1.etats.filter(est_final=True):
            for i in a2.etats.filter(est_initial=True):
                Transition.objects.create(
                    automate=automate_concat,
                    source=map_etat_a1[f.id],
                    cible=map_etat_a2[i.id],
                    symbole='ε'
                )
                etapes.append(f"ε: {map_etat_a1[f.id].nom} → {map_etat_a2[i.id].nom}")

    etapes.append("✅ Automate de concaténation généré avec succès.")
    return etapes, automate_concat


def miroir(automate):
    etapes = []

    with transaction.atomic():
        etapes.append("✅ Création de l'automate miroir.")

        miroir_auto = Automate.objects.create(
            nom=f"{automate.nom}_miroir",
            type="AFN",  # le miroir d'un DFA n'est généralement pas un DFA
            alphabet=automate.alphabet
        )

        # Étape 1 : dupliquer les états (avec nom identique)
        etat_map = {}
        for etat in automate.etats.all():
            nouveau = Etat.objects.create(
                automate=miroir_auto,
                nom=etat.nom,
                est_initial=False,  # on définit ensuite
                est_final=False
            )
            etat_map[etat.id] = nouveau

        # Étape 2 : inverser toutes les transitions
        for t in automate.transitions.all():
            Transition.objects.create(
                automate=miroir_auto,
                source=etat_map[t.cible.id],  # inversion
                cible=etat_map[t.source.id],
                symbole=t.symbole
            )

        # Étape 3 : gérer les états initiaux / finaux
        anciens_initiaux = automate.etats.filter(est_initial=True)
        anciens_finals = automate.etats.filter(est_final=True)

        if anciens_finals.count() == 1:
            seul_init = anciens_finals.first()
            etat_map[seul_init.id].est_initial = True
            etat_map[seul_init.id].save()
            etapes.append(f"✅ État initial miroir : {seul_init.nom}")
        else:
            # créer un nouvel état initial
            nouvel_initial = Etat.objects.create(
                automate=miroir_auto,
                nom="q_init",
                est_initial=True,
                est_final=False
            )
            etapes.append("🔁 Ajout d'un état initial intermédiaire (q_init)")
            for final in anciens_finals:
                Transition.objects.create(
                    automate=miroir_auto,
                    source=nouvel_initial,
                    cible=etat_map[final.id],
                    symbole='ε'
                )

        for init in anciens_initiaux:
            etat_map[init.id].est_final = True
            etat_map[init.id].save()

        etapes.append("✅ Tous les états finaux deviennent finaux du miroir.")

    return etapes, miroir_auto

def faire_minimisation(automate_orig):
    etapes = []
    with transaction.atomic():
        if automate_orig.type != 'DFA':
            raise ValueError("L'automate doit être déterministe pour être minimisé.")

        etapes.append("Étape 1 : Vérification que l'automate est déterministe.")

        # Récupérer alphabet et états
        alphabet = [s.strip() for s in automate_orig.alphabet.split(',')]
        etats = list(automate_orig.etats.all())

        # Identifier états accessibles
        accessibles = set()
        transitions = automate_orig.transitions.all()

        def dfs(e):
            if e in accessibles:
                return
            accessibles.add(e)
            for s in alphabet:
                for t in transitions.filter(source=e, symbole=s):
                    dfs(t.cible)

        initiaux = [e for e in etats if e.est_initial]
        for e in initiaux:
            dfs(e)

        etapes.append(f"Étape 2 : Élimination des états inaccessibles : {len(etats)} → {len(accessibles)} états.")

        etats = [e for e in accessibles]
        etat_noms = [e.nom for e in etats]

        # Étape 3 : Initialiser la partition P = {F, Q \ F}
        finals = set(e.nom for e in etats if e.est_final)
        non_finals = set(e.nom for e in etats if not e.est_final)
        P = [finals, non_finals]

        etapes.append("Étape 3 : Initialisation de la partition P = {F, Q \\ F}.")
        etapes.append(f"Finals = {finals}")
        etapes.append(f"Non-finals = {non_finals}")

        def trouver_classe(p, nom):
            for i, c in enumerate(p):
                if nom in c:
                    return i
            return -1

        stable = False
        while not stable:
            stable = True
            nouvelle_P = []
            for groupe in P:
                ref = next(iter(groupe))
                sous_groupes = {}
                for e in groupe:
                    signature = []
                    for s in alphabet:
                        cible = transitions.filter(source__nom=e, symbole=s).first()
                        cible_nom = cible.cible.nom if cible else None
                        signature.append(trouver_classe(P, cible_nom))
                    signature = tuple(signature)
                    sous_groupes.setdefault(signature, set()).add(e)

                if len(sous_groupes) > 1:
                    stable = False
                    nouvelle_P.extend(sous_groupes.values())
                    etapes.append(f"Raffinement du groupe {groupe} → {list(sous_groupes.values())}")
                else:
                    nouvelle_P.append(groupe)
            P = nouvelle_P

        etapes.append("Étape 4 : Partition stable obtenue.")
        etapes.append(f"Classes finales : {P}")

        # Étape 5 : Construction du nouvel automate
        automate_min = Automate.objects.create(
            nom=f"{automate_orig.nom}_MIN",
            type="DFA",
            alphabet=automate_orig.alphabet
        )

        classe_map = {}
        for i, groupe in enumerate(P):
            nom_classe = "_".join(sorted(groupe))
            is_initial = any(etat.nom in groupe and etat.est_initial for etat in etats)
            is_final = any(etat.nom in groupe and etat.est_final for etat in etats)
            e = Etat.objects.create(
                automate=automate_min,
                nom=nom_classe,
                est_initial=is_initial,
                est_final=is_final
            )
            for nom in groupe:
                classe_map[nom] = e

        # Transitions
        for t in transitions:
            if t.source.nom in classe_map and t.cible.nom in classe_map:
                Transition.objects.get_or_create(
                    automate=automate_min,
                    source=classe_map[t.source.nom],
                    cible=classe_map[t.cible.nom],
                    symbole=t.symbole
                )

        etapes.append("Étape 5 : Création des états et transitions de l’automate minimal.")

    return etapes, automate_min





def completion(automate):
    if automate.type != 'DFA':
        raise ValueError("La complétion ne s'applique qu'aux AFD.")

    etapes = []
    symboles = list(set(automate.alphabet))
    etats = list(automate.etats.all())

    # 1. Créer un automate copié
    with transaction.atomic():
        nouveau = Automate.objects.create(
            nom=f"{automate.nom}_complété",
            type="DFA",
            alphabet=automate.alphabet
        )
        etapes.append(f"Création d’un nouvel automate : {nouveau.nom}")

        etat_map = {}  # ancien -> nouveau
        for e in etats:
            new_e = Etat.objects.create(
                automate=nouveau,
                nom=e.nom,
                est_initial=e.est_initial,
                est_final=e.est_final
            )
            etat_map[e.nom] = new_e

        # Création de l'état puit
        etat_puit = Etat.objects.create(
            automate=nouveau,
            nom="Puit",
            est_initial=False,
            est_final=False
        )
        etapes.append("Création d’un état puit pour gérer les transitions manquantes.")

        # Copier les transitions existantes
        for t in automate.transitions.all():
            Transition.objects.create(
                automate=nouveau,
                source=etat_map[t.source.nom],
                cible=etat_map[t.cible.nom],
                symbole=t.symbole
            )

        # 2. Compléter les transitions manquantes
        for e in etats:
            dest_symboles = set(
                t.symbole for t in automate.transitions.filter(source=e)
            )
            manquants = set(symboles) - dest_symboles
            if manquants:
                etapes.append(f"Complétion des transitions manquantes pour l’état {e.nom}.")
            for s in manquants:
                Transition.objects.create(
                    automate=nouveau,
                    source=etat_map[e.nom],
                    cible=etat_puit,
                    symbole=s
                )
                etapes.append(f"Ajout de la transition manquante : {e.nom} --{s}--> Puit")

        # 3. Le puit boucle sur lui-même pour chaque symbole
        for s in symboles:
            Transition.objects.create(
                automate=nouveau,
                source=etat_puit,
                cible=etat_puit,
                symbole=s
            )
        etapes.append("Ajout des transitions bouclées sur l’état puit.")

    return etapes, nouveau



def faire_canonisation(automate_orig):
    etapes = []

    if automate_orig.type != "DFA":
        raise ValueError("L'automate doit être déterministe pour être canoniquement représenté.")

    # Étape 1 : Minimisation
    etapes.append("Étape 1 : Minimisation de l’automate.")
    minimisation_etapes, automate_min = faire_minimisation(automate_orig)
    etapes.extend(["    " + step for step in minimisation_etapes])

    # Étape 2 : Renommage canonique par parcours BFS
    etapes.append("Étape 2 : Parcours BFS depuis l’état initial pour établir l’ordre canonique.")


    old_etats = {e.nom: e for e in automate_min.etats.all()}
    transitions = automate_min.transitions.all()

    graph = {}
    for t in transitions:
        graph.setdefault(t.source.nom, []).append((t.symbole, t.cible.nom))

    # BFS pour ordonner les états
    visited = set()
    ordre = []
    queue = deque()

    etat_initial = next((e for e in automate_min.etats.all() if e.est_initial), None)
    if not etat_initial:
        raise ValueError("L’automate minimisé n’a pas d’état initial.")

    queue.append(etat_initial.nom)
    visited.add(etat_initial.nom)

    while queue:
        current = queue.popleft()
        ordre.append(current)
        for symbole, voisin in sorted(graph.get(current, []), key=lambda x: (x[0], x[1])):
            if voisin not in visited:
                visited.add(voisin)
                queue.append(voisin)

    etapes.append(f"Ordre canonique obtenu : {ordre}")

    # Étape 3 : Création d’un nouvel automate avec renommage canonique
    automate_canon = Automate.objects.create(
        nom=f"{automate_orig.nom}_CANON",
        type="DFA",
        alphabet=automate_orig.alphabet
    )

    etapes.append("Étape 3 : Construction de l’automate canonisé avec renommage q0, q1, …")

    nom_map = {}
    for i, nom in enumerate(ordre):
        etat_orig = old_etats[nom]
        nom_canon = f"q{i}"
        e = Etat.objects.create(
            automate=automate_canon,
            nom=nom_canon,
            est_initial=etat_orig.est_initial,
            est_final=etat_orig.est_final
        )
        nom_map[nom] = e

    for t in transitions:
        if t.source.nom in nom_map and t.cible.nom in nom_map:
            Transition.objects.create(
                automate=automate_canon,
                source=nom_map[t.source.nom],
                cible=nom_map[t.cible.nom],
                symbole=t.symbole
            )

    etapes.append("Étape 4 : Transitions recopiées avec états renommés.")

    return etapes, automate_canon




def cloture_etoile(automate):
    nouveau = Automate.objects.create(
        nom=f"{automate.nom}*",
        type='EFA',  # ε-transitions
        alphabet=automate.alphabet
    )

    etat_map = {}
    for etat in automate.etats.all():
        new_state = Etat.objects.create(
            automate=nouveau,
            nom=etat.nom,
            est_initial=False,
            est_final=etat.est_final
        )
        etat_map[etat.id] = new_state

    # Créer un nouvel état initial qui est aussi final
    initial_star = Etat.objects.create(
        automate=nouveau,
        nom="q_new",
        est_initial=True,
        est_final=True
    )

    anciens_initiaux = automate.etats.filter(est_initial=True)
    anciens_finaux = automate.etats.filter(est_final=True)

    # ε-transitions de q_new vers anciens initiaux
    for ei in anciens_initiaux:
        Transition.objects.create(
            automate=nouveau,
            source=initial_star,
            cible=etat_map[ei.id],
            symbole="ε"
        )

    # ε-transitions de finaux vers anciens initiaux
    for ef in anciens_finaux:
        for ei in anciens_initiaux:
            Transition.objects.create(
                automate=nouveau,
                source=etat_map[ef.id],
                cible=etat_map[ei.id],
                symbole="ε"
            )

    # Copier les transitions existantes
    for t in automate.transitions.all():
        Transition.objects.create(
            automate=nouveau,
            source=etat_map[t.source.id],
            cible=etat_map[t.cible.id],
            symbole=t.symbole
        )

    return nouveau




def difference(a1, a2):
    etapes = []

    if a1.type != 'DFA' or a2.type != 'DFA':
        raise ValueError("Les deux automates doivent être déterministes (DFA) pour faire la différence.")

    if a1.alphabet != a2.alphabet:
        raise ValueError("Les deux automates doivent avoir le même alphabet.")

    etapes.append("✅ Vérification des conditions : DFA et même alphabet.")
    
    # 1. Complémentaire de B
    etapes.append("🔄 Calcul du complémentaire de l'automate B.")
    etapes_compl, b_complement = faire_complementaire(a2)
    etapes += etapes_compl

    # 2. Intersection de A avec complémentaire(B)
    etapes.append("🔀 Calcul de l'intersection entre A et le complémentaire de B.")
    etapes_inter, result = faire_intersection(a1, b_complement)
    result.nom = f"{a1.nom}-{a2.nom}"
    result.save()
    b_complement.delete()
    etapes += etapes_inter

    etapes.append("✅ Automate résultant de la différence A \\ B construit avec succès.")
    return etapes, result


def quotient_gauche(a_b, a_a):
    """
    Calcule un automate reconnaissant L(B) / L(A)
    :param a_b: Automate B
    :param a_a: Automate A
    :return: automate résultant, etapes
    """
    etapes = []

    if a_b.alphabet != a_a.alphabet:
        raise ValueError("Les deux automates doivent avoir le même alphabet pour le quotient.")

    etapes.append("📌 Création du produit A × B pour la concaténation inversée.")

    # Étape 1 : renverser A
    etapes_r, miroir_a = miroir(a_a)
    etapes += etapes_r

    # Étape 2 : renverser B
    etapes_r2, miroir_b = miroir(a_b)
    etapes += etapes_r2

    # Étape 3 : faire l'intersection miroir(B) ∩ miroir(A)
    etapes_inter, inter = faire_intersection(miroir_b, miroir_a)
    etapes += etapes_inter
    miroir_a.delete()
    miroir_b.delete()

    # Étape 4 : renverser le résultat → L(B)/L(A)
    etapes_fin, resultat = miroir(inter)
    inter.delete()
    resultat.nom = f"{a_b.nom} / {a_a.nom}"
    resultat.save()
    etapes += etapes_fin

    etapes.append("✅ Quotient à gauche L(B)/L(A) construit par renversement triple.")
    return etapes, resultat





def etats_accessibles(automate):
    """Retourne tous les états accessibles depuis l'état initial"""
    etat_initial = automate.etats.filter(est_initial=True).first()
    if not etat_initial:
        return set()
    
    accessibles = set()
    a_visiter = {etat_initial}
    
    while a_visiter:
        etat = a_visiter.pop()
        accessibles.add(etat)
        
        # Trouver tous les états atteignables depuis cet état
        transitions = Transition.objects.filter(automate=automate, source=etat)
        for transition in transitions:
            if transition.cible not in accessibles:
                a_visiter.add(transition.cible)
    
    return accessibles

def etats_coaccessibles(automate):
    """Retourne tous les états co-accessibles (qui mènent à un état final)"""
    etats_finaux = set(automate.etats.filter(est_final=True))
    if not etats_finaux:
        return set()
    
    coaccessibles = set()
    a_visiter = set(etats_finaux)
    
    while a_visiter:
        etat = a_visiter.pop()
        coaccessibles.add(etat)
        
        # Trouver tous les états qui mènent à cet état
        transitions = Transition.objects.filter(automate=automate, cible=etat)
        for transition in transitions:
            if transition.source not in coaccessibles:
                a_visiter.add(transition.source)
    
    return coaccessibles

def etats_utiles(automate):
    """Retourne les états à la fois accessibles et co-accessibles"""
    accessibles = etats_accessibles(automate)
    coaccessibles = etats_coaccessibles(automate)
    return accessibles & coaccessibles




def calculer_epsilon_fermetures(automate):
    epsilon = 'ε'
    fermetures = {}

    # construire les transitions ε
    epsilon_transitions = defaultdict(list)
    for t in automate.transitions.filter(symbole=epsilon):
        epsilon_transitions[t.source].append(t.cible)

    # pour chaque état, calculer la fermeture ε
    for etat in automate.etats.all():
        fermeture = set()
        pile = [etat]

        while pile:
            courant = pile.pop()
            if courant not in fermeture:
                fermeture.add(courant)
                pile.extend(epsilon_transitions.get(courant, []))

        fermetures[etat] = fermeture

    return fermetures



def emoder_automate(automate):
    """
    Simplifie l'automate en conservant uniquement les états utiles
    et leurs transitions
    """
    # 1. Identifier les états utiles
    utiles = etats_utiles(automate)
    
    # 2. Créer un nouveau dictionnaire pour les nouveaux états
    nouveaux_etats = {}
    nouveaux_etats_objets = []
    
    # 3. Créer les nouveaux états (copie des utiles)
    for etat in utiles:
        nouveaux_etats[etat.nom] = Etat(
            nom=etat.nom,
            est_initial=etat.est_initial,
            est_final=etat.est_final
        )
        nouveaux_etats_objets.append(nouveaux_etats[etat.nom])
    
    # 4. Filtrer les transitions entre états utiles
    nouvelles_transitions = []
    for transition in automate.transitions.all():
        if transition.source in utiles and transition.cible in utiles:
            nouvelles_transitions.append(Transition(
                source=nouveaux_etats[transition.source.nom],
                cible=nouveaux_etats[transition.cible.nom],
                symbole=transition.symbole
            ))
    
    return {
        'etats': nouveaux_etats_objets,
        'transitions': nouvelles_transitions,
        'etats_supprimes': set(automate.etats.all()) - utiles,
        'transitions_supprimees': [
            t for t in automate.transitions.all() 
            if not (t.source in utiles and t.cible in utiles)
        ]
    }





def convertir_afd_en_afn(automate):
    if automate.type != 'DFA':
        raise ValueError("L'automate doit être un AFD pour être converti en AFN.")

    etapes = [f"Conversion de l’automate {automate.nom} (AFD) vers un AFN avec ajout d’un état non-déterministe."]
    alphabet = list(set(automate.alphabet))
    
    with transaction.atomic():
        nouveau = Automate.objects.create(
            nom=f"{automate.nom}_AFN",
            type="NFA",
            alphabet=automate.alphabet
        )
        etapes.append(f"Création de l'automate AFN : {nouveau.nom}")

        # Copier les états
        etat_map = {}
        for e in automate.etats.all():
            new_e = Etat.objects.create(
                automate=nouveau,
                nom=e.nom,
                est_initial=e.est_initial,
                est_final=e.est_final
            )
            etat_map[e.nom] = new_e

        etapes.append("Copie des états effectuée.")

        # Copier les transitions
        for t in automate.transitions.all():
            Transition.objects.create(
                automate=nouveau,
                source=etat_map[t.source.nom],
                cible=etat_map[t.cible.nom],
                symbole=t.symbole
            )
        etapes.append("Copie des transitions effectuée.")

        # Choisir un état cible pour les transitions supplémentaires
        q_source = list(etat_map.values())[1] if len(etat_map) > 1 else list(etat_map.values())[0]

        # Ajouter un nouvel état q_alt
        q_alt = Etat.objects.create(
            automate=nouveau,
            nom="q_alt",
            est_initial=False,
            est_final=False
        )
        etapes.append("Ajout d’un état alternatif q_alt.")

        # Ajouter des transitions de q_source vers q_alt pour chaque symbole
        for s in alphabet:
            if s != ',':
                Transition.objects.create(
                    automate=nouveau,
                    source=q_source,
                    cible=q_alt,
                    symbole=s
                )
                etapes.append(f"Ajout : {q_source.nom} --{s}--> q_alt")

    etapes.append("L’automate résultant est un vrai AFN avec non-déterminisme introduit.")
    return etapes, nouveau


def convertir_afn_vers_efn(automate):
    """
    Convertit un AFD ou AFN en EFA (ε-AFN) en ajoutant un nouvel état initial
    avec des transitions ε vers les anciens états initiaux.
    """
    if automate.type == "EFA":
        raise ValueError("L'automate est déjà un EFA (ε-AFN).")

    if automate.type != "NFA":
        raise ValueError("L'automate choisi n'est pas un AFN")

    with transaction.atomic():
        # Ajout de ε à l'alphabet si nécessaire
        alphabet_set = set(sym.strip() for sym in automate.alphabet.split(",") if sym.strip())
        alphabet_set.add("ε")
        nouvel_alphabet = ",".join(sorted(alphabet_set))

        # Création du nouvel automate
        nouveau = Automate.objects.create(
            nom=f"{automate.nom}_efa",
            type="EFA",
            alphabet=nouvel_alphabet
        )

        # Copier les états et garder une correspondance
        etat_mapping = {}
        for etat in automate.etats.all():
            copie = Etat.objects.create(
                automate=nouveau,
                nom=etat.nom,
                est_initial=False,
                est_final=etat.est_final
            )
            etat_mapping[etat.id] = copie

        # Créer le nouvel état initial
        nouvel_initial = Etat.objects.create(
            automate=nouveau,
            nom="q_init",
            est_initial=True,
            est_final=False
        )

        # Ajouter les transitions existantes
        for t in automate.transitions.all():
            Transition.objects.create(
                automate=nouveau,
                source=etat_mapping[t.source.id],
                symbole=t.symbole,
                cible=etat_mapping[t.cible.id]
            )

        # Ajouter transition ε du nouvel état initial vers chaque ancien état initial
        anciens_initiaux = automate.etats.filter(est_initial=True)
        for ancien in anciens_initiaux:
            Transition.objects.create(
                automate=nouveau,
                source=nouvel_initial,
                symbole='ε',
                cible=etat_mapping[ancien.id]
            )

        # Étapes pour affichage
        etapes = [
            "Création d'un nouvel état initial q_init.",
            f"Ajout de la lettre ε à l'alphabet : {nouvel_alphabet}.",
            f"Ajout de transitions ε de q_init vers : {', '.join(e.nom for e in anciens_initiaux)}."
        ]

        return etapes, nouveau



def convertir_afd_vers_efn(automate1):
    """
    Convertit un AFD ou AFN en EFA (ε-AFN) en ajoutant un nouvel état initial
    avec des transitions ε vers les anciens états initiaux.
    """
    if automate1.type == "EFA":
        raise ValueError("L'automate est déjà un EFA (ε-AFN).")

    if automate1.type != "DFA":
        raise ValueError("L'automate choisi n'est pas un AFD")
    

    et, automate = convertir_afd_en_afn(automate1)

    with transaction.atomic():
        # Ajout de ε à l'alphabet si nécessaire
        alphabet_set = set(sym.strip() for sym in automate.alphabet.split(",") if sym.strip())
        alphabet_set.add("ε")
        nouvel_alphabet = ",".join(sorted(alphabet_set))

        # Création du nouvel automate
        nouveau = Automate.objects.create(
            nom=f"{automate.nom}_efa",
            type="EFA",
            alphabet=nouvel_alphabet
        )

        # Copier les états et garder une correspondance
        etat_mapping = {}
        for etat in automate.etats.all():
            copie = Etat.objects.create(
                automate=nouveau,
                nom=etat.nom,
                est_initial=False,
                est_final=etat.est_final
            )
            etat_mapping[etat.id] = copie

        # Créer le nouvel état initial
        nouvel_initial = Etat.objects.create(
            automate=nouveau,
            nom="q_init",
            est_initial=True,
            est_final=False
        )

        # Ajouter les transitions existantes
        for t in automate.transitions.all():
            Transition.objects.create(
                automate=nouveau,
                source=etat_mapping[t.source.id],
                symbole=t.symbole,
                cible=etat_mapping[t.cible.id]
            )

        # Ajouter transition ε du nouvel état initial vers chaque ancien état initial
        anciens_initiaux = automate.etats.filter(est_initial=True)
        for ancien in anciens_initiaux:
            Transition.objects.create(
                automate=nouveau,
                source=nouvel_initial,
                symbole='ε',
                cible=etat_mapping[ancien.id]
            )

        # Étapes pour affichage
        etapes = [
            "Création d'un nouvel état initial q_init.",
            f"Ajout de la lettre ε à l'alphabet : {nouvel_alphabet}.",
            f"Ajout de transitions ε de q_init vers : {', '.join(e.nom for e in anciens_initiaux)}."
        ]
        etapes.append(et)
        automate.delete()

        return etapes, nouveau







def eliminer_transitions_epsilon(automate):
    etapes = []
    etapes.append("🔁 Début de l'élimination des ε-transitions.")
    epsilon = 'ε'

    anciens_etats = list(automate.etats.all())
    anciennes_transitions = list(automate.transitions.select_related('source', 'cible'))

    # Étape 1 : Construction des ε-transitions
    epsilon_adjacence = collections.defaultdict(list)
    for t in anciennes_transitions:
        if t.symbole == epsilon:
            epsilon_adjacence[t.source.id].append(t.cible)

    # Étape 2 : Calcul des fermetures ε
    fermeture_epsilon = {}
    for etat in anciens_etats:
        fermeture = set()
        pile = [etat]
        while pile:
            courant = pile.pop()
            if courant.id not in {e.id for e in fermeture}:
                fermeture.add(courant)
                pile.extend(epsilon_adjacence[courant.id])
        fermeture_epsilon[etat.id] = fermeture
        noms = ', '.join(sorted(e.nom for e in fermeture))
        etapes.append(f"Fermeture ε({etat.nom}) = {{{noms}}}")

    # Étape 3 : Création du nouvel automate sans ε
    nouvel_alphabet = ','.join([s for s in automate.alphabet.split(',') if s.strip() != epsilon])
    nouvel_automate = Automate.objects.create(
        nom=f"{automate.nom}_sans_ε",
        type='NFA',
        alphabet=nouvel_alphabet
    )

    map_etats = {}
    for ancien in anciens_etats:
        fermeture = fermeture_epsilon[ancien.id]
        est_initial = ancien.est_initial
        est_final = any(e.est_final for e in fermeture)

        nouveau = Etat.objects.create(
            automate=nouvel_automate,
            nom=ancien.nom,
            est_initial=est_initial,
            est_final=est_final
        )
        map_etats[ancien.id] = nouveau

    # Étape 4 : Recréation des transitions sans ε
    symbole_utiles = [s.strip() for s in nouvel_alphabet.split(',') if s.strip()]
    transitions_ajoutees = set()

    for ancien_source in anciens_etats:
        fermeture_src = fermeture_epsilon[ancien_source.id]

        for symbole in symbole_utiles:
            destinations = set()
            for etat_inter in fermeture_src:
                for t in anciennes_transitions:
                    if t.source.id == etat_inter.id and t.symbole == symbole:
                        fermeture_dest = fermeture_epsilon[t.cible.id]
                        destinations.update(fermeture_dest)

            source_mappee = map_etats[ancien_source.id]
            for dest in destinations:
                cible_mappee = map_etats[dest.id]
                cle = (source_mappee.id, symbole, cible_mappee.id)
                if cle not in transitions_ajoutees:
                    Transition.objects.create(
                        automate=nouvel_automate,
                        source=source_mappee,
                        symbole=symbole,
                        cible=cible_mappee
                    )
                    transitions_ajoutees.add(cle)

    etapes.append("✅ Élimination des ε-transitions terminée avec succès.")
    return nouvel_automate, etapes




def eliminer_epsilon_et_determiniser(automate):

    etapes = []

    # Étape 1 : Éliminer les transitions ε
    afn_sans_epsilon, etapes_epsilon = eliminer_transitions_epsilon(automate)
    etapes.extend(["🔹 " + e for e in etapes_epsilon])
    etapes.append("✅ Élimination des ε-transitions terminée.")

    # Étape 2 : Déterminiser l'automate obtenu
    etapes_determinisation, afd = determiniser(afn_sans_epsilon)
    afn_sans_epsilon.delete()
    etapes.extend(["🔹 " + e for e in etapes_determinisation])
    etapes.append("✅ Déterminisation terminée.")

    return etapes, afd


























import re

class EquationSolver:
    def __init__(self, systeme_texte):
        self.systeme_texte = systeme_texte.strip()
        self.equations = {}   # Xi -> expression (brute)
        self.resultats = {}   # Xi -> expression régulière finale
        self.etapes = []      # Étapes de résolution

    def resoudre(self):
        self._parser_systeme()
        self.etapes.append("📌 Système initial :")
        for var, expr in self.equations.items():
            self.etapes.append(f"{var} = {expr}")

        # Étape principale : application du lemme d’Arden et substitution
        while True:
            variables_restantes = [v for v in self.equations if v not in self.resultats]
            progress = False

            for var in variables_restantes:
                expr = self.equations[var]

                if expr.strip() == "ε":
                    self.resultats[var] = "ε"
                    self.etapes.append(f"✅ {var} = ε → remplacé partout")
                    self._remplacer_variable(var, "ε")
                    progress = True
                    break

                coeff_self, autres, const = self._analyser_expression(var, expr)

                if coeff_self is not None:
                    autres_str = self._expr_dict_to_str(autres)
                    partie = autres_str
                    if const:
                        partie = f"{autres_str} + {const}" if autres_str else const

                    nouvelle_expr = f"{coeff_self}*({partie})" if partie else f"{coeff_self}*ε"
                    self.resultats[var] = nouvelle_expr
                    self.etapes.append(f"📐 Lemme d’Arden sur {var} : {var} = {coeff_self}{var} + {partie or 'ε'} ⇒ {var} = {nouvelle_expr}")
                    self._remplacer_variable(var, nouvelle_expr)
                    progress = True
                    break

            if not progress:
                break

        # 🔁 Substitution récursive + simplification
        self.etapes.append("🔁 Simplification finale :")
        for var in list(self.resultats):
            expr = self.resultats[var]
            visited = set()

            while any(x in expr for x in self.resultats if x != var and x not in visited):
                for sub_var in self.resultats:
                    if sub_var != var and sub_var in expr:
                        expr = re.sub(f"{sub_var}", f"({self.resultats[sub_var]})", expr)
                        visited.add(sub_var)

            # Simplifications : a*ε = a*, ε + a = a, etc.
            expr = expr.replace("ε", "")
            expr = expr.replace("++", "+")
            expr = expr.replace("(ε)", "")
            expr = re.sub(r'\(\)', '', expr)
            expr = re.sub(r'\b\+ *\b', '+', expr)

            self.resultats[var] = expr
            self.etapes.append(f"{var} = {expr}")

        self.etapes.append("🎯 Système totalement résolu.")


    def _parser_systeme(self):
        lignes = self.systeme_texte.splitlines()
        for ligne in lignes:
            if '=' in ligne:
                gauche, droite = ligne.split('=')
                self.equations[gauche.strip()] = droite.strip()

    def _analyser_expression(self, var, expr):
        termes = re.split(r'\s*\+\s*', expr)
        coeff_self = None
        autres = {}
        const = ''

        for terme in termes:
            terme = terme.strip()
            if terme == "ε":
                const = "ε"
            elif re.fullmatch(rf"[a-z]+{var}", terme):
                coeff_self = terme[:-len(var)]
            elif re.fullmatch(r"[a-z]+X\d+", terme):
                m = re.match(r"([a-z]+)(X\d+)", terme)
                if m:
                    autres[m.group(2)] = m.group(1)
            elif re.fullmatch(r"[a-z]+", terme):
                const = terme

        return coeff_self, autres, const

    def _expr_dict_to_str(self, d):
        return ' + '.join([f"{v}{k}" for k, v in d.items()])

    def _remplacer_variable(self, cible, valeur):
        nouvelles_equations = {}
        for var, expr in self.equations.items():
            if var == cible:
                continue
            expr_mod = re.sub(f"{cible}", f"({valeur})", expr)
            expr_mod = expr_mod.replace('+ ε', '').replace('ε +', '')
            nouvelles_equations[var] = expr_mod
            if cible in expr:
                self.etapes.append(f"🔁 Substitution : {var} = {expr} → {expr_mod}")
        self.equations = nouvelles_equations

    def get_resultats(self):
        return self.resultats

    def get_etapes(self):
        return self.etapes




def simplify_expression(expr: str) -> str:
    """
    Simplifie une expression régulière selon les règles suivantes :
    - aε = a, εa = a
    - Aε = A, A*ε = A*
    - a+a = a, A+A = A
    - Suppression des parenthèses inutiles :
      * (a) → a
      * a(b(a+b)*) → ab(a+b)*
      * ((a+b)) → (a+b)
    - Élimination des doublons dans les alternatives
    """
    if not expr:
        return expr

    # Normalisation : supprimer les espaces et normaliser les symboles spéciaux
    expr = expr.replace(' ', '').replace('∅', '')
    
    old_expr = None
    while expr != old_expr:
        old_expr = expr
        
        # === 1. Simplification des parenthèses ===
        # (a) → a
        expr = re.sub(r'\((\w)\)', r'\1', expr)
        # (abc) → abc
        expr = re.sub(r'\(([^()*+]+)\)', r'\1', expr)
        # ((a+b)) → (a+b)
        expr = re.sub(r'\(\(([^()]+)\)\)', r'(\1)', expr)
        # a(b(a+b)*) → ab(a+b)*
        expr = re.sub(r'(\w+)\((\w+)\(([^()]+)\)\*\)', r'\1\2(\3)*', expr)
        # (a+b)(a+b)* → (a+b)+
        expr = re.sub(r'\(([^()]+)\)\((\1)\)\*', r'(\1)+', expr)
        
        # === 2. Simplification du epsilon (ε) ===
        expr = re.sub(r'\.ε', '', expr)                  # .ε → supprimé
        expr = re.sub(r'(\*|\))ε(\b|$)', r'\1', expr)    # *ε ou )ε → * ou )
        expr = re.sub(r'ε\.', '', expr)                  # ε. → supprimé
        
        # === 3. Simplification de la concaténation ===
        expr = re.sub(r'(\w)\.', r'\1', expr)           # a.b → ab
        expr = re.sub(r'\)\.\(', ')(', expr)             # ).( → )(
        expr = re.sub(r'\*\.', '*', expr)               # *. → *
        
        # === 4. Simplification des alternatives ===
        # Gestion des cas a + a → a
        expr = re.sub(r'\b(\w+)\+\1\b', r'\1', expr)
        expr = re.sub(r'\(([^()]+)\)\+\(\1\)', r'\1', expr)
        expr = re.sub(r'\b(\w+)\+\(\1\)|\(\1\)\+\1', r'\1', expr)
        
        # Élimination des doublons dans les alternatives
        parts = [p.strip() for p in expr.split('+') if p.strip()]
        unique_parts = []
        seen = set()
        for part in parts:
            if part not in seen:
                seen.add(part)
                unique_parts.append(part)
        expr = '+'.join(unique_parts)
        
        # Simplification des alternatives vides
        if expr == '':
            expr = '∅'
    
    return expr


def automate_to_expression(automate_id):
    automate = Automate.objects.prefetch_related('etats', 'transitions').get(id=automate_id)

    # Étape 1 : Émoder l’automate
    emode_result = emoder_automate(automate)
    etats = emode_result['etats']
    transitions = emode_result['transitions']
    
    noms_etats = {etat.nom: etat for etat in etats}
    etat_index = {etat.nom: i for i, etat in enumerate(etats)}
    equations = defaultdict(list)
    finals = set()
    initial = None

    for t in transitions:
        i, j = t.source.nom, t.cible.nom
        symbol = t.symbole.strip() or 'ε'
        equations[i].append((symbol, j))

    for etat in etats:
        if etat.est_initial:
            initial = etat.nom
        if etat.est_final:
            finals.add(etat.nom)

    langages = {e.nom: '' for e in etats}
    for etat in etats:
        parts = []
        for symb, cible in equations[etat.nom]:
            parts.append(f'{symb}.{cible}')
        if etat.nom in finals:
            parts.append('ε')
        langages[etat.nom] = ' + '.join(parts) if parts else '∅'

    def substitute(expr, var, val):
        return expr.replace(f'{var}', f'({val})').replace(var, f'({val})')

    for k in reversed(range(len(etats))):
        ek = etats[k].nom
        expr = langages[ek]
        A_parts, B_parts = [], []
        for part in expr.split('+'):
            part = part.strip()
            if f'.{ek}' in part or part == ek:
                A_parts.append(part.replace(f'.{ek}', '').strip())
            else:
                B_parts.append(part)
        A = ' + '.join(A_parts).strip()
        B = ' + '.join(B_parts).strip()
        if A:
            langages[ek] = f'({A})*({B})' if B else f'({A})*'
        else:
            langages[ek] = B

        for j in range(k):
            ej = etats[j].nom
            langages[ej] = substitute(langages[ej], ek, langages[ek])

    expr_finale = simplify_expression(langages[initial])
    return expr_finale




from collections import defaultdict
from .models import Automate, Etat, Transition

def extraire_expression_reguliere(automate: Automate) -> str:
    # Étape 1 : Chargement des états
    etats = list(automate.etats.all())
    transitions = automate.transitions.all()

    noms = [e.nom for e in etats]
    n = len(etats)
    index_etat = {etats[i].nom: i for i in range(n)}
    M = [['∅' for _ in range(n)] for _ in range(n)]

    # Étape 2 : Remplir la matrice initiale
    for t in transitions:
        i = index_etat[t.source.nom]
        j = index_etat[t.cible.nom]
        symbole = t.symbole
        if M[i][j] == '∅':
            M[i][j] = symbole
        else:
            M[i][j] = f"{M[i][j]}+{symbole}"

    # Ajouter ε pour les boucles
    for i in range(n):
        nom = etats[i].nom
        sorties = [t for t in transitions if t.source.nom == nom and t.cible.nom == nom]
        for t in sorties:
            if M[i][i] == '∅':
                M[i][i] = t.symbole
            else:
                M[i][i] = f"{M[i][i]}+{t.symbole}"

    # Trouver l’état initial et final
    initiales = [e for e in etats if e.est_initial]
    finaux = [e for e in etats if e.est_final]
    if len(initiales) != 1 or len(finaux) != 1:
        raise ValueError("L'automate doit avoir un seul état initial et un seul état final pour cet algorithme.")

    i0 = index_etat[initiales[0].nom]
    f0 = index_etat[finaux[0].nom]

    # Élimination des autres états
    for k in range(n):
        if k == i0 or k == f0:
            continue
        for i in range(n):
            for j in range(n):
                if i == k or j == k:
                    continue
                Rik = M[i][k]
                Rkk = M[k][k]
                Rkj = M[k][j]
                if Rik == '∅' or Rkj == '∅':
                    continue
                part1 = Rik
                if Rkk != '∅':
                    part1 += f"({Rkk})*"
                part1 += Rkj
                if M[i][j] == '∅':
                    M[i][j] = part1
                else:
                    M[i][j] = f"{M[i][j]}+{part1}"
        # Nettoyer ligne/colonne k
        for i in range(n):
            M[i][k] = '∅'
            M[k][i] = '∅'
        M[k][k] = '∅'

    # Dernière expression
    result = M[i0][f0]
    if result == '∅':
        return '∅'
    return result






# from django.db import transaction
# from .models import Automate

# def supprimer_automates():
#     """
#     Supprime tous les automates dont les IDs sont compris entre 9 et 100 (inclus).
    
#     Returns:
#         tuple: (nombre_supprime, liste_ids_supprimes)
#     """
#     with transaction.atomic():
#         # Récupère les automates concernés
#         automates_a_supprimer = Automate.objects.filter(id__gte=45, id__lte=185)
        
#         # Récupère la liste des IDs avant suppression pour le retour
#         ids_supprimes = list(automates_a_supprimer.values_list('id', flat=True))
        
#         # Supprime en masse
#         nombre_supprime, _ = automates_a_supprimer.delete()
        
#     return nombre_supprime, ids_supprimes

# # n,m = supprimer_automates()