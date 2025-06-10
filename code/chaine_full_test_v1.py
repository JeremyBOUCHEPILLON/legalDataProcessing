from collections import defaultdict
from collections import deque
from queue import Queue
from string import Template
from enum import Enum
from SPARQLWrapper import SPARQLWrapper, JSON, POST
from git import Repo
import sys
import os
import pathlib
import pygit2



#Define the type of a query bloc
#class BlocType(Enum):
#    NORMAL = 1
#    NEGATION = 2
#    UNION = 3
#    UNIVERSAL = 4


#Define the content of a normal bloc (no negation, no UNION, no universal quantifier)
#It is the building brick of our parsing structure
#Type list[string]
class NORMAL_Bloc:
    def __init__(self):
        self.content = []

    def __str__(self):
        string = """NORMAL_Bloc ["""
        for index, elem in enumerate(self.content):
            if index == 0:
                string = string + str(elem)
            else:
                string = string + ', ' + str(elem)

        string = string + ']'
        return string
    
    def print_as_request(self):
        string = """"""
        for index, elem in enumerate(self.content):
            if index == 0:
                string = string + str(elem)
            else:
                string = string + '\n' + str(elem)

        return string

    def get_content(self):
        return self.content

    def set_content(self, content):
        self.content = content

    def add_element(self, new_element):
        self.content.append(new_element)
        


#Define the content of a negation bloc (no other negation inside it)
#Type list[Bloc]
class NEGATION_Bloc:
    def __init__(self):
        self.content = []

    def __str__(self):
        string = """NEGATION_Bloc ["""
        for index, elem in enumerate(self.content):
            if index == 0:
                string = string + str(elem)
            else:
                string = string + ', ' + str(elem)
        string = string + "]"
        return string
    
    def print_as_request(self):
        string = """FILTER NOT EXISTS {"""
        for index, elem in enumerate(self.content):
            if index == 0:
                string = string + elem.print_as_request()
            else:
                string = string + '\n' + elem.print_as_request()
        string = string + "}"
        return string

    def get_content(self):
        return self.content

    def set_content(self, content):
        self.content = content

    def add_bloc(self, new_bloc):
        self.content.append(new_bloc)



#Define the content of a UNION Bloc : 
#Type list[list[Bloc]]
class UNION_Bloc:
    def __init__(self):
        self.content = []

    def __str__(self):
        string = """UNION_Bloc ["""
        for index, bloc in enumerate(self.content):
            if index == 0:
                string = string + '('
            else:
                string = string + ', ' + '('

            for index2, elem in enumerate(bloc):
                if index2 == 0:
                    string = string + str(elem)
                else:
                    string = string + ', ' + str(elem)
                
            string = string + ')'

        string = string + ']'
        return string

    def print_as_request(self):
        string = """"""
        for index, bloc in enumerate(self.content):
            string = string + '\n' + '{'
            for elem in bloc:
                string = string + '\n' + elem.print_as_request()
            string = string + '\n' + '}'
            if index < len(self.content) - 1:
                string = string + '\n' + "UNION"
        return string

    def get_content(self):
        return self.content
    
    def get_bloc(self, index):
        return self.content[index]

    def set_content(self, content):
        self.content = content

    #add a new case in the UNION
    def add_bloc(self, new_bloc):
        self.content.append(new_bloc)

    #add a new bloc (of type NORMAL, or UNIVERSAL, or NEGATION) in one of the cases of the union
    def add_subbloc(self, index, new_subbloc):
        bloc = self.content[index]
        bloc.append(new_subbloc)



#Define the content of a UNIVERSAL Bloc with its two subblocs
#Type: first: list[Bloc]    second: list[Bloc]
class UNIVERSAL_Bloc:
    def __init__(self):
        self.quantified = []
        self.content = []

    def __str__(self):
        string = """UNIVERSAL_Bloc [("""
        for index,elem in enumerate(self.quantified):
            if index == 0:
                string = string + str(elem)
            else:
                string = string + ', ' + str(elem)

        string = string + '), ('

        for index,elem in enumerate(self.content):
            if index == 0:
                string = string + str(elem)
            else:
                string = string + ', ' + str(elem)

        string = string + ')]'
        return string
    
    def print_as_request(self):
        string = """FILTER NOT EXISTS {"""
        for elem in self.quantified:
            string = string + '\n' + elem.print_as_request()
        string = string + '\n' + "FILTER NOT EXISTS {"
        for elem in self.content:
            string = string + '\n' + elem.print_as_request()
        string = string + '\n' + "}}"
        return string

    def get_quantified(self):
        return self.quantified
    
    def get_content(self):
        return self.content

    def set_quantified(self, first):
        self.quantified = first

    def set_content(self, second):
        self.content = second

    def add_bloc_first(self, new_bloc):
        self.quantified.append(new_bloc)

    def add_bloc_second(self, new_bloc):
        self.content.append(new_bloc)




