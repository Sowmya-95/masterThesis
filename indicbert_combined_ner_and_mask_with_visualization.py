# -*- coding: utf-8 -*-
"""IndicBERT_combined_ner_and_Mask_with_visualization.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1aoh6_VKWFz7CbWco32Ig2iUrgcPdZxHV
"""

from google.colab import drive
drive.mount('/content/drive')

# !pip3 install transformers
# !pip3 install datasets
# !pip3 install sentencepiece
# !pip3 install seqeval

# !pip uninstall transformers[torch]

# !pip install transformers[torch] -U

import json
import os

def extract_tokens_tags_and_custom_ids(data):
    document_text = next((item for item in data['%FEATURE_STRUCTURES'] if item['%TYPE'] == 'uima.cas.Sofa'), {}).get('sofaString', '')

    tokens = []
    sentences = []
    named_entities = []
    custom_masking = []

    # Extract tokens, sentences, and custom masking information
    for item in data['%FEATURE_STRUCTURES']:
        if item['%TYPE'] == 'de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token':
            tokens.append({
                'begin': item['begin'],
                'end': item['end'],
                'text': document_text[item['begin']:item['end']],
                'ner_tag': 'O',  # Default NER tag
                'mask_id': 'O'  # Default for tokens not matching any mask
            })
        elif item['%TYPE'] == 'de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence':
            sentences.append({
                'begin': item['begin'],
                'end': item['end'],
                'tokens': []
            })
        elif item['%TYPE'] == 'de.tudarmstadt.ukp.dkpro.core.api.ner.type.NamedEntity':
            value = item.get('value')
            if value:
                parts = value.split(':')
                if len(parts) > 2:
                    english_tag = ':'.join(parts[:2]).strip()
                else:
                    english_tag = parts[0].strip()
                named_entities.append({
                    'begin': item['begin'],
                    'end': item['end'],
                    'value': english_tag
                })
        elif item['%TYPE'] == 'webanno.custom.Masking':
            identifiers = item.get('identifiers')
            if identifiers:
                custom_masking.append({
                    'begin': item['begin'],
                    'end': item['end'],
                    'identifiers': identifiers
                })

    # Sort named entities by begin position and then by end position descending
    named_entities.sort(key=lambda x: (x['begin'], -x['end']))

    # Assign tokens to sentences
    for token in tokens:
        for sentence in sentences:
            if sentence['begin'] <= token['begin'] < sentence['end']:
                sentence['tokens'].append(token)
                break

    # Assign BIO tags to tokens for named entities
    for sentence in sentences:
        for token in sentence['tokens']:
            for ne in named_entities:
                if ne['begin'] <= token['begin'] < ne['end']:
                    prefix = "B-" if token['begin'] == ne['begin'] else "I-"
                    token['ner_tag'] = f"{prefix}{ne['value']}"
                    break

    # Assign custom identifiers to tokens using BIO tag format
    for token in tokens:
        matched = False
        for mask in custom_masking:
            if mask['begin'] <= token['begin'] < mask['end']:
                prefix = "B-" if token['begin'] == mask['begin'] else "I-"
                if mask['identifiers'] == 'Direct_id' or mask['identifiers'] == 'Indirect_id':
                    token['mask_id'] = f"{prefix}mask"
                else:
                    token['mask_id'] = f"{prefix}nomask"
                matched = True
                break
        if not matched:
            token['mask_id'] = 'O'  # Default to 'O' if no masks match

    # Debug: Print token information to check BIO tag assignments
    for token in tokens:
        print(f"Token: {token['text']}, NER Tag: {token['ner_tag']}, Mask ID: {token['mask_id']}")

    # Prepare final output structure
    output_data = []
    for sentence in sentences:
        words = [token['text'] for token in sentence['tokens']]
        ner_tags = [token['ner_tag'] for token in sentence['tokens']]
        mask_ids = [token['mask_id'] for token in sentence['tokens']]
        output_data.append({'words': words, 'ner': ner_tags, 'mask_ids': mask_ids})

    return output_data

