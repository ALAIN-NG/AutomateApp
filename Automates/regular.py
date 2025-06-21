from .models import Automate, Etat, Transition
import itertools
from django.core.exceptions import ValidationError

class ThompsonBuilder:
    def __init__(self, expression, user=None):
        self.expression = expression
        self.state_id = itertools.count()
        self.symbols = set()
        self.user = user

    def new_state_name(self):
        return f"q{next(self.state_id)}"

    def create_automate(self):
        # 1. Convertir l'expression en postfixée
        postfix = self.infix_to_postfix(self.expression)
        if postfix is None:
            raise ValueError("Expression invalide")
        
        # 2. Construire l'automate à partir du postfix
        nfa = self.build_from_postfix(postfix)

        # 3. Créer en base de données
        automate = Automate.objects.create(
            nom=f"Thompson({self.expression})",
            type="EFA",
            alphabet=",".join(sorted(self.symbols))
        )

        etat_objs = {}
        for name in nfa["etats"]:
            etat_objs[name] = Etat.objects.create(
                automate=automate,
                nom=name,
                est_initial=(name == nfa["initial"]),
                est_final=(name == nfa["final"])
            )

        for (src, symb, tgt) in nfa["transitions"]:
            Transition.objects.create(
                automate=automate,
                source=etat_objs[src],
                cible=etat_objs[tgt],
                symbole=symb
            )

        return automate

    def infix_to_postfix(self, expr):
        precedence = {'*': 3, '.': 2, '+': 1}
        output = []
        stack = []

        # Ajouter concaténation explicite
        expr = self.add_concat(expr)

        for token in expr:
            if token.isalnum():
                output.append(token)
            elif token == '(':
                stack.append(token)
            elif token == ')':
                while stack and stack[-1] != '(':
                    output.append(stack.pop())
                stack.pop()  # pop '('
            else:
                while stack and stack[-1] != '(' and precedence.get(token, 0) <= precedence.get(stack[-1], 0):
                    output.append(stack.pop())
                stack.append(token)

        while stack:
            output.append(stack.pop())
        return output

    def add_concat(self, expr):
        """Ajoute '.' pour concaténation implicite : ab -> a.b"""
        result = ""
        for i in range(len(expr)):
            c1 = expr[i]
            result += c1
            if i + 1 < len(expr):
                c2 = expr[i + 1]
                if (c1.isalnum() or c1 == ')' or c1 == '*') and (c2.isalnum() or c2 == '('):
                    result += '.'
        return result

    def build_from_postfix(self, postfix):
        stack = []

        for token in postfix:
            if token.isalnum():
                self.symbols.add(token)
                i = self.new_state_name()
                f = self.new_state_name()
                stack.append({
                    "etats": [i, f],
                    "transitions": [(i, token, f)],
                    "initial": i,
                    "final": f
                })
            elif token == '*':
                a = stack.pop()
                i = self.new_state_name()
                f = self.new_state_name()
                trans = a["transitions"] + [
                    (a["final"], 'ε', a["initial"]),
                    (i, 'ε', a["initial"]),
                    (a["final"], 'ε', f),
                    (i, 'ε', f),
                ]
                stack.append({
                    "etats": a["etats"] + [i, f],
                    "transitions": trans,
                    "initial": i,
                    "final": f
                })
            elif token == '.':
                b = stack.pop()
                a = stack.pop()
                trans = a["transitions"] + b["transitions"] + [(a["final"], 'ε', b["initial"])]
                stack.append({
                    "etats": a["etats"] + b["etats"],
                    "transitions": trans,
                    "initial": a["initial"],
                    "final": b["final"]
                })
            elif token == '+':
                b = stack.pop()
                a = stack.pop()
                i = self.new_state_name()
                f = self.new_state_name()
                trans = a["transitions"] + b["transitions"] + [
                    (i, 'ε', a["initial"]),
                    (i, 'ε', b["initial"]),
                    (a["final"], 'ε', f),
                    (b["final"], 'ε', f),
                ]
                stack.append({
                    "etats": a["etats"] + b["etats"] + [i, f],
                    "transitions": trans,
                    "initial": i,
                    "final": f
                })

        return stack.pop()




