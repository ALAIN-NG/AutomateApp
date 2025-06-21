from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_automates, name='liste_automates'),
    path('automate/creer/', views.creer_automate, name='creer_automate'),
    path('automate/<int:automate_id>/', views.details_automate, name='details_automate'),
    path('automate/<int:automate_id>/ajouter-etat/', views.ajouter_etat, name='ajouter_etat'),
    path('automate/<int:automate_id>/ajouter-transition/', views.ajouter_transition, name='ajouter_transition'),
    path('automate/<int:automate_id>/tester-mot/', views.tester_mot, name='tester_mot'),
    path('automate/<int:automate_id>/modifier/', views.modifier_automate, name='modifier_automate'),
    path('etat/<int:etat_id>/modifier/', views.modifier_etat, name='modifier_etat'),
    path('transition/<int:transition_id>/modifier/', views.modifier_transition, name='modifier_transition'),
    path('automate/<int:automate_id>/supprimer/', views.supprimer_automate, name='supprimer_automate'),
    path('etat/<int:etat_id>/supprimer/', views.supprimer_etat, name='supprimer_etat'),
    path('transition/<int:transition_id>/supprimer/', views.supprimer_transition, name='supprimer_transition'),
    
    
    path('operation/choisir/', views.choisir_operation, name='choisir_operation'),
    path('operation/union/<int:id1>/<int:id2>/', views.union_automates, name='union_automates'),
    path('operation/determinisation/<int:automate_id>/', views.determiniser_automate, name='determiniser_automate'),
    path('operation/intersection/<int:id1>/<int:id2>/', views.intersection_automates, name='intersection_automates'),
    path('operation/complementaire/<int:id>/', views.complement_automate, name='complement_automate'),
    path('operation/minimisation/<int:automate_id>/', views.minimiser_automate, name='minimiser_automate'),
    path('operation/completion/<int:automate_id>/', views.completer_automate, name='completion'),
    path('operation/canonisation/<int:automate_id>/', views.canoniser_automate, name='canoniser_automate'),
    path('operation/AFD_vers_AFN/<int:automate_id>/', views.afd_vers_afn, name='AFD_vers_AFN'),
    path('operation/epsilon-AFN_vers_AFN/<int:automate_id>/', views.convertir_epsilon_vers_afn, name='epsilon-AFN_vers_AFN'),
    path('operation/epsilon-AFN_vers_AFD/<int:automate_id>/', views.convertir_epsilon_vers_afd, name='epsilon-AFN_vers_AFD'),
    path('operation/AFD_vers_epsilon-AFN/<int:automate_id>/', views.afd_vers_efn, name='AFD_vers_epsilon-AFN'),
    path('operation/AFN_vers_epsilon-AFN/<int:automate_id>/', views.afn_vers_efn, name='AFN_vers_epsilon-AFN'),
    path('operation/Fermeture/<int:automate_id>/', views.epsilon_fermeture, name='Fermeture'),
    path('operation/Concatenation/<int:id1>/<int:id2>/', views.cloture_concatenation, name='Concatenation'),
    path('operation/Miroir/<int:automate_id>/', views.cloture_miroir, name='Miroir'),
    path('operation/difference/<int:id1>/<int:id2>/', views.cloture_difference, name='difference_automates'),
    path('operation/quotient/<int:id1>/<int:id2>/', views.cloture_quotient, name='quotient_automates'),
    path('operation/expression/<int:automate_id>/', views.expression_reguliere, name='automate_expression'),


    path('operation/etoile_kleene/<int:automate_id>/', views.etoile_kleene, name='etoile_kleene'),
    path('operation/analyse_etats/<int:automate_id>/', views.analyse_etats, name='analyse_etats'),
    path('automate/generer_expreg/', views.generer_automate_expreg, name='generer_automate_expreg'),
    path('automate/expreg/thompson/<str:expression>/', views.generer_thompson, name='generer_thompson'),
    path('automate/expreg/glushkov/<str:expression>/', views.generer_glushkov, name='generer_glushkov'),
    path('equations/', views.resoudre_equations, name='resoudre_equations'),
    path('<int:automate_id>/emoder/', views.emoder_automate, name='emoder_automate'),
]