def process_files_in_directory(input_directory, output_directory):
    # Ensure output directory exists
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Walk through all files in the input directory
    for root, dirs, files in os.walk(input_directory):
        for file in files:
            if file.endswith('harshal.vilas.tarmale.json'):
                input_path = os.path.join(root, file)
                with open(input_path, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)
                    output_data = extract_tokens_tags_and_custom_ids(data)

                # Prepare output path keeping the relative path
                relative_path = os.path.relpath(root, input_directory)
                output_file_directory = os.path.join(output_directory, relative_path)
                if not os.path.exists(output_file_directory):
                    os.makedirs(output_file_directory)

                output_path = os.path.join(output_file_directory, file.replace('.json', '_processed.json'))
                with open(output_path, 'w', encoding='utf-8') as outfile:
                    json.dump(output_data, outfile, ensure_ascii=False, indent=4)

                print(f"Processed {input_path} and saved to {output_path}")

# Define your input and output directories
input_dir = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_from_inception'
output_dir = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_ner_and_mask_ids_in_BIO'

# Process all JSON files in the nested directory
process_files_in_directory(input_dir, output_dir)

import os
import json
from datasets import Dataset, Features, ClassLabel, Sequence, Value

# Function to gather data from nested JSON files
def gather_data(directory):
    all_data = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)
                    all_data.extend(data)
    return all_data

# Load data from the specified directory
data_directory = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_ner_and_mask_ids_in_BIO'  # Update this path as needed
data = gather_data(data_directory)

# Combine NER and Mask IDs into a single label
for item in data:
    item['combined_labels'] = [f"{ner}-{mask}" if ner != 'O' else 'O' for ner, mask in zip(item['ner'], item['mask_ids'])]

# Extract unique combined labels from the dataset
unique_combined_labels = sorted(set(label for item in data for label in item['combined_labels']))

# Create a ClassLabel feature for combined labels
combined_label_feature = ClassLabel(names=unique_combined_labels)

# Convert the combined labels to integers and create the id_to_label mapping
id_to_label = {index: label for index, label in enumerate(unique_combined_labels)}
label_to_id = {label: index for index, label in enumerate(unique_combined_labels)}

# Convert the combined labels to integers using the label_to_id mapping
for item in data:
    item['labels'] = [label_to_id[label] for label in item['combined_labels']]

# Check for invalid combined labels
invalid_labels = []
for label in unique_combined_labels:
    parts = label.split('-')
    if len(parts) == 3 and parts[2] == 'O':
        invalid_labels.append(label)

# Print invalid labels
if invalid_labels:
    print("Invalid combined labels found:")
    for label in invalid_labels:
        print(label)
else:
    print("No invalid combined labels found.")

# Define features for the dataset
features = Features({
    'words': Sequence(feature=Value(dtype='string', id=None), length=-1),
    'labels': Sequence(feature=combined_label_feature, length=-1)
})

# Create a full Dataset from the processed data
full_dataset = Dataset.from_dict({
    'words': [item['words'] for item in data],
    'labels': [item['labels'] for item in data]
}, features=features)

import os
import json
from collections import defaultdict
from datasets import Dataset, Features, ClassLabel, Sequence, Value

# Function to gather data from nested JSON files
def gather_data(directory):
    all_data = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)
                    all_data.extend(data)
    return all_data

# Load data from the specified directory
data_directory = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_ner_and_mask_ids_in_BIO'  # Update this path as needed
data = gather_data(data_directory)

# Initialize a counter for invalid labels
invalid_label_counts = defaultdict(int)

# Combine NER and Mask IDs into a single label
for item in data:
    combined_labels = []
    for ner, mask in zip(item['ner'], item['mask_ids']):
        if ner == 'O' and mask == 'O':
            combined_labels.append('O')
        elif ner != 'O' and mask == 'O':
            # Increment the invalid label counter for the specific label combination
            invalid_label_counts[f"{ner}-{mask}"] += 1
            continue
        else:
            combined_labels.append(f"{ner}-{mask}")
    item['combined_labels'] = combined_labels

# Extract unique combined labels from the dataset
unique_combined_labels = sorted(set(label for item in data for label in item['combined_labels']))

# Create a ClassLabel feature for combined labels
combined_label_feature = ClassLabel(names=unique_combined_labels)

# Convert the combined labels to integers and create the id_to_label mapping
id_to_label = {index: label for index, label in enumerate(unique_combined_labels)}
label_to_id = {label: index for index, label in enumerate(unique_combined_labels)}