class GlushkovBuilder:
    def __init__(self, regex_expression):
        self.regex = regex_expression
        self.counter = itertools.count(start=1)
        self.symbols = set()
        self.positions = {}
        self.followpos = {}
        self.firstpos = set()
        self.lastpos = set()
        self.accepts_empty = False
        self.root_node = None

    def build(self):
        """Construit l'automate complet"""
        self.validate_regex()
        self.root_node = self.parse_regex()
        self.compute_positions(self.root_node)
        return self.create_automate()

    def validate_regex(self):
        """Valide la syntaxe de l'expression régulière"""
        if not self.regex:
            raise ValidationError("Expression vide")
        stack = 0
        for c in self.regex:
            if c == '(':
                stack += 1
            elif c == ')':
                stack -= 1
                if stack < 0:
                    raise ValidationError("Parentèses déséquilibrées")
        if stack != 0:
            raise ValidationError("Parentèses déséquilibrées")

    def parse_regex(self):
        """Parse l'expression et construit l'AST"""
        expr = self.add_concat_operators()
        postfix = self.infix_to_postfix(expr)
        return self.build_ast(postfix)

    def add_concat_operators(self):
        """Ajoute les opérateurs de concaténation explicites"""
        output = []
        for i, c in enumerate(self.regex):
            output.append(c)
            if i < len(self.regex) - 1:
                next_c = self.regex[i+1]
                if (c not in {'(', '|'} and 
                    next_c not in {')', '|', '*', '+', '?'}):
                    output.append('.')
        return ''.join(output)

    def infix_to_postfix(self, expr):
        """Conversion infixe vers postfixe"""
        precedence = {'*': 4, '+': 4, '?': 4, '.': 3, '|': 2}
        output = []
        stack = []

        for token in expr:
            if token.isalnum():
                output.append(token)
                self.symbols.add(token)
            elif token == '(':
                stack.append(token)
            elif token == ')':
                while stack and stack[-1] != '(':
                    output.append(stack.pop())
                stack.pop()
            else:
                while (stack and stack[-1] != '(' and 
                       precedence[token] <= precedence.get(stack[-1], 0)):
                    output.append(stack.pop())
                stack.append(token)

        while stack:
            output.append(stack.pop())
        return output

    class ASTNode:
        """Nœud de l'arbre de syntaxe"""
        def __init__(self, value, left=None, right=None):
            self.value = value
            self.left = left
            self.right = right
            self.position = None
            self.nullable = False
            self.firstpos = set()
            self.lastpos = set()

    def build_ast(self, postfix_expr):
        """Construit l'AST à partir de la notation postfixe"""
        stack = []
        for token in postfix_expr:
            if token.isalnum():
                stack.append(self.ASTNode(token))
            elif token == '*':
                stack.append(self.ASTNode(token, stack.pop()))
            elif token in {'+', '?'}:
                stack.append(self.ASTNode(token, stack.pop()))
            elif token in {'.', '|'}:
                right = stack.pop()
                left = stack.pop()
                stack.append(self.ASTNode(token, left, right))
        return stack[0] if stack else None

    def compute_positions(self, node):
        """Calcule les positions et relations followpos"""
        if node is None:
            return

        self.compute_positions(node.left)
        self.compute_positions(node.right)

        if node.value.isalnum():
            pos = next(self.counter)
            node.position = pos
            self.positions[pos] = node.value
            self.followpos[pos] = set()
            node.nullable = False
            node.firstpos = {pos}
            node.lastpos = {pos}
            
        elif node.value == '|':
            node.nullable = node.left.nullable or node.right.nullable
            node.firstpos = node.left.firstpos | node.right.firstpos
            node.lastpos = node.left.lastpos | node.right.lastpos
            
        elif node.value == '.':
            node.nullable = node.left.nullable and node.right.nullable
            node.firstpos = node.left.firstpos.copy()
            if node.left.nullable:
                node.firstpos.update(node.right.firstpos)
            node.lastpos = node.right.lastpos.copy()
            if node.right.nullable:
                node.lastpos.update(node.left.lastpos)
            for i in node.left.lastpos:
                self.followpos[i].update(node.right.firstpos)
                
        elif node.value == '*':
            node.nullable = True
            node.firstpos = node.left.firstpos.copy()
            node.lastpos = node.left.lastpos.copy()
            for i in node.lastpos:
                self.followpos[i].update(node.firstpos)
                
        elif node.value in {'+', '?'}:
            node.nullable = (node.value == '?') or node.left.nullable
            node.firstpos = node.left.firstpos.copy()
            node.lastpos = node.left.lastpos.copy()
            if node.value == '+':
                for i in node.lastpos:
                    self.followpos[i].update(node.firstpos)

        if node is self.root_node:
            self.firstpos = node.firstpos
            self.lastpos = node.lastpos
            self.accepts_empty = node.nullable

    def create_automate(self):
        """Crée l'automate dans la base de données"""
        automate = Automate.objects.create(
            nom=f"Glushkov({self.regex})",
            type="NFA",
            alphabet="".join(sorted(self.symbols)))
        
        # Création des états
        etat_map = {}
        if self.accepts_empty:
            q0 = Etat.objects.create(
                automate=automate,
                nom="q0",
                est_initial=True,
                est_final=True)
        
        for pos in self.positions:
            etat_map[pos] = Etat.objects.create(
                automate=automate,
                nom=f"q{pos}",
                est_initial=(pos in self.firstpos),
                est_final=(pos in self.lastpos))
        
        # Création des transitions
        for src_pos, symbol in self.positions.items():
            for dest_pos in self.followpos[src_pos]:
                Transition.objects.create(
                    automate=automate,
                    source=etat_map[src_pos],
                    cible=etat_map[dest_pos],
                    symbole=symbol)
        
        if self.accepts_empty:
            for pos in self.firstpos:
                Transition.objects.create(
                    automate=automate,
                    source=q0,
                    cible=etat_map[pos],
                    symbole=self.positions[pos])
        
        return automate














