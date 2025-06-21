from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Automate, Etat, Transition
from .forms import *
from django.http import HttpResponseBadRequest
from collections import deque
from django.contrib import messages
from django.views.generic import FormView
from .algorithmes import *
from .regular import *

""" AFFICHAGES """

def liste_automates(request):
    automates = Automate.objects.all()
    return render(request, 'automates/liste.html', {'automates': automates})



def details_automate(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    etats = automate.etats.all()
    transitions = automate.transitions.all()
    return render(request, 'automates/details.html', {
        'automate': automate,
        'etats': etats,
        'transitions': transitions
    })


"""CREATIONS """

def creer_automate(request):
    if request.method == 'POST':
        form = AutomateForm(request.POST)
        if form.is_valid():
            automate = form.save()
            messages.success(request, "Automate créé avec succès !")
            return redirect('details_automate', automate_id=automate.id)
    else:
        form = AutomateForm()
    return render(request, 'automates/creer_automate.html', {'form': form, 'automate': None})


def ajouter_etat(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    if request.method == 'POST':
        form = EtatForm(request.POST)
        if form.is_valid():
            etat = form.save(commit=False)
            etat.automate = automate
            etat.save()
            messages.success(request, "État ajouté avec succès !")
            return redirect('details_automate', automate_id=automate.id)
    else:
        form = EtatForm()
    return render(request, 'automates/ajouter_etat.html', {'form': form, 'automate': automate})


def ajouter_transition(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    if request.method == 'POST':
        form = TransitionForm(request.POST or None, automate=automate)
        if form.is_valid():
            transition = form.save(commit=False)
            transition.automate = automate
            transition.save()
            messages.success(request, "Transition ajoutée avec succès !")
            return redirect('details_automate', automate_id=automate.id)
    else:
        form = TransitionForm(automate=automate)
    return render(request, 'automates/ajouter_transition.html', {'form': form, 'automate': automate})



"""MODIFICATIONS"""

def modifier_automate(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    if request.method == 'POST':
        form = AutomateForm(request.POST, instance=automate)
        if form.is_valid():
            form.save()
            messages.success(request, "Automate modifié avec succès !")
            return redirect('details_automate', automate_id=automate.id)
    else:
        form = AutomateForm(instance=automate)
    return render(request, 'automates/creer_automate.html', {'form': form, 'automate': automate})


def modifier_etat(request, etat_id):
    etat = get_object_or_404(Etat, id=etat_id)
    automate = etat.automate
    if request.method == 'POST':
        form = EtatForm(request.POST, instance=etat)
        if form.is_valid():
            form.save()
            messages.success(request, "État modifié avec succès !")
            return redirect('details_automate', automate_id=automate.id)
    else:
        form = EtatForm(instance=etat)
    return render(request, 'automates/ajouter_etat.html', {'form': form, 'automate': automate, 'etat': etat})


def modifier_transition(request, transition_id):
    transition = get_object_or_404(Transition, id=transition_id)
    automate = transition.automate
    if request.method == 'POST':
        form = TransitionForm(request.POST or None, instance=transition, automate=automate)
        if form.is_valid():
            form.save()
            messages.success(request, "Transition modifiée avec succès !")
            return redirect('details_automate', automate_id=automate.id)
    else:
        form = TransitionForm(instance=transition, automate=automate)
    return render(request, 'automates/ajouter_transition.html', {'form': form, 'automate': automate, 'transition': transition})


"""SUPPRESSIONS"""

def supprimer_automate(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    automate.delete()
    messages.success(request, "Automate supprimé avec succès.")
    return redirect('liste_automates')

def supprimer_etat(request, etat_id):
    etat = get_object_or_404(Etat, id=etat_id)
    automate_id = etat.automate.id
    etat.delete()
    messages.success(request, "État supprimé avec succès.")
    return redirect('details_automate', automate_id=automate_id)

def supprimer_transition(request, transition_id):
    transition = get_object_or_404(Transition, id=transition_id)
    automate_id = transition.automate.id
    transition.delete()
    messages.success(request, "Transition supprimée avec succès.")
    return redirect('details_automate', automate_id=automate_id)



"""tEST DE MOT"""


def tester_mot(request, automate_id):
    if request.method != "POST":
        return JsonResponse({'valide': False, 'erreur': 'Méthode non autorisée'}, status=405)
    
    mot = request.POST.get("mot", "")
    automate = get_object_or_404(Automate, id=automate_id)
    
    # Préparation des données
    transitions = automate.transitions.select_related('source', 'cible').all()
    etats = automate.etats.all()
    epsilon = 'ε'
    
    # Vérification des états initiaux/finaux
    etats_initiaux = [e.nom for e in etats.filter(est_initial=True)]
    etats_finaux = {e.nom for e in etats.filter(est_final=True)}
    
    if not etats_initiaux:
        return JsonResponse({
            'valide': False,
            'message': "Aucun état initial défini dans l'automate",
            'detail': "L'automate doit avoir au moins un état initial"
        }, status=400)
    
    # Construction du graphe de transition
    transitions_dict = {}
    for trans in transitions:
        if trans.source.nom not in transitions_dict:
            transitions_dict[trans.source.nom] = {}
        symbole = trans.symbole if trans.symbole != epsilon else ''
        if symbole not in transitions_dict[trans.source.nom]:
            transitions_dict[trans.source.nom][symbole] = []
        transitions_dict[trans.source.nom][symbole].append({
            'cible': trans.cible.nom,
            'id': trans.id  # Pour l'animation dans le frontend
        })
    
    # Fonction de fermeture epsilon
    def epsilon_closure(etats):
        fermeture = set(etats)
        queue = deque(etats)
        while queue:
            etat = queue.popleft()
            if etat in transitions_dict and '' in transitions_dict[etat]:
                for transition in transitions_dict[etat]['']:
                    if transition['cible'] not in fermeture:
                        fermeture.add(transition['cible'])
                        queue.append(transition['cible'])
        return fermeture
    
    # Algorithme pour trouver un chemin valide
    def trouver_chemin(etats_courants, pos, chemin):
        if pos == len(mot):
            if any(etat in etats_finaux for etat in etats_courants):
                return chemin
            return None
        
        lettre = mot[pos]
        transitions_possibles = []
        
        # Explorer d'abord les transitions non-epsilon
        for etat in etats_courants:
            if etat in transitions_dict:
                if lettre in transitions_dict[etat]:
                    for transition in transitions_dict[etat][lettre]:
                        transitions_possibles.append((
                            transition['cible'],
                            pos + 1,
                            chemin + [{
                                'source': etat,
                                'cible': transition['cible'],
                                'symbole': lettre,
                                'id': transition['id']
                            }]
                        ))
        
        # Si aucune transition normale, essayer epsilon-transitions
        if not transitions_possibles:
            for etat in etats_courants:
                if etat in transitions_dict and '' in transitions_dict[etat]:
                    for transition in transitions_dict[etat]['']:
                        transitions_possibles.append((
                            transition['cible'],
                            pos,
                            chemin + [{
                                'source': etat,
                                'cible': transition['cible'],
                                'symbole': epsilon,
                                'id': transition['id']
                            }]
                        ))
        
        # Trier pour prioriser les transitions consommant des lettres
        transitions_possibles.sort(key=lambda x: -x[1])
        
        for etat_suivant, new_pos, new_chemin in transitions_possibles:
            result = trouver_chemin(epsilon_closure([etat_suivant]), new_pos, new_chemin)
            if result is not None:
                return result
        
        return None
    
    # Trouver un chemin valide
    chemin_complet = trouver_chemin(epsilon_closure(etats_initiaux), 0, [])
    
    if chemin_complet is None:
        return JsonResponse({
            'valide': False,
            'message': f"Le mot '{mot}' n'est pas accepté par l'automate",
            'detail': "Aucun chemin valide trouvé pour ce mot",
            'mot': mot,
            'automate': automate.nom
        })
    
    # Préparer la réponse pour l'animation
    chemin_animation = []
    for transition in chemin_complet:
        chemin_animation.append({
            'source': transition['source'],
            'cible': transition['cible'],
            'symbole': transition['symbole'],
            'id': transition['id']
        })
    
    return JsonResponse({
        'valide': True,
        'chemins': [chemin_animation],  # Format attendu par le frontend
        'mot': mot,
        'automate': automate.nom,
    })


""" Operations sur les automates """

def union_automates(request, id1, id2):
    a1 = get_object_or_404(Automate, id=id1)
    a2 = get_object_or_404(Automate, id=id2)

    etapes, result = faire_union(a1, a2)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [a1, a2],
        'automate_resultat': result,
        'etapes': etapes,
        'operation': 'Union'
    })



def intersection_automates(request, id1, id2):
    a1 = get_object_or_404(Automate, id=id1)
    a2 = get_object_or_404(Automate, id=id2)

    etapes, resultat = faire_intersection(a1, a2)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [a1, a2],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Intersection'
    })


def determiniser_automate(request, automate_id):
    afn = get_object_or_404(Automate, id=automate_id)
    try:
        etapes, afd = determiniser(afn)
        error = None
    except ValueError as e:
        afd = None
        etapes = []
        error = str(e)
    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [afn],
        'automate_resultat': afd,
        'etapes': etapes,
        'operation': 'Déterminisation',
        'error': error
    })