# Convert the combined labels to integers using the label_to_id mapping
for item in data:
    item['labels'] = [label_to_id[label] for label in item['combined_labels']]

# Check for invalid combined labels
invalid_labels = []
for label in unique_combined_labels:
    parts = label.split('-')
    if len(parts) == 3 and parts[2] == 'O':
        invalid_labels.append(label)

# Print invalid labels and their count
if invalid_labels:
    print("Invalid combined labels found:")
    for label in invalid_labels:
        print(label)
else:
    print("No invalid combined labels found.")

print("Total count of each invalid label:")
for label, count in invalid_label_counts.items():
    print(f"{label}: {count}")

# Define features for the dataset
features = Features({
    'words': Sequence(feature=Value(dtype='string', id=None), length=-1),
    'labels': Sequence(feature=combined_label_feature, length=-1)
})

# Create a full Dataset from the processed data
full_dataset = Dataset.from_dict({
    'words': [item['words'] for item in data],
    'labels': [item['labels'] for item in data]
}, features=features)

import os
import json
from collections import defaultdict
from datasets import Dataset, Features, ClassLabel, Sequence, Value

# Function to gather data from nested JSON files
def gather_data(directory):
    all_data = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)
                    all_data.extend(data)
    return all_data

# Load data from the specified directory
data_directory = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_ner_and_mask_ids_in_BIO'  # Update this path as needed
data = gather_data(data_directory)

# Initialize counters for valid and invalid labels
invalid_label_counts = defaultdict(int)
valid_label_counts = defaultdict(int)

# Combine NER and Mask IDs into a single label
for item in data:
    combined_labels = []
    for ner, mask in zip(item['ner'], item['mask_ids']):
        if ner == 'O' and mask == 'O':
            combined_labels.append('O')
            valid_label_counts['O'] += 1
        elif ner != 'O' and mask == 'O':
            # Increment the invalid label counter for the specific label combination
            invalid_label_counts[f"{ner}-{mask}"] += 1
            continue
        else:
            combined_label = f"{ner}-{mask}"
            combined_labels.append(combined_label)
            valid_label_counts[combined_label] += 1
    item['combined_labels'] = combined_labels

# Extract unique combined labels from the dataset
unique_combined_labels = sorted(set(label for item in data for label in item['combined_labels']))

# Create a ClassLabel feature for combined labels
combined_label_feature = ClassLabel(names=unique_combined_labels)

# Convert the combined labels to integers and create the id_to_label mapping
id_to_label = {index: label for index, label in enumerate(unique_combined_labels)}
label_to_id = {label: index for index, label in enumerate(unique_combined_labels)}

# Convert the combined labels to integers using the label_to_id mapping
for item in data:
    item['labels'] = [label_to_id[label] for label in item['combined_labels']]

# Check for invalid combined labels
invalid_labels = []
for label in unique_combined_labels:
    parts = label.split('-')
    if len(parts) == 3 and parts[2] == 'O':
        invalid_labels.append(label)

# Print valid labels and their counts
print("Total count of each valid label:")
for label, count in valid_label_counts.items():
    print(f"{label}: {count}")

# Print invalid labels and their counts
if invalid_labels:
    print("Invalid combined labels found:")
    for label in invalid_labels:
        print(label)
else:
    print("No invalid combined labels found.")

print("Total count of each invalid label:")
for label, count in invalid_label_counts.items():
    print(f"{label}: {count}")

# Define features for the dataset
features = Features({
    'words': Sequence(feature=Value(dtype='string', id=None), length=-1),
    'labels': Sequence(feature=combined_label_feature, length=-1)
})

# Create a full Dataset from the processed data
full_dataset = Dataset.from_dict({
    'words': [item['words'] for item in data],
    'labels': [item['labels'] for item in data]
}, features=features)

import os
import json
from collections import defaultdict
from datasets import Dataset, Features, ClassLabel, Sequence, Value

# Function to gather data from nested JSON files
def gather_data(directory):
    all_data = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)
                    all_data.extend(data)
    return all_data

# Load data from the specified directory
data_directory = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_ner_and_mask_ids_in_BIO'  # Update this path as needed
data = gather_data(data_directory)

# Initialize counters for valid and invalid labels
invalid_label_counts = defaultdict(int)
valid_label_counts = defaultdict(int)

