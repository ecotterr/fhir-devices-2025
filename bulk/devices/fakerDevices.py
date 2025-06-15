import csv
import json
import random
import uuid
from faker import Faker
from datetime import datetime, timedelta
import os
import demoSettings

fake = Faker()

CSV_PATH = demoSettings.dev_path + "/mappings_2.csv"
OUTPUT_DIR = "fhir_output"

DEVICE_TYPES = [
    {"type": "Smartwatch", "code": {"system": "http://snomed.info/sct", "code": "706168006", "display": "Smart watch device"}},
    {"type": "BP Cuff", "code": {"system": "http://snomed.info/sct", "code": "705051002", "display": "Blood pressure cuff"}},
    {"type": "Pulse Oximeter", "code": {"system": "http://snomed.info/sct", "code": "706170002", "display": "Pulse oximeter"}},
    {"type": "CGM", "code": {"system": "http://snomed.info/sct", "code": "706171003", "display": "Continuous glucose monitor"}}
]

OBSERVATION_TYPES = [
    {
        "label": "Heart rate",
        "code": {"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"},
        "unit": "beats/minute", "unit_code": "bpm", "range": (55, 110)
    },
    {
        "label": "Respiratory rate",
        "code": {"system": "http://loinc.org", "code": "9279-1", "display": "Respiratory rate"},
        "unit": "breaths/minute", "unit_code": "breaths/min", "range": (12, 22)
    },
    {
        "label": "Systolic blood pressure",
        "code": {"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"},
        "unit": "mmHg", "unit_code": "mm[Hg]", "range": (100, 140)
    },
    {
        "label": "Diastolic blood pressure",
        "code": {"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"},
        "unit": "mmHg", "unit_code": "mm[Hg]", "range": (60, 90)
    },
    {
        "label": "Body temperature",
        "code": {"system": "http://loinc.org", "code": "8310-5", "display": "Body temperature"},
        "unit": "Celsius", "unit_code": "Cel", "range": (36.0, 38.0)
    },
    {
        "label": "Blood oxygen saturation (SpO2)",
        "code": {"system": "http://loinc.org", "code": "59408-5", "display": "Oxygen saturation in Arterial blood"},
        "unit": "%", "unit_code": "%", "range": (92, 100)
    },
    {
        "label": "Heart rate variability",
        "code": {"system": "http://loinc.org", "code": "80372-6", "display": "HRV (Standard deviation of NN intervals)"},
        "unit": "ms", "unit_code": "ms", "range": (20, 120)
    },
    {
        "label": "Skin temperature",
        "code": {"system": "http://loinc.org", "code": "8328-7", "display": "Skin temperature"},
        "unit": "Celsius", "unit_code": "Cel", "range": (32.0, 36.0)
    },
    {
        "label": "Glucose (CGM)",
        "code": {"system": "http://loinc.org", "code": "15074-8", "display": "Glucose [Moles/volume] in Capillary blood"},
        "unit": "mmol/L", "unit_code": "mmol/L", "range": (3.5, 10.0)
    },
    {
        "label": "Step count",
        "code": {"system": "http://loinc.org", "code": "41950-7", "display": "Number of steps in 24 hours"},
        "unit": "steps", "unit_code": "steps", "range": (1000, 20000)
    },
    {
        "label": "Calories burned",
        "code": {"system": "http://loinc.org", "code": "41981-2", "display": "Calories burned"},
        "unit": "kcal", "unit_code": "kcal", "range": (1500, 4000)
    },
    {
        "label": "Distance walked/run",
        "code": {"system": "http://loinc.org", "code": "41953-1", "display": "Distance walked or run in 24 hours"},
        "unit": "km", "unit_code": "km", "range": (1.0, 20.0)
    },
    {
        "label": "Duration of exercise",
        "code": {"system": "http://loinc.org", "code": "55411-3", "display": "Exercise duration"},
        "unit": "minutes", "unit_code": "min", "range": (10, 120)
    },
    {
        "label": "Exercise heart rate",
        "code": {"system": "http://loinc.org", "code": "55423-8", "display": "Heart rate during exercise"},
        "unit": "beats/minute", "unit_code": "bpm", "range": (90, 170)
    }
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

patients = []
with open(CSV_PATH, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["resource_type"] == "Patient":
            patients.append(row["resource_id"])

all_devices = []
all_observations = []

for patient_id in patients:
    # Generate devices for each patient
    num_devices = random.randint(1, 3)
    patient_devices = []
    for _ in range(num_devices):
        device_type = random.choice(DEVICE_TYPES)
        device_id = str(uuid.uuid4())
        device = {
            "resourceType": "Device",
            "id": device_id,
            "type": {
                "coding": [device_type["code"]],
                "text": device_type["type"]
            },
            "patient": {"reference": f"Patient/{patient_id}"},
            "manufacturer": fake.company(),
            "modelNumber": fake.word() + "-" + str(random.randint(100, 999)), ## need to use Device.modelNumber for R4 spec with searchparam 'model'
            "serialNumber": str(uuid.uuid4())
        }
        all_devices.append(device)
        patient_devices.append(device)

    # Generate observations per type per patient
    for obs_type in OBSERVATION_TYPES:
        num_obs = random.randint(2, 4)
        for _ in range(num_obs):
            obs_id = str(uuid.uuid4())
            device = random.choice(patient_devices)
            effective_datetime = (datetime.now() - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 1440))).isoformat()
            effective_datetime += "Z"
            # Use float for some types, int for others
            if isinstance(obs_type["range"][0], float) or isinstance(obs_type["range"][1], float):
                value = round(random.uniform(*obs_type["range"]), 1)
            else:
                value = random.randint(*obs_type["range"])
            observation = {
                "resourceType": "Observation",
                "id": obs_id,
                "status": "final",
                "category": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }]
                }],
                "code": {
                    "coding": obs_type["code"]
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "device": {"reference": f"Device/{device['id']}"},
                "effectiveDateTime": effective_datetime,
                "valueQuantity": {
                    "value": value,
                    "unit": obs_type["unit"],
                    "system": "http://unitsofmeasure.org",
                    "code": obs_type["unit_code"]
                }
            }
            all_observations.append(observation)

with open(os.path.join(OUTPUT_DIR, "devices.json"), "w") as f:
    json.dump(all_devices, f, indent=2)

with open(os.path.join(OUTPUT_DIR, "observations.json"), "w") as f:
    json.dump(all_observations, f, indent=2)

print(f"Generated {len(all_devices)} devices and {len(all_observations)} observations for {len(patients)} patients.")