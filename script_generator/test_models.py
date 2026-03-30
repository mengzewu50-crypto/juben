import google.generativeai as genai
import json

genai.configure(api_key="AIzaSyAeKE0-zOBCf4V5_Mg71OxvpTbrzRyGZr0")
models = []
for m in genai.list_models():
    models.append({"name": m.name, "methods": m.supported_generation_methods})

with open("models.json", "w", encoding="utf-8") as f:
    json.dump(models, f)