# Combine NER and Mask IDs into a single label
for item in data:
    combined_labels = []
    for ner, mask in zip(item['ner'], item['mask_ids']):
        if ner == 'O' and mask == 'O':
            combined_labels.append('O')
            valid_label_counts['O'] += 1
        elif ner != 'O' and mask == 'O':
            # Increment the invalid label counter for the specific label combination
            invalid_label_counts[f"{ner}-{mask}"] += 1
            continue
        else:
            # Modify the combined label logic to reflect `mask` or `nomask`
            combined_label = f"{ner}-mask" if "mask" in mask else f"{ner}-nomask"
            combined_labels.append(combined_label)
            valid_label_counts[combined_label] += 1
    item['combined_labels'] = combined_labels

# Extract unique combined labels from the dataset
unique_combined_labels = sorted(set(label for item in data for label in item['combined_labels']))

# Create a ClassLabel feature for combined labels
combined_label_feature = ClassLabel(names=unique_combined_labels)

# Convert the combined labels to integers and create the id_to_label mapping
id_to_label = {index: label for index, label in enumerate(unique_combined_labels)}
label_to_id = {label: index for index, label in enumerate(unique_combined_labels)}

# Convert the combined labels to integers using the label_to_id mapping
for item in data:
    item['labels'] = [label_to_id[label] for label in item['combined_labels']]

# Print valid labels and their counts
print("Total count of each valid label:")
for label, count in valid_label_counts.items():
    print(f"{label}: {count}")

# Print invalid labels and their counts
print("Total count of each invalid label:")
for label, count in invalid_label_counts.items():
    print(f"{label}: {count}")

# Define features for the dataset
features = Features({
    'words': Sequence(feature=Value(dtype='string', id=None), length=-1),
    'labels': Sequence(feature=combined_label_feature, length=-1)
})

# Create a full Dataset from the processed data
full_dataset = Dataset.from_dict({
    'words': [item['words'] for item in data],
    'labels': [item['labels'] for item in data]
}, features=features)

import os
import json
from collections import defaultdict
from datasets import Dataset, Features, ClassLabel, Sequence, Value

# Function to gather data from nested JSON files
def gather_data(directory):
    all_data = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)
                    all_data.extend(data)
    return all_data

# Load data from the specified directory
data_directory = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_ner_and_mask_ids_in_BIO'  # Update this path as needed
data = gather_data(data_directory)

# Initialize counters for valid and invalid labels
invalid_label_counts = defaultdict(int)
valid_label_counts = defaultdict(int)

# Initialize total counters
total_valid_count = 0
total_invalid_count = 0

# Combine NER and Mask IDs into a single label
for item in data:
    combined_labels = []
    for ner, mask in zip(item['ner'], item['mask_ids']):
        if ner == 'O' and mask == 'O':
            combined_labels.append('O')
            valid_label_counts['O'] += 1
            total_valid_count += 1
        elif ner != 'O' and mask == 'O':
            # Increment the invalid label counter for the specific label combination
            invalid_label_counts[f"{ner}-{mask}"] += 1
            total_invalid_count += 1
            continue
        else:
            # Modify the combined label logic to reflect `mask` or `nomask`
            if mask == "I-mask" or mask == "B-mask":
                combined_label = f"{ner}-mask"
            else:
                combined_label = f"{ner}-nomask"
            combined_labels.append(combined_label)
            valid_label_counts[combined_label] += 1
            total_valid_count += 1
    item['combined_labels'] = combined_labels

# Extract unique combined labels from the dataset
unique_combined_labels = sorted(set(label for item in data for label in item['combined_labels']))

# Create a ClassLabel feature for combined labels
combined_label_feature = ClassLabel(names=unique_combined_labels)

# Convert the combined labels to integers and create the id_to_label mapping
id_to_label = {index: label for index, label in enumerate(unique_combined_labels)}
label_to_id = {label: index for index, label in enumerate(unique_combined_labels)}

# Convert the combined labels to integers using the label_to_id mapping
for item in data:
    item['labels'] = [label_to_id[label] for label in item['combined_labels']]

# Print valid labels and their counts
print("Total count of each valid label:")
for label, count in valid_label_counts.items():
    print(f"{label}: {count}")

# Print invalid labels and their counts
print("Total count of each invalid label:")
for label, count in invalid_label_counts.items():
    print(f"{label}: {count}")