def choisir_operation(request):
    operations = {
        'union': 2,
        'intersection': 2,
        'complementaire': 1,
        'determinisation': 1,
        'minimisation': 1,
        'canonisation': 1,
        'etoile_kleene': 1,
        'analyse_etats': 1,
        'emodage': 1,
        'expression': 1,
        'Miroir': 1, 
        'completion': 1,
        'AFD_vers_AFN': 1,
        'epsilon-AFN_vers_AFD': 1,
        'epsilon-AFN_vers_AFN': 1,
        'AFD_vers_epsilon-AFN': 1,
        'AFN_vers_epsilon-AFN': 1,
        'Fermeture': 1,
        'Concatenation': 2,
        'difference': 2,
        'quotient': 2,
    }

    if request.method == "POST":
        operation = request.POST.get('operation')
        selected_ids = request.POST.getlist('automates')

        if operation not in operations:
            return HttpResponseBadRequest("Opération invalide")

        nb_requis = operations[operation]
        if len(selected_ids) != nb_requis:
            return HttpResponseBadRequest(f"L'opération '{operation}' nécessite {nb_requis} automate(s)")

        # Redirections vers les opérations
        if operation == 'union':
            return redirect('union_automates', id1=selected_ids[0], id2=selected_ids[1])
        if operation == 'difference':
            return redirect('difference_automates', id1=selected_ids[0], id2=selected_ids[1])
        if operation == 'quotient':
            return redirect('quotient_automates', id1=selected_ids[0], id2=selected_ids[1])
        elif operation == 'intersection':
            return redirect('intersection_automates', id1=selected_ids[0], id2=selected_ids[1])
        elif operation == 'complementaire':
            return redirect('complement_automate', id=selected_ids[0])
        elif operation == 'determinisation':
            return redirect('determiniser_automate', automate_id=selected_ids[0])
        elif operation == 'minimisation':
            return redirect('minimiser_automate', automate_id=selected_ids[0])
        elif operation == 'canonisation':
            return redirect('canoniser_automate', automate_id=selected_ids[0])
        elif operation == 'etoile_kleene':
            return redirect('etoile_kleene', automate_id=selected_ids[0])
        elif operation == 'analyse_etats':
            return redirect('analyse_etats', automate_id=selected_ids[0])
        elif operation == 'emodage':
            return redirect('emoder_automate', automate_id=selected_ids[0])
        elif operation == 'expression':
            return redirect('automate_expression', automate_id=selected_ids[0])
        elif operation == 'completion':
            return redirect('completion', automate_id=selected_ids[0])
        elif operation == 'AFD_vers_AFN':
            return redirect('AFD_vers_AFN', automate_id=selected_ids[0])
        elif operation == 'epsilon-AFN_vers_AFD':
            return redirect('epsilon-AFN_vers_AFD', automate_id=selected_ids[0])
        elif operation == 'epsilon-AFN_vers_AFN':
            return redirect('epsilon-AFN_vers_AFN', automate_id=selected_ids[0])
        elif operation == 'AFD_vers_epsilon-AFN':
            return redirect('AFD_vers_epsilon-AFN', automate_id=selected_ids[0])
        elif operation == 'AFN_vers_epsilon-AFN':
            return redirect('AFN_vers_epsilon-AFN', automate_id=selected_ids[0])
        elif operation == 'Fermeture':
            return redirect('Fermeture', automate_id=selected_ids[0])
        elif operation == 'Miroir':
            return redirect('Miroir', automate_id=selected_ids[0])
        elif operation == 'Concatenation':
            return redirect('Concatenation', id1=selected_ids[0], id2=selected_ids[1])

    automates = Automate.objects.all()
    return render(request, 'automates/choisir_operation.html', {
        'automates': automates,
    })