# Glushkov.py (ou dans un fichier utilitaire de votre app Django)

import re
from django.db import transaction
from .models import Automate, Etat, Transition

# --- Classes pour la construction de l'AST ---
class Node:
    """
    Représente un nœud dans l'arbre syntaxique abstrait (AST) de l'expression régulière.
    """
    def __init__(self, char=None, op=None):
        self.char = char  # Le caractère (pour les feuilles)
        self.op = op      # L'opérateur (*, |, ., +)
        self.left = None  # Enfant gauche (pour les opérateurs binaires et unaires)
        self.right = None # Enfant droit (pour les opérateurs binaires)
        self.nullable = False
        self.firstpos = set()
        self.lastpos = set()
        self.positions = set() # Pour les feuilles, contient la position unique
        self.is_leaf = (char is not None)

    def __repr__(self):
        if self.is_leaf:
            return f"Leaf('{self.char}' P:{self.positions})"
        if self.op == '*':
            return f"Star(Left={self.left})"
        return f"Op('{self.op}', Left={self.left}, Right={self.right})"

# Variables globales pour l'état de l'algorithme
global_position_counter = 0
global_followpos_map = {}
global_char_at_position = {}

def reset_glushkov_globals():
    global global_position_counter, global_followpos_map, global_char_at_position
    global_position_counter = 0
    global_followpos_map = {}
    global_char_at_position = {}

def create_leaf_node(char):
    global global_position_counter, global_char_at_position
    node = Node(char=char)
    global_position_counter += 1
    node.positions.add(global_position_counter)
    node.firstpos.add(global_position_counter)
    node.lastpos.add(global_position_counter)
    global_char_at_position[global_position_counter] = char
    if char == 'ε': # Epsilon, pour la chaîne vide
        node.nullable = True
    return node

def insert_concat_operators(regex):
    """
    Insère les opérateurs de concaténation explicites ('.')
    dans l'expression régulière.
    """
    new_regex = []
    i = 0
    while i < len(regex):
        current = regex[i]
        new_regex.append(current)

        if i + 1 < len(regex):
            next_char = regex[i+1]
            # La concaténation implicite se produit entre:
            # - un caractère ou epsilon et un caractère ou '(' ou epsilon
            # - un ')' et un caractère ou '(' ou epsilon
            # - un '*' et un caractère ou '(' ou epsilon
            # - un '+' (qui est maintenant un OR) et un caractère ou '(' ou epsilon
            # Cette condition inclut 'current == '+' si c'est un OR binaire.
            # Cependant, si '+' est un OR, il ne participe pas à une concaténation implicite après lui
            # de la même manière que '*' le ferait.
            # Revoir la logique: 'current' doit être quelque chose qui "produit" un résultat
            # avant le 'next_char'. C'est le cas pour les lettres, ')' et '*'.
            # Pour l'opérateur 'OU' ('|' ou '+'), il n'y a pas de concaténation implicite juste après.
            
            # Correction: '+' ne devrait pas initier une concaténation implicite
            # comme le ferait un caractère ou un star. Il est un opérateur binaire.
            if (current.isalnum() or current == ')' or current == '*') and \
               (next_char.isalnum() or next_char == '(' or next_char == 'ε'):
                new_regex.append('.')
        i += 1
    return "".join(new_regex)

