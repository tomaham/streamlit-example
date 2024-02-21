import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from SPARQLWrapper import SPARQLWrapper, JSON
from nltk.corpus import wordnet as wn
import os
import platform
import re
import sys

nltk.download('wordnet')

"""
# Welcome to Streamlit!

Edit `/streamlit_app.py` to customize this app to your heart's desire :heart:.
If you have any questions, checkout our [documentation](https://docs.streamlit.io) and [community
forums](https://discuss.streamlit.io).

In the meantime, below is an example of what you can do with just a few lines of code:
"""



def get_synset_from_id(synset_id):
    offset = int(synset_id[:8])
    pos_tag = synset_id[-1]
    pos_mapping = {'n': 'n', 'v': 'v', 'a': 'a', 'r': 'r'}
    nltk_pos_tag = pos_mapping.get(pos_tag)
    if nltk_pos_tag:
        return wn.synset_from_pos_and_offset(nltk_pos_tag, offset)
    else:
        return None


    

lemma_input = st.text_input("Enter a lemma:")

if lemma_input:
	sparql = SPARQLWrapper("https://lila-erc.eu/sparql/lila_knowledge_base/sparql")
	sparql.setReturnFormat(JSON)

	sparql.setQuery(f"""
PREFIX lila: <http://lila-erc.eu/ontologies/lila/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX powla: <http://purl.org/powla/powla.owl#>
PREFIX lemma: <http://lila-erc.eu/data/id/lemma#>
PREFIX premon: <http://premon.fbk.eu/ontology/core#>
PREFIX lv: <http://lila-erc.eu/ontologies/latinVallex/>

SELECT ?senseLabel ?valencyPattern WHERE {{
  {{
    SELECT ?lemma (GROUP_CONCAT(DISTINCT ?wr; separator=", ") AS ?wrs)
    WHERE {{
      ?lemma rdf:type lila:Lemma;
             lila:hasPOS lila:verb;
             ontolex:writtenRep ?wr .
      FILTER (str(?wr) = "{lemma_input}")
    }}
    GROUP BY ?lemma
  }}
  ?sense ontolex:canonicalForm ?lemma .
  ?sense ontolex:sense ?senseLabel .
  ?sense ontolex:evokes ?functor .
  ?functor premon:semRole ?semanticRole .
  ?semanticRole rdfs:label ?functorLabel .
  
  BIND(SUBSTR(?functorLabel, 1, STRLEN(?functorLabel) - STRLEN(STRAFTER(?functorLabel, " "))) AS ?valencyPattern)
  FILTER CONTAINS(str(?functor), "LatinVallex")
}}
GROUP BY ?senseLabel
ORDER BY ?wrs	
	""")

	synset_to_functors = {}
	sense_to_synset = {}
	synset_to_definition = {}
	lemma_id = ""
	sense_ids = []
	try:
		ret = sparql.queryAndConvert()
		for b in ret["results"]["bindings"]:
			sense_id = b['senseLabel']['value']
			lemma_id = re.sub(r'.*l_([0-9]+)_.*', '\\1', sense_id)
			synset_id = re.sub(r'.*l_[0-9]+_(.*)$', '\\1', sense_id)
			offset_id = re.sub(r'.*_(.*?)-.*', '\\1', str(sense_id))
			pos_tag = sense_id.split('/')[-1].split('-')[1]  # Extract the POS tag from the sense ID
			synset = wn.synset_from_pos_and_offset(pos_tag, int(offset_id))

			functor = b['valencyPattern']['value'].strip()
			if synset_id not in synset_to_functors:
				synset_to_functors[synset_id] = functor
			else:
				if functor not in synset_to_functors[synset_id]:
					synset_to_functors[synset_id] = synset_to_functors[synset_id] + " " + functor
			if synset_id not in synset_to_definition:
				synset_to_definition[synset_id] = synset.definition()
	except Exception as e:
		st.write(e)

	#color = "#333333"
	for i, synset_id in enumerate(synset_to_functors):
		synset = get_synset_from_id(synset_id)
		definition = synset_to_definition[synset_id]
		eng_examples = synset.examples()
		if len(eng_examples) > 0:
			eng_examples = '<br>'.join(['&nbsp;&nbsp;&nbsp;' + example for example in eng_examples])
		else:
			eng_examples = "None"
		item = f"Lemma: <b>{lemma_input}</b><br>Definition:<br>&nbsp;&nbsp;&nbsp;<b>{definition}</b><br>English examples:<br><b>{eng_examples}</b><br>LiLa lemma ID:<br><b>{lemma_id}</b><br>WordNet 3.0 Synset ID:<br><b>{synset_id}</b>"
		st.markdown(f'<div style="padding: 10px; margin-bottom: 10px;">{item}</div>', unsafe_allow_html=True)