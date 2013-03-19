import os, sys
import glob
import urllib2, urllib
import yaml, json
import re

class Biblio:

    config_dir = 'config/search/'

    def __init__(self):
        self.load_sources()


    def load_sources(self):
        self.sources = {}
        source_list = glob.glob(Biblio.config_dir + '*.yaml')
        for source in source_list:
            try:
                f = open(source, 'r')
                y = yaml.load(f)
                self.sources[y['root']] = y
            except Exception as e:
                raise Exception(str(e))

    
    def get_source(self, source):
        if source is not None and source in self.sources:
            return self.sources[source]
        else:
            for s, specs in self.sources.items():
                if specs['default']:
                    return self.sources[s]


    def search(self, query, source=None, api='default'):
        search_source = self.get_source(source)
        input_type = search_source['api'][api]['input']['type']        
        if input_type == 'json':
            query_string = self.format_as_json(query, search_source, api)
        elif input_type == 'key_value':
            query_string = self.format_as_key_value(query, search_source, api)
        elif input_type == 'lazy':
            query_string = self.format_lazy(query, search_source, api)
        print query_string
        #return
        request = urllib2.urlopen(query_string)
        results = request.read()
        #return json.loads(results)
        return results


    def format_lazy(self, query, source, api):
        elements = query.split(':')
        param_bind_char, param_chain_char = source['api'][api]['input']['param_bind_chain']
        option_bind_char, option_chain_char = source['api'][api]['input']['option_bind_chain']
        if len(elements) == 1:
            return source['url'] + source['api'][api]['path'] + param_bind_char + urllib2.quote(query)
        else:
            query_string = ''
            for num in range(0, len(elements), 2):
                query_string += str(elements[num]) + str(option_bind_char) + urllib2.quote(elements[num+1])
                if num != len(elements) - 2:
                    query_string += str(option_chain_char)
        return source['url'] + source['api'][api]['path'] + query_string


    def format_as_key_value(self, query, source, api):
        elements = query.split(':')
        if len(elements)%2!=0:
            raise Exception('Invalid query: Not enough arguments.')
        param_bind_char, param_chain_char = source['api'][api]['input']['param_bind_chain']
        option_bind_char, option_chain_char = source['api'][api]['input']['option_bind_chain']
        query_string = ''
        for num in range(0, len(elements), 2):
            key = elements[num]
            if key in source['api'][api]['input']['params']:
                query_string += str(key) + str(param_bind_char) + str(elements[num+1]) + str(param_chain_char)
            elif key in source['api'][api]['input']['options']:
                query_string += str(option_chain_char) + str(key) + str(option_bind_char) + str(elements[num+1])
            else:
                raise Exception('Invalid query: \''+str(key)+'\' unknown parameter.')
        return source['url'] + source['api'][api]['path'] + query_string
                                                                    

    def format_as_json(self, query, source, api):
        elements = query.split(':')
        qtype = elements[0]
        if qtype not in source['api'][api]['input']['params']:
            raise Exception('Invalid query: \''+str(qtype)+'\' unknown parameter.')
        elements = elements[1:]
        if len(elements)%2!=0:
            raise Exception('Invalid query: Not enough arguments.')
        qproperties = []
        qstrings = []
        property_items = []
        for num in range(0, len(elements), 2):
            property_items.append(self.assign_property(elements[num], elements[num+1], 
                                                       source['api'][api]['input']['params'][qtype]))            
        query_string = "{\"type\":\"\/type\/" + qtype + "\""
        for item in property_items:
            if type(item) == tuple:
                query_string += ",\""+item[0]+"\":\""+item[1]+"\""
            elif type(item) == dict:
                query_string += ',' + re.sub('(^\{|\}$)', '', str(item).replace("'", "\""))
        query_string = str(source['url']) + str(source['api'][api]['path']) + urllib2.quote(query_string + '}')
        return query_string


    def assign_property(self, qproperty, qstring, types):
        for p in types:
            if p == str(qproperty):
                return (qproperty, qstring)
            elif qproperty in p:
                item = p
                for entry, chain in item[qproperty].items():
                    chain['key'] = '/' + qproperty + '/' + qstring
                return item
        raise Exception('Invalid query: \''+qproperty+'\' unknown property')


    def get_bib_data(self, query):
        pass

        