def infix_to_postfix(regex):
    """
    Convertit une expression régulière infixée en notation post-fixée (RPN).
    Gère les parenthèses et la précédence des opérateurs.
    L'opérateur '+' a le même fonctionnement que '|'.
    """
    # Modification: '+' a la même précédence que '|'
    precedence = {'*': 3, '.': 2, '|': 1, '+': 1} 
    output = []
    operators = []

    processed_regex = insert_concat_operators(regex)
    print(f"Regex après insertion de '.': {processed_regex}")

    for char in processed_regex:
        if char.isalnum() or char == 'ε': # Opérandes (lettres ou epsilon)
            output.append(char)
        elif char == '(':
            operators.append(char)
        elif char == ')':
            while operators and operators[-1] != '(':
                output.append(operators.pop())
            if not operators or operators[-1] != '(':
                raise ValueError("Mismatching parentheses in regex.")
            operators.pop() # Pop the '('
        elif char in precedence: # Opérateurs
            while operators and operators[-1] != '(' and \
                  precedence.get(operators[-1], 0) >= precedence[char]:
                output.append(operators.pop())
            operators.append(char)
        else:
            raise ValueError(f"Caractère non reconnu dans l'expression régulière: '{char}'")
    
    while operators:
        if operators[-1] == '(':
            raise ValueError("Mismatching parentheses in regex.")
        output.append(operators.pop())
    
    return "".join(output)

def build_ast_from_postfix(postfix_regex):
    """
    Construit l'AST à partir de la notation post-fixée.
    L'opérateur '+' est traité comme un opérateur binaire d'union.
    """
    stack = []
    for char in postfix_regex:
        if char.isalnum() or char == 'ε': # Feuille
            stack.append(create_leaf_node(char))
        elif char == '*': # Unaire (Kleene Star)
            if not stack: raise ValueError(f"Erreur de syntaxe: '*' sans opérande précédent dans {postfix_regex}")
            operand = stack.pop()
            node = Node(op='*')
            node.left = operand
            stack.append(node)
        # Modification: '+' est traité comme un opérateur binaire d'union
        elif char in ('.', '|', '+'): # Binaire (concaténation, union, ou notre nouveau 'OU')
            if len(stack) < 2: raise ValueError(f"Erreur de syntaxe: '{char}' sans deux opérandes précédents dans {postfix_regex}")
            right_operand = stack.pop()
            left_operand = stack.pop()
            node = Node(op=char) # Le nœud aura l'opérateur ('.', '|', ou '+')
            node.left = left_operand
            node.right = right_operand
            stack.append(node)
        else:
            raise ValueError(f"Caractère opérateur non géré en post-fixé: '{char}'")
    
    if len(stack) != 1:
        raise ValueError(f"Erreur de syntaxe: Pile d'AST invalide à la fin de {postfix_regex}")
    return stack.pop() # La racine de l'AST

def compute_glushkov_sets(node):
    """
    Calcule nullable, firstpos, lastpos récursivement pour chaque nœud de l'AST.
    Met à jour global_followpos_map.
    """
    if node.is_leaf:
        return

    # Parcourir les enfants d'abord (post-ordre)
    if node.left:
        compute_glushkov_sets(node.left)
    if node.right:
        compute_glushkov_sets(node.right)

    if node.op == '*':
        node.nullable = True
        node.firstpos = node.left.firstpos
        node.lastpos = node.left.lastpos
        for pos_last in node.left.lastpos:
            global_followpos_map.setdefault(pos_last, set()).update(node.left.firstpos)

    # Modification: La logique pour '+' est la même que pour '|'
    elif node.op == '|' or node.op == '+': 
        node.nullable = node.left.nullable or node.right.nullable
        node.firstpos = node.left.firstpos.union(node.right.firstpos)
        node.lastpos = node.left.lastpos.union(node.right.lastpos)

    elif node.op == '.': # Concaténation
        node.nullable = node.left.nullable and node.right.nullable
        
        if node.left.nullable:
            node.firstpos = node.left.firstpos.union(node.right.firstpos)
        else:
            node.firstpos = node.left.firstpos

        if node.right.nullable:
            node.lastpos = node.left.lastpos.union(node.right.lastpos)
        else:
            node.lastpos = node.right.lastpos

        for pos_last in node.left.lastpos:
            global_followpos_map.setdefault(pos_last, set()).update(node.right.firstpos)