#Get the prefixes of a request given the keyword for the type of request
def parsingPrefix(request, keyword):
    sep = request.split(keyword)
    prefixes = sep[0]
    return prefixes

#Get the body of a SPARQL request
def parsingBody(request):
    sep = request.split("WHERE")
    body = sep[1]
    sep2 = body.split("{", 1)
    body = sep2[1]
    sep3 = body.rsplit("}", 1)
    body = sep3[0]
    return body


#one solution for obtaining the different nested blocs in a request (not used here)
def brackets_contents(string):
    """Generate bracketed contents in string as pairs (level, contents)."""
    stack = []
    for i, c in enumerate(string):
        if c == '{':
            stack.append(i)
        elif c == '}' and stack:
            start = stack.pop()
            yield (len(stack), string[start + 1: i])


#another solution for obtaining the different nested blocs in a request
def push(obj, l, depth):
    while depth:
        l = l[-1]
        depth -= 1

    l.append(obj)

def parse_brackets(s):
    groups = []
    depth = 0

    try:
        for char in s:
            if char == '{':
                push([], groups, depth)
                depth += 1
            elif char == '}':
                depth -= 1
            else:
                push(char, groups, depth)
    except IndexError:
        raise ValueError('Brackets mismatch')

    if depth > 0:
        raise ValueError('Brackets mismatch')
    else:
        return groups


#function to concat characters that follow each other in a list that can contain other nested lists
def concat_result(reslist):
    result = []
    string = ""
    i = 0
    while (i < len(reslist)):
        if (isinstance(reslist[i], list)):
            result.append(string)
            result.append(concat_result(reslist[i]))
            result.extend(concat_result(reslist[i+1 : len(reslist)]))
            return result
        elif (reslist[i] == '\n'):
            string = string #+ reslist[i] (the newline character is not included in the elements)
            result.append(string)
            string = ""
            i += 1
        else:
            string = string + reslist[i]
            i += 1
    if (string != ""):
        result.append(string)
    return result
        

#print(concat_result(['a', 'b', 'c']))
#print(concat_result(['a', 'b', 'c', ['d', 'e'], 'f', 'g', ['h', 'i', ['j'], 'k']]))



#function for a deapsearch in nested lists.
def deepSearch(searchElement, searchList):
    for element in searchList:
        if element == searchElement:
            return True
        elif type(element) == type(list):
            found = deepSearch(searchElement, element)
            if found:
                return found
    return False


def cleanTabs(searchList):
    res = []
    for element in searchList:
        if type(element) == list:
            res.append(cleanTabs(element))
        else:
            string = element.replace("\t", "")
            string = string.replace("    ", "")
            if (string != '' and string != ' '): #empty elements shall not be kept
                res.append(string)
    return res




def parsingBlocs(clean_blocks):

    parsing = []

    i = 0

    while i < len(clean_blocks):
        #elem = clean_blocks[i]
        if type(clean_blocks[i]) == list:
            if "UNION" in clean_blocks[i+1]:
                union = True
                new_bloc = UNION_Bloc()

                union_bloc = parsingBlocs(clean_blocks[i])
                new_bloc.add_bloc(union_bloc)
                i = i+2

                while (union and i < len(clean_blocks)):
                    union_bloc = parsingBlocs(clean_blocks[i])
                    new_bloc.add_bloc(union_bloc)
                    if ((i+1 < len(clean_blocks)) and (type(clean_blocks[i+1]) != list) and ("UNION" in clean_blocks[i+1])):
                        i = i+2
                    else:
                        union = False
                        i = i+1

                parsing.append(new_bloc)

            # Que faire si ce bloc n'est pas dans une union (quelles sont les cas de figure)


        elif "FILTER NOT EXISTS" in clean_blocks[i]:
            universal = False
            filter_content = clean_blocks[i+1]
            j = 0

            while ((not universal) and j < len(filter_content)):
                if ((type(filter_content[j]) == str) and "FILTER NOT EXISTS" in filter_content[j]):
                    universal = True
                else:
                    j = j+1

            if (universal):
                first_part = []
                j = 0
                second_filter = False
                while ((not second_filter) and j < len(filter_content)):
                    if ((type(filter_content[j]) == str) and "FILTER NOT EXISTS" in filter_content[j]):
                        second_filter = True
                    else:
                        first_part.append(filter_content[j])
                        j = j+1
                
                new_bloc = UNIVERSAL_Bloc()
                first_part_blocs = parsingBlocs(first_part)
                new_bloc.set_quantified(first_part_blocs)

                second_part_blocs = parsingBlocs(filter_content[j+1])
                new_bloc.set_content(second_part_blocs)

                parsing.append(new_bloc)

                i = i+2


            else:
                new_bloc = NEGATION_Bloc()
                bloc_content = parsingBlocs(filter_content)
                new_bloc.set_content(bloc_content)
                parsing.append(new_bloc)
                i = i+2

        else:
            new_bloc = NORMAL_Bloc()
            while ((i < len(clean_blocks)) and (type(clean_blocks[i]) != list) and ("FILTER NOT EXISTS" not in clean_blocks[i])):
                new_bloc.add_element(clean_blocks[i])
                i += 1
            
            parsing.append(new_bloc)


    return parsing




