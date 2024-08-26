import openai
import os
from rdkit import Chem
from rdkit.Chem import AllChem

# open ai key
openai.api_key = ''

error_categories = [
    "Unclosed Ring",
    "Invalid Character",
    "Duplicate Bond",
    "Invalid Bond Order",
    "Atom Not Recognized",
    "Invalid Ring Closure",
    "Invalid Valence"
]

def classify_error(error_message):
    error_vector = [1] * len(error_categories)
    
    if "Unclosed ring" in error_message:
        error_vector[error_categories.index("Unclosed Ring")] = 0
    if "Invalid character" in error_message:
        error_vector[error_categories.index("Invalid Character")] = 0
    if "Duplicate bond" in error_message:
        error_vector[error_categories.index("Duplicate Bond")] = 0
    if "Invalid bond order" in error_message:
        error_vector[error_categories.index("Invalid Bond Order")] = 0
    if "Atom not recognized" in error_message:
        error_vector[error_categories.index("Atom Not Recognized")] = 0
    if "Invalid ring closure" in error_message:
        error_vector[error_categories.index("Invalid Ring Closure")] = 0
    if "Invalid valence" in error_message:
        error_vector[error_categories.index("Invalid Valence")] = 0
    
    return error_vector

def parse_smiles(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        error_message = "SMILES Parse Error: Failed to generate molecule from SMILES"
        return False, classify_error(error_message)
    return True, [1] * len(error_categories)

def call_chatgpt(prompt):
    detailed_prompt = (
        "You are a chemical informatics expert. I have a list of SMILES validation error vectors "
        "for chemical reactants and a product. Each vector corresponds to specific types of errors "
        "in the SMILES strings, such as 'Unclosed Ring', 'Invalid Character', 'Duplicate Bond', "
        "'Invalid Bond Order', 'Atom Not Recognized', 'Invalid Ring Closure', and 'Invalid Valence'. "
        "I need you to analyze these error vectors and identify which atoms in the SMILES strings "
        "are causing the errors. The output should be a binary string where each '0' represents a "
        "wrong atom, and each '1' represents a correct atom in the SMILES notation. Here are the details:\n\n"
        f"{prompt}\n\n"
        "Please return a binary string for each reactant and product, indicating the correctness of each atom."
    )
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a chemical informatics expert."},
            {"role": "user", "content": detailed_prompt}
        ]
    )
    return response['choices'][0]['message']['content']


def validate_reaction(product_smiles, reactant_smiles_array):
    success_product, product_error_vector = parse_smiles(product_smiles)
    
    reactant_error_vectors = []
    valid_reactants = []
    
    for i, reactant_smiles in enumerate(reactant_smiles_array):
        success_reactant, reactant_error_vector = parse_smiles(reactant_smiles)
        if success_reactant:
            valid_reactants.append(Chem.MolFromSmiles(reactant_smiles))
        reactant_error_vectors.append((i, reactant_error_vector))
    
    if not success_product or len(valid_reactants) != len(reactant_smiles_array):
        errors = []
        if not success_product:
            errors.append(f"Product Error Vector: {product_error_vector}")
        for i, error_vector in reactant_error_vectors:
            if error_vector != [1] * len(error_categories):
                errors.append(f"Reactant {i+1} Error Vector: {error_vector}")
        
        llm_input = "\n".join(errors)
        print("LLM Input:", llm_input)
        
        llm_output = call_chatgpt(llm_input)
        return llm_output

    reactants_smiles = '.'.join(reactant_smiles_array)
    reaction_smarts = f"{reactants_smiles}>>{product_smiles}"
    reaction = AllChem.ReactionFromSmarts(reaction_smarts)
    
    ps = reaction.RunReactants(tuple(valid_reactants))
    valid_reaction = False
    
    for product_tuple in ps:
        generated_product = product_tuple[0]
        if Chem.MolToSmiles(generated_product) == product_smiles:
            valid_reaction = True
            break
    
    if valid_reaction:
        return "The predicted reactants are valid and produce the correct product."
    
    errors = ["The reactants do not combine to produce the given product."]
    errors.append(f"Product Error Vector: {product_error_vector}")
    for i, error_vector in reactant_error_vectors:
        errors.append(f"Reactant {i+1} Error Vector: {error_vector}")
    
    llm_input = "\n".join(errors)
    print("LLM Input:", llm_input)
    
    llm_output = call_chatgpt(llm_input)
    return llm_output

product_smiles = 'CC(=O)OCC1=CC=CC=C1C(=O)O'
reactant_smiles_array = ['CC(=O)O[C1]=CC=CC=C1C(=O)O', 'CC1=CC=CC1=O']  # Multiple errors in both reactants

result = validate_reaction(product_smiles, reactant_smiles_array)
print(result)