def glushkov_to_django_automate(regex_name, input_regex):
    """
    Construit un automate AFN à partir d'une expression régulière
    et l'enregistre dans la base de données Django.
    """
    reset_glushkov_globals() # Réinitialiser les globales pour une nouvelle exécution

    try:
        # 1. Convertir en post-fixé et construire l'AST
        postfix_regex = infix_to_postfix(input_regex) 
        print(f"Expression régulière post-fixée: {postfix_regex}")
        ast_root = build_ast_from_postfix(postfix_regex)

        # 2. Calculer les ensembles (nullable, firstpos, lastpos, et remplir followpos_map)
        compute_glushkov_sets(ast_root)

        # 3. Construire l'AFN et l'enregistrer dans Django
        with transaction.atomic():
            # Créer l'objet Automate
            all_leaf_chars = set(global_char_at_position.values())
            alphabet_chars = sorted(list(c for c in all_leaf_chars if c != 'ε'))
            alphabet_str = ",".join(alphabet_chars)

            automate = Automate.objects.create(
                nom=regex_name,
                type='NFA', # Glushkov construit un NFA
                alphabet=alphabet_str
            )

            # Créer les objets Etat
            # Utilisation d'un dictionnaire pour mapper les positions (P1, P2, ...)
            # aux objets Etat Django (q1, q2, ...) et aussi pour S0 (q0).
            django_states_by_pos = {} # Map Glushkov_position -> Etat_Django_Object
            django_states_by_qname = {} # Map q_name -> Etat_Django_Object

            # État initial q0
            # Il est toujours q0 et a le premier id Django
            initial_django_state = Etat.objects.create(
                automate=automate,
                nom="q0",
                est_initial=True,
                est_final=False # Sera mis à jour si l'expression est nullable
            )
            django_states_by_qname["q0"] = initial_django_state

            # Mapping des positions Glushkov (1, 2, ...) aux noms d'états (q1, q2, ...)
            # Nous réservons q0 pour l'état initial virtuel.
            # Donc, position 1 devient q1, position 2 devient q2, etc.
            glushkov_pos_to_q_name_map = {}
            current_q_number = 1 # q1, q2, ...
            
            # Tri des positions pour un nommage déterministe
            sorted_positions = sorted(global_char_at_position.keys())

            for pos in sorted_positions:
                q_name = f"q{current_q_number}"
                glushkov_pos_to_q_name_map[pos] = q_name
                
                # Créer l'état Django
                is_final_state = (pos in ast_root.lastpos)
                
                django_state = Etat.objects.create(
                    automate=automate,
                    nom=q_name,
                    est_initial=False, # q0 est le seul initial
                    est_final=is_final_state
                )
                django_states_by_pos[pos] = django_state
                django_states_by_qname[q_name] = django_state # Pour référence facile

                current_q_number += 1

            # Si l'expression est nullable, l'état initial q0 est aussi final
            if ast_root.nullable:
                initial_django_state.est_final = True
                initial_django_state.save()

            # Créer les Transitions
            # Transitions depuis l'état initial q0
            for pos_first in ast_root.firstpos:
                target_state = django_states_by_pos[pos_first]
                Transition.objects.create(
                    automate=automate,
                    source=initial_django_state,
                    symbole=global_char_at_position[pos_first],
                    cible=target_state
                )

            # Transitions basées sur followpos
            for pos_source, follow_set in global_followpos_map.items():
                source_django_state = django_states_by_pos.get(pos_source)
                if not source_django_state:
                    print(f"AVERTISSEMENT: État source (pos {pos_source}) non trouvé pour une transition.")
                    continue

                for pos_dest in follow_set:
                    symbol = global_char_at_position[pos_dest]
                    cible_django_state = django_states_by_pos.get(pos_dest)
                    if not cible_django_state:
                        print(f"AVERTISSEMENT: État cible (pos {pos_dest}) non trouvé pour une transition.")
                        continue
                        
                    Transition.objects.create(
                        automate=automate,
                        source=source_django_state,
                        symbole=symbol,
                        cible=cible_django_state
                    )

        return automate

    except ValueError as e:
        print(f"Erreur de syntaxe de l'expression régulière: {e}")
        raise # Relaunch the error so the view can catch it
    except Exception as e:
        print(f"Une erreur inattendue est survenue: {e}")
        import traceback
        traceback.print_exc()
        raise