# Print total counts of all valid and all invalid labels
total_valid_labels = sum(valid_label_counts.values())
total_invalid_labels = sum(invalid_label_counts.values())
print(f"Total count of all valid labels: {total_valid_labels}")
print(f"Total count of all invalid labels: {total_invalid_labels}")

# Define features for the dataset
features = Features({
    'words': Sequence(feature=Value(dtype='string', id=None), length=-1),
    'labels': Sequence(feature=combined_label_feature, length=-1)
})

# Create a full Dataset from the processed data
full_dataset = Dataset.from_dict({
    'words': [item['words'] for item in data],
    'labels': [item['labels'] for item in data]
}, features=features)

import os
import json
from collections import defaultdict
from datasets import Dataset, Features, ClassLabel, Sequence, Value

# Function to gather data from nested JSON files
def gather_data(directory):
    all_data = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as infile:
                    data = json.load(infile)
                    all_data.extend(data)
    return all_data

# Load data from the specified directory
data_directory = '/content/drive/MyDrive/NLPMasterthesis/Tesseract-OCR/Documents/final_documents_ner_and_mask_ids_in_BIO'  # Update this path as needed
data = gather_data(data_directory)

# Initialize counters for valid and invalid labels
invalid_label_counts = defaultdict(int)
valid_mask_label_counts = defaultdict(int)
valid_nomask_label_counts = defaultdict(int)

# Initialize total counters
total_valid_mask_count = 0
total_valid_nomask_count = 0
total_invalid_count = 0

# Combine NER and Mask IDs into a single label
for item in data:
    combined_labels = []
    for ner, mask in zip(item['ner'], item['mask_ids']):
        if ner == 'O' and mask == 'O':
            combined_labels.append('O')
            valid_nomask_label_counts['O'] += 1
            total_valid_nomask_count += 1
        elif ner != 'O' and mask == 'O':
            # Increment the invalid label counter for the specific label combination
            invalid_label_counts[f"{ner}-{mask}"] += 1
            total_invalid_count += 1
            continue
        else:
            # Modify the combined label logic to reflect `mask` or `nomask`
            if mask == "I-mask" or mask == "B-mask":
                combined_label = f"{ner}-mask"
                valid_mask_label_counts[combined_label] += 1
                total_valid_mask_count += 1
            else:
                combined_label = f"{ner}-nomask"
                valid_nomask_label_counts[combined_label] += 1
                total_valid_nomask_count += 1
            combined_labels.append(combined_label)
    item['combined_labels'] = combined_labels

# Extract unique combined labels from the dataset
unique_combined_labels = sorted(set(label for item in data for label in item['combined_labels']))

# Create a ClassLabel feature for combined labels
combined_label_feature = ClassLabel(names=unique_combined_labels)

# Convert the combined labels to integers and create the id_to_label mapping
id_to_label = {index: label for index, label in enumerate(unique_combined_labels)}
label_to_id = {label: index for index, label in enumerate(unique_combined_labels)}

# Convert the combined labels to integers using the label_to_id mapping
for item in data:
    item['labels'] = [label_to_id[label] for label in item['combined_labels']]

# Print valid mask labels and their counts
print("Total count of each valid mask label:")
for label, count in valid_mask_label_counts.items():
    print(f"{label}: {count}")

# Print valid nomask labels and their counts
print("Total count of each valid nomask label:")
for label, count in valid_nomask_label_counts.items():
    print(f"{label}: {count}")

# Print invalid labels and their counts
print("Total count of each invalid label:")
for label, count in invalid_label_counts.items():
    print(f"{label}: {count}")

# Print total counts of all valid and all invalid labels
print(f"Total count of all valid mask labels: {total_valid_mask_count}")
print(f"Total count of all valid nomask labels: {total_valid_nomask_count}")
print(f"Total count of all invalid labels: {total_invalid_count}")

# Define features for the dataset
features = Features({
    'words': Sequence(feature=Value(dtype='string', id=None), length=-1),
    'labels': Sequence(feature=combined_label_feature, length=-1)
})

# Create a full Dataset from the processed data
full_dataset = Dataset.from_dict({
    'words': [item['words'] for item in data],
    'labels': [item['labels'] for item in data]
}, features=features)

