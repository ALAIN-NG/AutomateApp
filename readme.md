# README - TP INF3421 : Implémentation d'Opérations sur les Automates

## Description du Projet

Ce projet consiste en une application web développée dans le cadre du TP INF3421, permettant d'implémenter et de visualiser diverses opérations sur les automates finis. L'application offre une interface conviviale pour effectuer des conversions entre différents types d'automates (AFN, AFD, epsilon-AFN), résoudre des systèmes d'équations pour obtenir des expressions régulières, émonder des automates, calculer des epsilon-fermetures, et bien plus encore.

## Fonctionnalités Implémentées

L'application prend en charge les fonctionnalités suivantes :

- **Résolution d'un système d'équations** : Génération d'une expression régulière à partir d'un système d'équations.
- **Conversions entre automates** :
  - AFN vers AFD
  - AFD vers AFDC (Automate Fini Déterministe Complet)
  - AFD vers AFN
  - AFN vers epsilon-AFN et vice-versa
  - epsilon-AFN vers AFD
  - AFD vers epsilon-AFN
- **Extraction d'expression régulière** : À partir d'un automate (AFN ou AFD).
- **Identification des états** :
  - États accessibles
  - États co-accessibles
  - États utiles (accessibles et co-accessibles)
- **Émondage d'un automate** : Réduction de l'automate à ses états utiles.
- **Calcul des epsilon-fermetures** : Pour un état donné d'un epsilon-AFN.
- **Construction de Thompson** : Génération d'un epsilon-AFN à partir d'une expression régulière.
- **Minimisation d'automate** : Obtention de l'AFD minimal équivalent.
- **Algorithme de Gloushkov** : Construction d'un automate à partir d'une expression régulière.
- **Canonisation d'un automate**
- **Opérations de clôture** : Union, intersection, complémentation, concaténation, etc.

## Structure du Projet

Le projet est organisé comme suit :

```
.
├── Automates
│   ├── admin.py                # Configuration de l'interface d'administration Django
│   ├── algorithmes.py          # Implémentation des algorithmes sur les automates
│   ├── apps.py                 # Configuration de l'application Automates
│   ├── forms.py                # Définition des formulaires pour les opérations sur les automates
│   ├── migrations              # Migrations de la base de données
│   ├── models.py               # Modèles de données pour les automates
│   ├── regex_simplifier.py     # Fonctions pour simplifier les expressions régulières
│   ├── regular.py              # Fonctions pour les opérations sur les expressions régulières
│   ├── templates               # Templates HTML pour l'interface utilisateur
│   │   └── automates
│   │       ├── ajouter_etat.html
│   │       ├── ajouter_transition.html
│   │       ├── base.html
│   │       ├── choisir_operation.html
│   │       ├── creer_automate.html
│   │       ├── details.html
│   │       ├── emodage_resultat.html
│   │       ├── epsilon_fermetures.html
│   │       ├── etats.html
│   │       ├── expreg_form.html
│   │       ├── expression_resultat.html
│   │       ├── liste.html
│   │       ├── operation_resultat.html
│   │       └── resolution_equations.html
│   ├── templatetags           # Filtres personnalisés pour les templates
│   ├── tests.py               # Tests unitaires
│   ├── urls.py                # Routes de l'application
│   └── views.py               # Logique des vues pour les opérations sur les automates
├── db.sqlite3                 # Base de données SQLite
├── manage.py                  # Script de gestion Django
└── TP_INF342
    ├── asgi.py                # Configuration ASGI pour le déploiement
    ├── settings.py            # Configuration du projet Django
    ├── urls.py                # Routes principales du projet
    └── wsgi.py                # Configuration WSGI pour le déploiement
```

## Prérequis

- Python 3.12 ou supérieur
- Django 4.2 ou supérieur
- Bibliothèques Python supplémentaires (si nécessaires, spécifiées dans `requirements.txt`)

## Installation

1. **Cloner le dépôt** :
   ```bash
   git clone [URL_DU_DEPOT]
   cd [NOM_DU_DEPOT]
   ```

2. **Créer un environnement virtuel** (recommandé) :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Linux/Mac
   venv\Scripts\activate     # Sur Windows
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

4. **Appliquer les migrations** :
   ```bash
   python manage.py migrate
   ```

5. **Lancer le serveur de développement** :
   ```bash
   python manage.py runserver
   ```

6. **Accéder à l'application** :
   Ouvrez un navigateur et allez à l'adresse `http://127.0.0.1:8000/`.

## Utilisation

1. **Créer un automate** :
   - Accédez à l'interface de création d'automate.
   - Ajoutez des états et des transitions.
   - Spécifiez les états initiaux et finaux.

2. **Effectuer des opérations** :
   - Sélectionnez une opération dans la liste (par exemple, conversion AFN vers AFD).
   - Suivez les instructions pour fournir les entrées nécessaires.
   - Visualisez le résultat de l'opération.

3. **Exporter/Réutiliser les résultats** :
   - Les automates générés peuvent être sauvegardés et réutilisés pour d'autres opérations.

## Contribution

Les contributions sont les bienvenues. Pour contribuer :

1. Forkez le projet.
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/nouvelle-fonctionnalite`).
3. Committez vos changements (`git commit -m 'Ajouter une nouvelle fonctionnalité'`).
4. Pushez vers la branche (`git push origin feature/nouvelle-fonctionnalite`).
5. Ouvrez une Pull Request.

## Auteurs

- [Liste des membres du groupe]
  - [Nom du chef de groupe] (Chef de groupe)
  - [Membre 2]
  - [Membre 3]
  - ...

## Licence

Ce projet est sous licence [MIT]. Voir le fichier `LICENSE` pour plus de détails.

## Remerciements

Nous remercions [Etienne Kouokam] pour son encadrement et ses précieuses orientations tout au long de ce projet.