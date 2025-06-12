from fhir.resources.encounter import Encounter
import json, importlib
from pydantic import ConfigDict

model_class_cache = {}

def get_fhir_model(resource_type):
    """Dynamically import and return the FHIR resource model class, with caching."""
    if resource_type.lower() in model_class_cache:
        return model_class_cache[resource_type.lower()]
    module_name = f"fhir.resources.{resource_type.lower()}"
    class_name = resource_type.capitalize()
    module = importlib.import_module(module_name)
    base_class = getattr(module, class_name)
    # Dynamically create a subclass that allows extra fields
    class CustomModel(base_class):
        model_config = ConfigDict(extra='allow')
    model_class_cache[resource_type.lower()] = CustomModel
    return CustomModel

def preprocess_encounter_json(enc_json):
    # Remove 'class' field entirely if present
    if "class" in enc_json:
        del enc_json["class"]
    # Remove 'individual' field from each participant if present
    if "participant" in enc_json:
        for part in enc_json["participant"]:
            if "individual" in part:
                del part["individual"]
    return enc_json

# Usage:
with open('./failed_encounter.json', 'r') as file:
    resource_json = json.load(file)

resource_json = preprocess_encounter_json(resource_json)
obj_model = get_fhir_model("Encounter")
resource_obj = obj_model.model_validate(resource_json, strict=False)
print(resource_obj)