def complement_automate(request, id):
    automate = get_object_or_404(Automate, id=id)
    try:
        etapes, resultat = faire_complementaire(automate)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)
    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Complémentaire',
        'error': error
    })



def minimiser_automate(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    try:
        etapes, resultat = faire_minimisation(automate)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)
    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Minimisation',
        'error': error
    })



def canoniser_automate(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    try:
        etapes, resultat = faire_canonisation(automate)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)
    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Canonisation',
        'error': error
    })



def etoile_kleene(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)

    try:
        resultat = cloture_etoile(automate)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('details_automate', automate_id=automate.id)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        # 'etapes': etapes,
        'operation': 'etoile_kleene'
    })


def cloture_concatenation(request, id1, id2):
    a1 = get_object_or_404(Automate, id=id1)
    a2 = get_object_or_404(Automate, id=id2)

    etapes, resultat = concatenation(a1, a2)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [a1, a2],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Cloture par Concatenation'
    })



def cloture_miroir(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)

    etapes, resultat = miroir(automate)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Clôture par Miroir'
    })



def cloture_difference(request, id1, id2):
    a1 = get_object_or_404(Automate, id=id1)
    a2 = get_object_or_404(Automate, id=id2)

    try:
        etapes, resultat = difference(a1, a2)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [a1, a2],
        'automate_resultat': resultat,
        'etapes': etapes,
        'error': error,
        'operation': f"Clôture par Différence ({a1.nom} \\ {a2.nom})"
    })

