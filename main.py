# Pubmed search:
# (((((("musc*"[Title] AND "Diffusion"[Title/Abstract] AND ("MR"[Title/Abstract] OR "MRI"[Title/Abstract] OR "Magnetic"[Title/Abstract])) NOT "mouse"[Title/Abstract]) NOT "mice"[Title/Abstract]) NOT "rat"[Title/Abstract]) AND "hasabstract"[All Fields]) NOT "meta-analysis"[Publication Type]) NOT "review"[Publication Type]

openai.api_key = "INSERT_API_KEY"

import csv
import json
import pickle
import time

import openai

entry_list = []

current_field = ''
current_content = ''
new_field = False
old_field = ''
old_content = ''
current_entry = {}

with open('pubmed-muscTitleA-set.txt', 'r') as f:
    for line in f:
        field = line[:4].strip()
        content = line[6:].strip()
        # beginning of a new field
        if field:
            old_field = current_field
            old_content = current_content
            current_field = field
            current_content = content
            new_field = True
        else:
            current_content += content
            new_field = False

        if new_field and current_field == 'PMID':
            if current_entry:
                entry_list.append(current_entry)
            current_entry = {'PMID': current_content}
        elif new_field:
            if old_field == 'TI':
                current_entry['Title'] = old_content
            elif old_field == 'AB':
                current_entry['Abstract'] = old_content

total_entries = len(entry_list)

prompt = """The following is an abstract of a scientific paper. Please tell me if it is about neuromuscular diseases and if it is a review paper. If it is not a review papers, also add the size of the patient group and the size of the control group, if mentioned in the abstract. Give a response in the following JSON format:
{
"Neuromuscular disease": bool,
"Disease type": str,
"Review paper": bool,
"Patient group size": int,
"Control group size": int
}
Make sure that the boolean values are in lower case and use null if a value is not mentioned in the abstract.
Only reply with the JSON object and nothing else.

Abstract:
"""


try:
    entry_list = pickle.load(open('output_data.pkl', 'rb'))
except FileNotFoundError:
    pass

for i, entry in enumerate(entry_list):
    print(f'Processing entry {i+1} of {total_entries}')
    if 'Neuromuscular disease' in entry:
        print('Entry already processed')
        continue
    retry = True
    while retry:
        try:
            chat = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
              messages=[
                    {"role": "system", "content": "You are an academic researcher that is reading papers for the purpose of writing a review."},
                    {"role": "user", "content": prompt + entry['Abstract']}
                ],
              temperature=0
            )
            retry = False
        except openai.error.RateLimitError:
            print('Rate limit error - retrying in 5s')
            time.sleep(5)

    reply = chat.choices[0].message.content
    try:
        reply_dict = json.loads(reply)
    except json.decoder.JSONDecodeError:
        print('JSON decoding error')
        print(reply)
        continue

    entry.update(reply_dict)
    pickle.dump(entry_list, open('output_data.pkl', 'wb'))

all_labels = [
    'PMID',
    'Title',
    'Abstract',
    'Review paper',
    'Neuromuscular Disease',
    'Disease type',
    'Patient group size',
    'Control group size'
]

lowercase_entry_list = [ {key.lower(): value for key, value in entry_list_dict_item.items()} for entry_list_dict_item in entry_list ]

with open('output_data.csv', 'w') as f:
    # save the entry_list as a csv file
    writer = csv.DictWriter(f, fieldnames=[k.lower() for k in all_labels])
    writer.writeheader()
    for entry in lowercase_entry_list:
        writer.writerow(entry)