#list of blocs composing a SPARQL request : list[Bloc]
parsing = []



#situation=":storage_change_04"

queryString_PJ10 = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX nrv: <http://ns.inria.fr/nrv#>
PREFIX lrml: <http://docs.oasis-open.org/legalruleml/ns/v1.0#>
PREFIX lrmlmm: <http://docs.oasis-open.org/legalruleml/ns/mm/v1.0#>
PREFIX :  <http://www.semanticweb.org/jbouchep/ontologies/2023/10/legal_data_sharing#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?action
WHERE {
    ?action a :Processing .
    ?action :involvesData ?dataset .
    ?action :isNecessary "true"^^xsd:boolean .
    { 
        ?action :isAuthorizedLaw "true"^^xsd:boolean .
    }
    UNION
    { 
        ?action :protectsVitalInterests "true"^^xsd:boolean .
    }
    UNION
    { FILTER NOT EXISTS {
        ?dataset :containsData ?data .
        ?data a :SensitivePersonalData .
        FILTER NOT EXISTS {
            ?data a :PublicData .
        }
    }}
}
"""


PJ10_full_temp = Template("""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX nrv: <http://ns.inria.fr/nrv#>
PREFIX lrml: <http://docs.oasis-open.org/legalruleml/ns/v1.0#>
PREFIX lrmlmm: <http://docs.oasis-open.org/legalruleml/ns/mm/v1.0#>
PREFIX :  <http://www.semanticweb.org/jbouchep/ontologies/2023/10/legal_data_sharing#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