def cloture_quotient(request, id1, id2):
    a_b = get_object_or_404(Automate, id=id1)  # B
    a_a = get_object_or_404(Automate, id=id2)  # A

    try:
        etapes, resultat = quotient_gauche(a_b, a_a)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [a_b, a_a],
        'automate_resultat': resultat,
        'etapes': etapes,
        'error': error,
        'operation': f"Clôture par Quotient à Gauche ({a_b.nom} / {a_a.nom})"
    })





def analyse_etats(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)

    try:
        accessibles = etats_accessibles(automate)
        coaccessibles = etats_coaccessibles(automate)
        utiles = etats_utiles(automate)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('details_automate', automate_id=automate.id)

    return render(request, 'automates/etats.html', {
        'automate': automate,
        'accessibles': sorted(accessibles, key=lambda x: x.nom),
        'coaccessibles': sorted(coaccessibles, key=lambda x: x.nom),
        'utiles': sorted(utiles, key=lambda x: x.nom),
    })
    
    


def completer_automate(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    try:
        etapes, resultat = completion(automate)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)
    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Complétion',
        'error': error
    })


def epsilon_fermeture(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    fermetures = calculer_epsilon_fermetures(automate) 

    context = {
        'automate': automate,
        'fermetures': fermetures
    }
    return render(request, 'automates/epsilon_fermetures.html', context)




def afd_vers_afn(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)

    try:
        etapes, resultat = convertir_afd_en_afn(automate)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('details_automate', automate_id=automate.id)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'Conversion AFD vers AFN'
    })





def afn_vers_efn(request, automate_id):
    automate = get_object_or_404(Automate, id = automate_id)
    try:
        etapes, resultat = convertir_afn_vers_efn(automate)
        error = None

    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)
    
    return render(request, 'automates/operation_resultat.html',{
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'AFN vers EFN',
        'error': error,
    })

def afd_vers_efn(request, automate_id):
    automate = get_object_or_404(Automate, id = automate_id)
    try:
        etapes, resultat = convertir_afd_vers_efn(automate)
        error = None

    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)
    
    return render(request, 'automates/operation_resultat.html',{
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': 'AFD vers EFN',
        'error': error,
    })




def convertir_epsilon_vers_afn(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    try:
        resultat, etapes = eliminer_transitions_epsilon(automate)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': "Conversion epsilon-AFN vers AFN",
        'error': error
    })



