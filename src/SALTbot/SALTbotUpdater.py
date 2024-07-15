from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator import wbi_login
#from wikiintegrator import wbi_core
from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.datatypes import ExternalID, Item, String, URL, Quantity, Property, CommonsMedia, GlobeCoordinate
from wikibaseintegrator.models import Qualifiers
from wikibaseintegrator.wbi_enums import ActionIfExists
import click
from click_option_group import optgroup, RequiredMutuallyExclusiveOptionGroup
import re
import json
import ast
import SALTbotHandler
import time

def createEmptyEntity(data, dict_item_wb, wbi):
    try:
        print('Creating entity ',data['LABEL'])
   
        item_wb = wbi.item.new()
        item_wb.labels.set(language='en', value=data['LABEL'])
        item_wb.descriptions.set(language='en', value=data['DESCRIPTION'])
        summary='created '+ data['LABEL']
        item_wb = item_wb.write(summary=summary) 
        print('Item created as ', item_wb.id)
        dict_item_wb.update({data['LABEL']:item_wb.id})
        return item_wb, dict_item_wb
    except Exception as e:
        print('Create ',data,' could not be done. Reason: ', e)
        return None, dict_item_wb






def createStatement(data,subject_map, dict_item_wb, wbi):
    #print(data['qualifiers'])
    try:
        regex = r'^(http|https)://([a-zA-Z0-9-]+\.)+([a-zA-Z]{2,})(/[^\s]*)?$'
        if data['s'] in dict_item_wb.keys():
            data['s'] = dict_item_wb[data['s']]
        else:
            item = SALTbotHandler.getCorrectQnode(data['s'], wbi_helpers.search_entities(search_string=data['s'], dict_result = True))
            dict_item_wb.update({data['s']:item})
            data['s'] = item
        
        if data['o'] in dict_item_wb.keys():
            data['o'] = dict_item_wb[data['o']]
            
        #elif re.match(regex, data['o']) == None and re.match('\bQ\d+\b', data['o']) != None:
        #    print('match not regex', data['o'])
        
        print('creating statement [', data['s'], ' ', data['p'],' ' ,data['o'], ']')

        if data['s'] not in subject_map.keys():
            item_wb = wbi.item.get(entity_id=data['s'])
            #print(item_wb)
            subject_map.update({item_wb.id:[item_wb, '']})
            data['s'] = item_wb.id
        if data['datatype'] == 'Item':
            subject_map[data['s']][0].claims.add(Item(value=data['o'], prop_nr=data['p']),action_if_exists = ActionIfExists.APPEND_OR_REPLACE)
            subject_map[data['s']][1] = subject_map[data['s']][1] +' '+ str(data['p']) + ':' + str(data['o']) + ' '
        elif data['datatype'] == 'URL':
            print(data['o'])
            qualifiers = None
            if qualifiers != None:
                for qual in data['qualifiers']:
                    qualifiers.add(Item(prop_nr=qual[1], value=qual[0]))
            subject_map[data['s']][0].claims.add(URL(value=data['o'], prop_nr=data['p'], qualifiers=qualifiers), action_if_exists = ActionIfExists.APPEND_OR_REPLACE)
            subject_map[data['s']][1] = subject_map[data['s']][1] + ' ' +str(data['p']) + ':' +str(data['o']) + ' '
        elif data['datatype'] == 'String':
            subject_map[data['s']][0].claims.add(String(value=data['o'], prop_nr=data['p']), action_if_exists = ActionIfExists.APPEND_OR_REPLACE)
            subject_map[data['s']][1] = subject_map[data['s']][1] + ' ' +str(data['p']) + ':' +str(data['o']) + ' '
            
        subject_map[data['s']][0].write(summary = subject_map[data['s']][1])
        print('succesfully created [', data['s'], ' ', data['p'],' ' ,data['o'], ']')
    except Exception as e:
        print('statement ', data, 'could not be imported. Reason: ', e)

#CHANGED LAST_ITEM FROM LAST_SOFTWARE
def updateChanges(operation_list, wbi):
    last_item = None
    subject_map = {}
    dict_item_wb = {}
    if(operation_list == []):
        print('SALTbot did not detect any relevant statements to add to the graph')
    for operation in operation_list:  
        if operation[0]=='create':
            try:
                last_item, dict_item_wb = createEmptyEntity(operation[1], dict_item_wb, wbi)
            
                subject_map.update({last_item.id:[last_item, '']})
            except:
                continue

            #print("subject_map: ", subject_map) 
           
        elif operation[0] == 'statement':
            createStatement(operation[1],subject_map, dict_item_wb, wbi)
    
def executeOperations(operation_list,auto,wbi):
    
    click.echo(click.style('SALTbot WILL INTRODUCE THESE STATEMENTS IN WIKIDATA', fg='red', bold = True))
    #print(operation_list)
    #operation = json.load(str(operation_list.readlines()))
    #print(operation)
    operation_list_aux = []
    for operation in operation_list:
        #print('operation en bucle', operation)
        operation_aux = ast.literal_eval(operation)
        operation_list_aux.append(operation_aux)
        #print('operation_aux', operation_aux)
        #print('op 1', operation_aux[1])
        #print(operation_aux[1].keys())
        if operation_aux[0] == 'create':
            print('CREATE ENTITY [', operation_aux[1]['LABEL'], '] WITH DESCRIPTION [', operation_aux[1]['DESCRIPTION'],']')
        if operation_aux[0] == 'statement':
            print('CREATE STATEMENT [', operation_aux[1]['s'],' ',operation_aux[1]['p'],' ',operation_aux[1]['o'],'] OF TYPE [', operation_aux[1]['datatype'], '] WITH QUALIFIERS [', operation_aux[1]['qualifiers'],']')
    
    if auto == True:
        updateChanges(operation_list_aux, wbi)
    else:
        confirmation = input("CONFIRM (Y/N): ").strip()
            
        while(confirmation != "Y" and confirmation != "N"):
            confirmation = input("ONLY Y OR N ARE VALID CONFIRMATION ANSWERS. CONFIRM (Y/N): ").strip()	
            
        if(confirmation == "Y"):
            updateChanges(operation_list_aux, wbi)