ASK
{
	$action a :Processing .
	$action :involvesData ?dataset .
    $action :isNecessary "true"^^xsd:boolean .
    { $action :isAuthorizedLaw "true"^^xsd:boolean .}
    UNION
    { $action :protectsVitalInterests "true"^^xsd:boolean .}
    UNION
    { FILTER NOT EXISTS {
        ?dataset :containsData ?data .
        ?data a :SensitivePersonalData .
        FILTER NOT EXISTS {
            ?data a :PublicData .
        }
    }}
}
""")

#PJ10_full = PJ10_full_temp.substitute({'action' : situation})

# Manual construction of the parsing to verify if it applies correctly
first_bloc = NORMAL_Bloc()
first_bloc.add_element('?action a :Processing .')
first_bloc.add_element('?action :involvesData ?dataset .')
first_bloc.add_element('?action :isNecessary "true"^^xsd:boolean .')


second_bloc = UNION_Bloc()

union_bloc1 = []
intern_bloc1_1 = NORMAL_Bloc()
intern_bloc1_1.add_element('?action :isAuthorizedLaw "true"^^xsd:boolean .')
union_bloc1.append(intern_bloc1_1)
second_bloc.add_bloc(union_bloc1)

union_bloc2 = []
intern_bloc2_1 = NORMAL_Bloc()
intern_bloc2_1.add_element('?action :protectsVitalInterests "true"^^xsd:boolean .')
union_bloc2.append(intern_bloc2_1)
second_bloc.add_bloc(union_bloc2)

union_bloc3 = []
intern_bloc3_1 = UNIVERSAL_Bloc()
universal_intern1 = NORMAL_Bloc()
universal_intern1.add_element('?dataset :containsData ?data .')
universal_intern1.add_element('?data a :SensitivePersonalData .')
intern_bloc3_1.add_bloc_first(universal_intern1)

universal_intern2 = NORMAL_Bloc()
universal_intern2.add_element('?data a :PublicData .')
intern_bloc3_1.add_bloc_second(universal_intern2)
union_bloc3.append(intern_bloc3_1)
second_bloc.add_bloc(union_bloc3)


expected_parsing = []
expected_parsing.append(first_bloc)
expected_parsing.append(second_bloc)


expected_string = """"""
for elem in expected_parsing:
    expected_string = expected_string + '\n' + str(elem)


#print("first Bloc : " + str(first_bloc))
#print("second Bloc : " + str(second_bloc))
#print("expected parsing : " + expected_string + '\n')


prefixes = parsingPrefix(queryString_PJ10, "SELECT")
#print("Prefixes :" + '\n' + prefixes)

body = parsingBody(queryString_PJ10)
#print("Body :" + '\n' + body)


res = parse_brackets(body)
res_concat = concat_result(res)
res_clean = cleanTabs(res_concat)
#print(res_clean)


result_parsing = parsingBlocs(res_clean)

result_string = """["""
for index,elem in enumerate(result_parsing):
    if index == 0:
        result_string = result_string + str(elem)
    else:
        result_string = result_string + ', ' + str(elem)

#print("result parsing : " + '\n' + result_string + ']' + '\n')


result_request = """"""
for elem in result_parsing:
    result_request = result_request + '\n' + elem.print_as_request()

#print("result as request : " + result_request + '\n')




#After the preparatory parsing, we need to build the tree / automata 

#The tree structure is a binary DAG
class Node:
    def __init__(self, key, content):
        self.name = key
        self.data = content

        self.union_start = False
        self.union_end = False

        self.left = None
        self.right = None

    def __str__(self):
        string = self.name
        return string

    def get_name(self):
        return self.name
    
    def get_content(self):
        return self.data
    
    def get_union_start(self):
        return self.union_start
    
    def get_union_end(self):
        return self.union_end

    def get_left(self):
        return self.left
    
    def get_right(self):
        return self.right
    
    
    def set_name(self, new_name):
        self.name = new_name

    def set_content(self, content):
        self.data = content

    def set_union_start(self, value):
        self.union_start = value

    def set_union_end(self, value):
        self.union_end = value

    def set_left(self, node):
        self.left = node
    
    def set_right(self, node):
        self.right = node





#Method to generate a binary tree from a list of elements
def from_list(elements):
    root_node = Node(elements[0], elements[0])
    nodes = [root_node]
    for i, x in enumerate(elements[1:]):
        if x is None:
            continue
        parent_node = nodes[i // 2]
        is_left = (i % 2 == 0)
        node = Node(x, x)
        if is_left:
            parent_node.left = node
        else:
            parent_node.right = node
        nodes.append(node)

    return root_node




# Iterative Method to print the height of a binary tree
def printLevelOrder(root):
    # Base Case
    if root is None:
        return
    # Create an empty queue
    # for level order traversal
    queue = []
    # Enqueue Root and initialize height
    queue.append(root)
    while(len(queue) > 0):
        # Print front of queue and
        # remove it from queue
        print(queue[0].name, end=", ")
        node = queue.pop(0)
        # Enqueue left child
        if node.left is not None:
            queue.append(node.left)
        # Enqueue right child
        if node.right is not None:
            queue.append(node.right)




#Iterative Method to list the nodes of a binary tree in pre-order
def preorder_traversal(root):
    res = []
    if not root:
        return res
 
    stack = [root]
    while stack:
        node = stack.pop()
        res.append(node)
        if node.right:
            stack.append(node.get_right())
        if node.left:
            stack.append(node.left())
    return res



#Iterative Method to list the nodes of a binary tree in post-order
def postorder_traversal(root):
    res = []
    if not root:
        return res

    node = root
    stack = []
    right_stack = []
    while stack or node:
        if node:
            if node.right:
                right_stack.append(node.get_right())
            stack.append(node)
            node = node.get_left()
        else:
            node = stack[-1]
            if right_stack and node.right == right_stack[-1]:
                node = right_stack.pop()
            else:
                res.append(node)
                stack.pop()
                node = None
        
    return res



#Iterative Method to print the nodes of a binary tree in level-order
def level_order(root):
    if not root:
        return []

    q = deque([(root, 0)])
    level_map = {}
    
    while q:
        node, level = q.popleft()
        if level not in level_map:
            level_map[level] = [node]
        else:
            level_map[level].append(node)
        if node.left:
            q.append((node.get_left(), level+1))
        if node.right:
            q.append((node.get_right(), level+1))
    n = max(level_map)
    return [level_map[level] for level in range(n+1)]




# An iterative process to search an
# element (based on its name) in a given binary tree 
def iterative_search(tree, name):
     
    # Base Case 
    if (tree == None):
        return None
 
    # Create an empty queue for level
    # order traversal 
    q = Queue() 
 
    # Enqueue Root and initialize height 
    q.put(tree) 
 
    # Queue based level order traversal 
    while (q.empty() == False):
         
        # See if current node is same as x 
        node = q.queue[0] 
        if (node.get_name() == name): 
            return node
 
        # Remove current node and 
        # enqueue its children 
        q.get()
        if node.left:
            q.put(node.get_left()) 
        if node.right:
            q.put(node.get_right())
 
    return None





#Method to print a binary tree (not the best suited since we have a binary DAG)
def print_recursive(tree, level=0, prefix="root"):
    print(f"{level * '  '}{prefix:5s}: name={tree.name} ; u_start={tree.union_start} ; u_end={tree.union_end}")
    if tree.left:
        print_recursive(tree.get_left(), level + 1, "left")
    if tree.right:
        print_recursive(tree.get_right(), level + 1, "right")




#Method to connect subtrees between them.
#Find nodes in tree that have a "OK" node as "left"
def replace_node_ok(tree, node):
    list_node = postorder_traversal(tree)
    for elem in list_node:
        if elem.left:
            if elem.get_left().get_name() == "OK":
                elem.set_left(node)


#Method to connect subtrees between them.
#Find nodes in tree that have a "NOT OK" node as "right"
def replace_node_not_ok(tree, node):
    list_node = postorder_traversal(tree)
    for elem in list_node:
        if elem.right:
            if elem.get_right().get_name() == "NOT OK":
                elem.set_right(node)



def set_union_end(tree):
    list_node = level_order(tree)
    for list in list_node:
        for elem in list:
            if elem.left:
                if (elem.get_left().get_name() == "OK") :
                    elem.set_union_end(True)


def add_end_of_last(tree, suffix):
    list_node = level_order(tree)
    for list in list_node:
        for elem in list:
            if elem.left:
                if (elem.get_left().get_name() == "OK") :
                    elem.set_content(elem.get_content() + suffix)






# Generating the tree from the parsing
def generateTree(parsing):

    i = 0
    root = None
    bloc_root = None
    previous_bloc = None

    while (i < len(parsing)):

        if  isinstance(parsing[i], NORMAL_Bloc):
            content = parsing[i].get_content()
            
            j = 0
            node1 = Node(content[j], content[j])
            bloc_root = node1
            
            if i == 0:
                root = node1
            
            out1 = Node("NOT OK", "Missing " + content[j])
            node1.set_right(out1)

            j = j+1

            while (j < len(content)):
                node2 = Node(content[j], content[j])
                out2 = Node("NOT OK", "Missing " + content[j])
                node2.set_right(out2)

                node1.set_left(node2)

                node1 = node2
                j = j+1
            
            last_out = Node("OK", "OK")
            node1.set_left(last_out)
            



        elif isinstance(parsing[i], UNION_Bloc):
            case_list = parsing[i].get_content()

            previous_case = None

            for index, case in enumerate(case_list):
                case_tree = generateTree(case)
                case_tree.set_union_start(True)
                set_union_end(case_tree)
                
                if index == 0:
                    bloc_root = case_tree
                    previous_case = case_tree
                    if i == 0:
                        root = case_tree
                else:
                    replace_node_not_ok(previous_case, case_tree)
                    previous_case = case_tree



        elif isinstance(parsing[i], NEGATION_Bloc):
            content = parsing[i].get_content()

            prefix = "FILTER NOT EXISTS {" + '\n'
            bloc_tree = generateTree(content)
            bloc_tree.set_content(prefix + bloc_tree.get_content())
            add_end_of_last(bloc_tree, "}")

            bloc_root = bloc_tree


            if i == 0:
                root = bloc_tree
            
        

        elif isinstance(parsing[i], UNIVERSAL_Bloc):
            quantified = parsing[i].get_quantified()

            quantified_str = "FILTER NOT EXISTS {" + '\n'
            for elem in quantified:
                quantified_str = quantified_str + str(elem) + '\n'

            quantified_str = quantified_str + "FILTER NOT EXISTS {" + '\n'


            content = parsing[i].get_content()
            bloc_tree = generateTree(content)

            bloc_tree.set_content(quantified_str + bloc_tree.get_content())

            add_end_of_last(bloc_tree, "}}")


            bloc_root = bloc_tree

            if i == 0:
                root = bloc_tree



        if i == 0:
            previous_bloc = bloc_root
        else:
            replace_node_ok(previous_bloc, bloc_root)
            previous_bloc = bloc_root

        i = i+1

    return root





tree_test = generateTree(result_parsing)
#print_recursive(tree_test)



query_test = """
PREFIX :  <http://www.semanticweb.org/jbouchep/ontologies/2023/10/legal_data_sharing#>


SELECT DISTINCT ?a
WHERE {
    ?a .
    ?b .
    { 
        ?c .
    }
    UNION
    {
        ?d . 
        FILTER NOT EXISTS { ?e . }
    }
    UNION
    { FILTER NOT EXISTS {
        ?f .
        ?g .
        FILTER NOT EXISTS {
            ?h .
            ?i .
        }
    }}

    ?j .
    ?k .
}
"""



prefixes = parsingPrefix(query_test, "SELECT")
#print("Prefixes :" + '\n' + prefixes)

body = parsingBody(query_test)
#print("Body :" + '\n' + body)


res = parse_brackets(body)
res_concat = concat_result(res)
res_clean = cleanTabs(res_concat)
#print(res_clean)


result_parsing = parsingBlocs(res_clean)

result_string = """["""
for index,elem in enumerate(result_parsing):
    if index == 0:
        result_string = result_string + str(elem)
    else:
        result_string = result_string + ', ' + str(elem)

result_string = result_string + ']'

#print("result parsing : " + '\n' + result_string + '\n')


result_request = """"""
for elem in result_parsing:
    result_request = result_request + '\n' + elem.print_as_request()

#print("result as request : " + result_request + '\n')


tree = generateTree(result_parsing)
#print_recursive(tree, 0)




#function te execute a sparql query in an endpoint
def ask_query_execution(query, sparql_endpoint):
    sparql_endpoint.setQuery(query)
    sparql_endpoint.setReturnFormat(JSON)
    results = sparql_endpoint.query().convert()
    result_bool = results["boolean"]

    return result_bool




#function for traveling a tree generated from a SPARQL query
def tree_traversal(request, tree, sparql_endpoint, situation_name):
    if tree is None:
        return
    
    prefix = parsingPrefix(request, "SELECT")

    perm_query = prefix + '\n' + "ASK {" + '\n'

    curr_query = perm_query

    node = tree

    unrespected = []

    temp = ""

    while ((node.left is not None) and (node.right is not None)) :


        #Gestion des unions
        #Il faut garder le contenu des sous-blocs UNION en tant que contenu temporaire des requêtes
        if (node.get_union_start()):
            temp = ""
            temp_query = curr_query

            #Tant que ce n'est pas le dernier element d'un sous-bloc UNION
            while (not node.get_union_end()):
                temp = temp + node.get_content() + '\n'
                temp_query = curr_query + temp + '\n'
                exec_query = temp_query.replace("?action", situation_name)
                result_bool = ask_query_execution(temp_query + '}', sparql_endpoint)

                if (result_bool) :
                    node = node.left
                else :
                    unrespected.append(node.get_name)
                    node = node.right

            #Il s'agit cette fois du dernier element d'un sous-bloc UNION
            temp = temp + node.get_content() + '\n'
            temp_query = curr_query + temp + '\n'
            exec_query = temp_query.replace("?action", situation_name)
            result_bool = ask_query_execution(exec_query + '}', sparql_endpoint)

            if (result_bool) :
                node = node.left
            else :
                unrespected.append(node.get_name)
                node = node.right
            
            #le noeud qui suit le sous-bloc union n'est pas le début d'un autre sous-bloc union
            # ATTENTION, peut poser problème si la requête comporte 2 Gros blocs UNION à la suite
            #Envisager de rajouter une variable ALL_UNION_END dans les noeuds
            if (not node.get_union_start()):
                curr_query = temp_query
                


        #On ne se trouve pas face à une UNION, c'est le traitement classique
        else:
            curr_query = curr_query + node.get_content() + '\n'
            exec_query = curr_query.replace("?action", situation_name)
            result_bool = result_bool = ask_query_execution(exec_query + '}', sparql_endpoint)

            if (result_bool) :
                node = node.left
            else :
                unrespected.append(node.get_name)
                node = node.right

    return node.get_content()

        


#sparql = SPARQLWrapper("http://localhost:3030/ds/query")
#tree_traversal(queryString_PJ10, tree, sparql, "name")



# design of the full chain


def walk_repo_files(repo_path, branch="main"):
    repo = pygit2.Repository(repo_path)
    tree = repo.revparse_single(branch).tree
    trees_and_paths = [(tree, [])]
    # keep going until there is no more data
    while len(trees_and_paths) != 0:
        tree, path = trees_and_paths.pop() # take the last entry
        for entry in tree:
            if entry.filemode == pygit2.GIT_FILEMODE_TREE:
                next_tree = repo.get(entry.id)
                next_path = list(path)
                next_path.append(entry.name)
                trees_and_paths.append((next_tree, next_path,))
            else:
                yield os.path.join(*path, entry.name)



def read_files_from_git(repo_path, branch="main", file_paths=[]):
    #Open the repo
    repo = Repo(repo_path)

    #Get the commit at the head of the specified branch
    commit = repo.commit(branch)

    file_contents = {}
    for file_path in file_paths:
        try:
            #Read the content of the file at the specified path in the repo
            file_content = commit.tree[file_path].data_stream.read().decode('utf-8')
            file_contents[file_path] = file_content
        except KeyError:
            print(f"File '{file_path}' not found in branch '{branch}'")

    return file_contents

#ex of usage
repo_path = 'https://github.com/JeremyBOUCHEPILLON/legalDataProcessing.git'
branch = 'main'
file_paths = ['rules...']


#files_content = read_files_from_git(repo_path, branch, file_paths)

#for file_path, content in files_content.items():
#    print(f"Content of '{file_path}':\n{content}")


#get the content of a specific rule
#grap_htype = global or named
#rule_type = applicable or explicit or implicit or exception
def get_rule_content(graph_type, rule_type, name):
    path = "resources/rules/"
    if graph_type == "global":
        path +=  "global graph rules"
    elif graph_type == "named":
        path += "named graph rules"
    else:
        raise Exception("Wrong value for the graph_type argument: has to be either 'global' or 'named'")
    
    path += "/"
    
    match rule_type:
        case "applicable":
            path += "applicable rules"
        case "explicit":
            path += "explicit compliance rules"
        case "implicit":
            path += "implicit compliance rules"
        case "exception":
            path += "exception rules"
        case _:
            raise Exception("Wrong value for the rule_type argument: has to be either 'applicable', 'explicit', 'implicit' or 'exception'")

    path += "/" + name

    file = open(path, "r")
    content = file.read()
    file.close()

    return content


#get a list of all the paths of the rules of a certain type for a type of graph
#grap_htype = global or named
#rule_type = applicable or explicit or implicit or exception
def get_rules(graph_type, rule_type):
    path = "resources/rules/"
    if graph_type == "global":
        path +=  "global graph rules"
    elif graph_type == "named":
        path += "named graph rules"
    else:
        raise Exception("Wrong value for the graph_type argument: has to be either 'global' or 'named'")
    
    path += "/"
    
    match rule_type:
        case "applicable":
            path += "applicable rules"
        case "explicit":
            path += "explicit compliance rules"
        case "implicit":
            path += "implicit compliance rules"
        case "exception":
            path += "exception rules"
        case _:
            raise Exception("Wrong value for the rule_type argument: has to be either 'applicable', 'explicit', 'implicit' or 'exception'")


    directory = pathlib.Path(path)
    list_paths = list(directory.iterdir())

    list_str_paths = [str(elem) for elem in list_paths]

    return list_str_paths



def check_update_rules(situation_id, rule_path_list, sparql_endpoint):

    for path in rule_path_list:

        file = open(path, "r")
        content = file.read()
        file.close()

        #The query is adapted to check only for the situation specified in input
        adapted_content = content.replace("?situation", ":" + situation_id)

        sparql_endpoint.setMethod(POST)
        sparql_endpoint.setQuery(adapted_content)
        results = sparql_endpoint.query()
        #print(results.response.read())



def get_applicability(situation_id, sparql_endpoint):
    request = """
    PREFIX nrv: <http://ns.inria.fr/nrv#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX lrml: <http://docs.oasis-open.org/legalruleml/ns/v1.0#>
    PREFIX lrmlmm: <http://docs.oasis-open.org/legalruleml/ns/mm/v1.0#>
    PREFIX :  <http://www.semanticweb.org/jbouchep/ontologies/2023/10/legal_data_sharing#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT DISTINCT ?rule
    WHERE {
        ?rule :isApplicable ?situation .
    }
    """

    request_adapted = request.replace("?situation", ":" + situation_id)

    output = []
    sparql_endpoint.setQuery(request_adapted)
    sparql_endpoint.setReturnFormat(JSON)
    results = sparql_endpoint.query().convert()
    for result in results["results"]["bindings"]:
        output.append(result["rule"]["value"])
    
    return output


def get_compliance(situation_id, sparql_endpoint):
    request = """
    PREFIX nrv: <http://ns.inria.fr/nrv#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX lrml: <http://docs.oasis-open.org/legalruleml/ns/v1.0#>
    PREFIX lrmlmm: <http://docs.oasis-open.org/legalruleml/ns/mm/v1.0#>
    PREFIX :  <http://www.semanticweb.org/jbouchep/ontologies/2023/10/legal_data_sharing#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT DISTINCT ?rule ?type
    WHERE {
        ?rule a :ComplianceStatement .
        ?rule nrv:hasCompliance ?situation .
        ?rule a ?type .
    }
    """

    request_adapted = request.replace("?situation", ":" + situation_id)

    #list of the results in the form list[(rule, type)]
    output = []
    sparql_endpoint.setQuery(request_adapted)
    sparql_endpoint.setReturnFormat(JSON)
    results = sparql_endpoint.query().convert()
    for result in results["results"]["bindings"]:
        output.append((result["rule"]["value"], result["type"]["value"]))
    
    return output



    
def clean_compliant_list(ruleandtype):
    if ("Permission" in ruleandtype[1]) or ("Prohibition" in ruleandtype[1]) or ("Obligation" in ruleandtype[1]) or ("Facultative" in ruleandtype[1]):
        return True
    else:
        return False
    

#Function to return whether or not the rules are consistent and the global deontic answer in case they are
def test_consistency(rule_list):
    type_list = []
    for elem in rule_list:
        if (elem[1] not in type_list):
            type_list.append(elem[1])


    #Classification established thanks to a Karnaugh table over deontic modalities
    if any("Obligation" in elem for elem in type_list) and (not any("Facultative" in elem for elem in type_list)) and (not any("Prohibition" in elem for elem in type_list)):
        consistent = True
        compliance_type = "Obligation"
    
    elif any("Prohibition" in elem for elem in type_list) and (not any("Permission" in elem for elem in type_list)) and (not any("Obligation" in elem for elem in type_list)):
        consistent = True
        compliance_type = "Prohibition"

    elif any("Permission" in elem for elem in type_list) and (not any("Obligation" in elem for elem in type_list)) and (not any("Prohibition" in elem for elem in type_list)):
        consistent = True
        compliance_type = "Permission"
    
    elif any("Facultative" in elem for elem in type_list) and (not any("Obligation" in elem for elem in type_list)) and (not any("Prohibition" in elem for elem in type_list)):
        consistent = True
        compliance_type = "Facultative"

    else:
        consistent = False

    if consistent:
        return consistent, compliance_type
    else:
        return consistent, None



def all_trees(list_applicable, graph_type):
    trees = []

    path = "resources/rules/"
    if graph_type == "global":
        path +=  "global graph rules"
    elif graph_type == "named":
        path += "named graph rules"
    else:
        raise Exception("Wrong value for the graph_type argument: has to be either 'global' or 'named'")
    
    path += "/applicable rules"

    for rule in list_applicable:
        path_rule = path + "/" + rule

        file = open(path_rule, "r")
        content = file.read()
        file.close()

        #!!! ATTENTION. Il faut aussi prendre en compte la strucutre quand on a les graphes nommés
        body = parsingBody(content)

        res = parse_brackets(body)
        res_concat = concat_result(res)
        res_clean = cleanTabs(res_concat)
        result_parsing = parsingBlocs(res_clean)

        tree = generateTree(result_parsing)

        trees.append((rule, tree))

    return trees


        

#graph_type = global or named
def full_pipeline(situation_id, graph_type, sparql_update, sparql_query):
    
    #selection of the rules to check
    applicable_rules = get_rules(graph_type, "applicable")
    explicit_rules = get_rules(graph_type, "explicit")
    implicit_rules = get_rules(graph_type, "implicit")
    compliance_rules = explicit_rules + implicit_rules
    exception_rules = get_rules(graph_type, "exception")

    applicable_rule_names = []
    for path in applicable_rules:
        directory, filename = path.rsplit("/", maxsplit=1)
        applicable_rule_names.append(filename)

    compliance_rule_names = []
    for path in compliance_rules:
        directory, filename = path.rsplit("/", maxsplit=1)
        compliance_rule_names.append(filename)

    exception_rule_names = []
    for path in exception_rules:
        directory, filename = path.rsplit("/", maxsplit=1)
        exception_rule_names.append(filename)

    #first part of checking: checking applicability and compliance
    check_update_rules(situation_id, applicable_rules, sparql_update)
    check_update_rules(situation_id, compliance_rules, sparql_update)
    #second part of checking: applying the exception rules
    check_update_rules(situation_id, exception_rules, sparql_update)

    #get the list of rules respectively applicable and compliant with the situation in input
    #list of applicable rules (their names)
    applicable = get_applicability(situation_id, sparql_query)

    #list of compliant rules (names and types)
    compliant = get_compliance(situation_id, sparql_query)

    #If there are applicable rules
    if (len(applicable) > 0):
    
        #There can be compliance only if there is applicability
        if (len(compliant) > 0):
            clean_compliant = filter(clean_compliant_list, compliant)

            consistent, compliance_type = test_consistency(clean_compliant)
            
            #Case where all the compliant rules are consistent
            if consistent:
                output = "According to the rules checked, the situation is in a case of " + compliance_type

                return output

            #Case where the rules are not consistent
            else:
                output = """
                Several rules have been found to apply in this situation but are inconsistent:
                """
                for elem in clean_compliant:
                    output += elem[0] + '\n'

                return output


        #The case where there are no compliance: the most complex case, we initiate the reasoning process with the trees
        else:
            trees = all_trees(applicable, graph_type)
            list_out = []

            for elem in trees:
                #Les arguments sont-ils bons ?
                result = tree_traversal(elem[0], elem[1], sparql_query, situation_id)
                list_out.append(result)

                #Besoin de classer les arbres selon la profondeur atteinte !!


            output = """
            Despite applicable rules, no compliance has been found:
            The different options of missing elements are the following:
            """

            for elem in list_out:
                output = output + '\n' + elem + '\n'

            return output


    #The case where there are no applicalbe rules
    else:
        return "The rules from the selected regulations are not applicalbe to the situation"

    




def test_chaine():
    sparql_query = SPARQLWrapper("http://localhost:3030/ds/query")
    sparql_update = SPARQLWrapper("http://localhost:3030/ds/update")

    
    list_situation = [ "Situation01", "Situation02", "Situation02bis", "Situation02ter", "Situation03", "Situation04", "Situation05", "Situation06", "Situation07", "Situation08", "Situation09", "Situation10", "Situation11", "Situation12", "Situation13"]

    for situation in list_situation:
        print(situation + " : ")
        print(full_pipeline(situation, "global", sparql_update, sparql_query))
        print('\n')




test_chaine()