def convertir_epsilon_vers_afd(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    try:
        etapes, resultat = eliminer_epsilon_et_determiniser(automate)
        error = None
    except ValueError as e:
        resultat = None
        etapes = []
        error = str(e)

    return render(request, 'automates/operation_resultat.html', {
        'automates_origine': [automate],
        'automate_resultat': resultat,
        'etapes': etapes,
        'operation': "Conversion epsilon-AFN vers AFD",
        'error': error
    })




def emoder_automate(request, automate_id):
    automate = get_object_or_404(Automate, pk=automate_id)
    
    # Analyse initiale
    accessibles = etats_accessibles(automate)
    coaccessibles = etats_coaccessibles(automate)
    utiles = accessibles & coaccessibles
    transitions_utiles = [
        t for t in automate.transitions.all() 
        if t.source in utiles and t.cible in utiles
    ]
    
    # Créer le nouvel automate émodé
    nouvel_automate = Automate.objects.create(
        nom=f"{automate.nom} (Émodé)",
        type=automate.type,
        alphabet=automate.alphabet
    )
    
    # Copier les états utiles
    etats_map = {}
    for etat in utiles:
        nouvel_etat = Etat.objects.create(
            automate=nouvel_automate,
            nom=etat.nom,
            est_initial=etat.est_initial,
            est_final=etat.est_final
        )
        etats_map[etat.id] = nouvel_etat
    
    # Copier les transitions utiles
    for transition in transitions_utiles:
        Transition.objects.create(
            automate=nouvel_automate,
            source=etats_map[transition.source_id],
            cible=etats_map[transition.cible_id],
            symbole=transition.symbole
        )
    
    return render(request, 'automates/emodage_resultat.html', {
        'operation': 'Émodage',
        'automates_origine': [automate],
        'automate_resultat': nouvel_automate,
        'etapes': [
            f"Analyse des états accessibles: {len(accessibles)} état(s)",
            f"Analyse des états co-accessibles: {len(coaccessibles)} état(s)",
            f"Identification des états utiles: {len(utiles)} état(s)",
            f"Transitions conservées: {len(transitions_utiles)} transition(s)",
            "Création du nouvel automate émodé"
        ]
    })
    


def generer_automate_expreg(request):
    if request.method == "POST":
        form = ExpressionReguliereForm(request.POST)
        if form.is_valid():
            expression = form.cleaned_data["expression"]
            algo = form.cleaned_data["algorithme"]

            if algo == "thompson":
                return redirect("generer_thompson", expression=expression)
            elif algo == "glushkov":
                return redirect("generer_glushkov", expression=expression)
    else:
        form = ExpressionReguliereForm()

    return render(request, "automates/expreg_form.html", {"form": form})



def generer_thompson(request, expression):
    try:
        builder = ThompsonBuilder(expression)
        automate = builder.create_automate()
        messages.success(request, f"Automate généré à partir de l'expression : {expression}")
        return redirect("details_automate", automate_id=automate.id)
    except Exception as e:
        messages.error(request, f"Erreur : {e}")
        return redirect("generer_automate_expreg")

    
def generer_glushkov(request, expression):
    try:
        automate = glushkov_to_django_automate(f"Glushkov({expression})", expression)
        
        messages.success(request, f"Automate généré avec Glushkov pour : {expression}")
        return redirect("details_automate", automate_id=automate.id)
    
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération de l'automate Glushkov : {e}")
        
        return redirect("generer_automate_expreg")
    



def expression_reguliere(request, automate_id):
    automate = get_object_or_404(Automate, id=automate_id)
    try:
        expression = automate_to_expression(automate_id)
    except ValueError as e:
        expression = f"Erreur : {str(e)}"

    return render(request, 'automates/expression_resultat.html', {
        'automate': automate,
        'expression': expression
    })








def resoudre_equations(request):
    resultats = {}
    etapes = []
    if request.method == 'POST':
        form = EquationForm(request.POST)
        if form.is_valid():
            systeme = form.cleaned_data['systeme']
            solver =EquationSolver(systeme)
            solver.resoudre()
            resultats = solver.get_resultats()
            etapes = solver.get_etapes()
    else:
        form = EquationForm()
    return render(request, 'automates/resolution_equations.html', {
        'form': form,
        'resultats': resultats,
        'etapes': etapes
    })


